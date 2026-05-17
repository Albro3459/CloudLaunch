import json
import boto3

from vpn_manager import deploy_instance, terminate_instance_resources
from role_manager import get_max_count_for_role, get_user_vpn_count, increment_user_count
from firebase import (
    get_instance,
    get_user_instances_in_region,
    initialize_firebase,
    mark_instance_terminated,
    record_instance_cleanup_error,
    verify_firebase_token,
    get_user_role,
)
from get_secrets import (
    AwsSecretKey,
    OciSecretKey,
    SecretSection,
    VpnSecretKey,
    get_cloudlaunch_secret,
    get_secret_section,
    get_secret_value,
)
from notify import deliver_emails
from config_helper import get_config, get_wireguard_config_options

AWS_REGION = "us-west-1"

VALID_ACTIONS = {"deploy", "terminate"}

dynamodb = boto3.resource("dynamodb")
user_table = dynamodb.Table("vpn-users")
role_table = dynamodb.Table("vpn-roles")


def _build_cleanup_error(instance_id, cleanup_result):
    stack_result = cleanup_result.get("stack", {})
    instance_result = cleanup_result.get("instance", {})
    return (
        f"Cleanup failed for {instance_id}. "
        f"Stack cleanup: {stack_result.get('status')} ({stack_result.get('detail')}). "
        f"Instance cleanup: {instance_result.get('status')} ({instance_result.get('detail')})."
    )


def _record_cleanup_error_safely(uid, region, instance_id, error_message):
    try:
        record_instance_cleanup_error(uid, region, instance_id, error_message)
    except Exception as e:
        print(f"Failed to persist cleanup error for {instance_id}: {e}")

def _build_deploy_response(is_new, oci_region, oci_region_name, public_ipv4, client_private_key, server_public_key, wireguard_options):
    return {
        "isNew": is_new,
        "region": {
            "oci_region": oci_region,
            "oci_region_name": oci_region_name,
        },
        "ip_addresses": {
            "public_ipv4": public_ipv4,
        },
        "wireguard_config": get_config(
            client_private_key,
            server_public_key,
            public_ipv4,
            wireguard_options,
        ),
    }

def lambda_handler(event, context):
    """
    Handles incoming Lambda requests
    Token is extracted from the 'Authorization' header
    """
    headers = event.get("headers", {})
    auth_header = headers.get("Authorization", headers.get("authorization", "")).strip() # AWS is case-sensitive
    token = auth_header.replace("Bearer ", "")

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON body"})
        }

    # Extract required values
        # Action params
    action = (body.get("action") or "").strip() # ALWAYS REQUIRED
    # targets = {
    #     "userID": {
    #         "us-west-1": ["i-0123"],
    #         "us-east-1": ["i-0456"]
    #     }
    # }
    targets = body.get("targets") or {} # (Required for non-deploy actions)
    
        # Deploy params (Required for Deploy)
    email = (body.get("email") or "").strip()

    # Validate input
    if not token:
        print(f"Missing required parameter")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required parameter"})
        }
    if not action or action.lower() not in VALID_ACTIONS:
        print(f"Missing or invalid action: {action}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing or invalid action"})
        }        
        
    # Fetch secrets
    cloudlaunch_secret = get_cloudlaunch_secret(AWS_REGION)
    if not cloudlaunch_secret:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve secrets from AWS"})
        }
    try:
        aws_config = get_secret_section(cloudlaunch_secret, SecretSection.AWS)
        firebaseSecrets = get_secret_section(cloudlaunch_secret, SecretSection.FIREBASE)
        oci_config = get_secret_section(cloudlaunch_secret, SecretSection.OCI)
        vpn_config = get_secret_section(cloudlaunch_secret, SecretSection.VPN)
    except ValueError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    try:
        client_private_key = get_secret_value(vpn_config, VpnSecretKey.CLIENT_PRIVATE_KEY)
        server_public_key = get_secret_value(vpn_config, VpnSecretKey.SERVER_PUBLIC_KEY)
        sender = get_secret_value(aws_config, AwsSecretKey.SES_SENDER)
        admin_email = get_secret_value(aws_config, AwsSecretKey.ADMIN_EMAIL)
        oci_region = get_secret_value(oci_config, OciSecretKey.REGION)
        oci_region_name = get_secret_value(oci_config, OciSecretKey.REGION_NAME)
    except ValueError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
    try:
        wireguard_options = get_wireguard_config_options(vpn_config)
    except ValueError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
    
    # Verify token
    initialize_firebase(firebaseSecrets)
    user_id = verify_firebase_token(token)
    if not user_id:
        return {"statusCode": 403, "body": json.dumps({"error": "Invalid or expired token"})}
    role = get_user_role(user_id)
    if not role: 
        return {"statusCode": 403, "body": json.dumps({"error": "No user role found"})}
        
    # Perform Action        

    if action.lower() == "terminate":
        if role != "admin":
            return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}
        if not targets or not isinstance(targets, dict):
            print(f"Invalid or missing targets: {targets}")
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid or missing targets"})}

        print(f"User {user_id}: terminating {targets}")

        terminated_targets = []
        errors = []
        for uid, regions in targets.items():
            for region, instance_ids in regions.items():
                for instance_id in instance_ids:
                    instance = get_instance(uid, region, instance_id)
                    if not instance:
                        errors.append({
                            "uid": uid,
                            "region": region,
                            "instance_id": instance_id,
                            "error": "Instance record not found",
                        })
                        continue

                    stack_id = instance.get("stackOcid") or instance_id
                    instance_ocid = instance.get("instanceOcid")

                    try:
                        cleanup_result = terminate_instance_resources(
                            oci_config,
                            oci_region,
                            stack_id=stack_id,
                            instance_ocid=instance_ocid,
                        )
                        if cleanup_result["ok"]:
                            mark_instance_terminated(uid, region, instance_id)
                            terminated_targets.append({
                                "uid": uid,
                                "region": region,
                                "instance_id": instance_id,
                                "stack_id": stack_id,
                                "instance_ocid": instance_ocid,
                            })
                            continue

                        _record_cleanup_error_safely(
                            uid,
                            region,
                            instance_id,
                            _build_cleanup_error(instance_id, cleanup_result),
                        )
                        errors.append({
                            "uid": uid,
                            "region": region,
                            "instance_id": instance_id,
                            "stack_id": stack_id,
                            "instance_ocid": instance_ocid,
                            "stack": cleanup_result.get("stack"),
                            "instance": cleanup_result.get("instance"),
                        })
                    except Exception as e:
                        error_message = f"Failed to terminate {instance_id}: {e}"
                        _record_cleanup_error_safely(uid, region, instance_id, error_message)
                        errors.append({
                            "uid": uid,
                            "region": region,
                            "instance_id": instance_id,
                            "stack_id": stack_id,
                            "instance_ocid": instance_ocid,
                            "error": str(e),
                        })

        if errors:
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "One or more terminations failed",
                    "details": errors,
                    "terminated": terminated_targets,
                })
            }

        return {
            "statusCode": 200,
            "body": json.dumps({
                "action_completed": action.lower(),
                "terminated": terminated_targets,
            })
        }
        
    elif action.lower() == "deploy":
        if not email:
            print(f"Missing required parameters: {email}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Missing required parameters"})
            }
        
        # Check if the user can make more VPNs
        user_vpn_count = get_user_vpn_count(user_id, user_table)
        vpn_role_max_count = get_max_count_for_role(role, role_table)
        if user_vpn_count >= vpn_role_max_count:
            return {"statusCode": 403, "body": json.dumps({"error": "User's VPN limit reached"})}
        increment_user_count(user_id, user_table)
                    
        # Make sure there are no running instances in the region for that user
        # if there are, just return that instance ID
        vpn = get_user_instances_in_region(user_id, role, oci_region)
        if vpn:
            instance_ip = list(vpn.values())[0][0]["ipv4"]
            print(f"VPN {instance_ip} already exists in region {oci_region} for user {user_id}")
            return {
                "statusCode": 200,
                "body": json.dumps(_build_deploy_response(
                    False,
                    oci_region,
                    oci_region_name,
                    instance_ip,
                    client_private_key,
                    server_public_key,
                    wireguard_options,
                ))
            }

        # Deploy the OCI instance through Resource Manager
        result = deploy_instance(oci_config, vpn_config, user_id, oci_region)
        if result["error"]:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": result["error"]})
            }        
        instance_id = result["instance_id"]
        public_ip = result["public_ip"]

        if not instance_id or not public_ip:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to deploy instance"})
            }
            
        # Send emails
        ses_client = boto3.client('sesv2', region_name=AWS_REGION)
        emails = [email]
        if email != admin_email:
            emails.append(admin_email)
        
        deliver_emails(
            ses_client,
            client_private_key,
            server_public_key,
            public_ip,
            oci_region_name,
            sender,
            emails,
            wireguard_options,
        )

        return {
            "statusCode": 200,
            "body": json.dumps(_build_deploy_response(
                True,
                oci_region,
                oci_region_name,
                public_ip,
                client_private_key,
                server_public_key,
                wireguard_options,
            ))
        }
    else:
        print(f"{action} is not a valid action")
        return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Not a valid action"})
            }
