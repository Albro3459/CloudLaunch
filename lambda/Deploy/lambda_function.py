import json
import boto3

from vpn_manager import deploy_instance, terminate_instance_resources
from role_manager import get_max_count_for_role, get_user_vpn_count, increment_user_count
from firebase import (
    get_instance,
    get_user_instances_in_region,
    get_live_regions,
    initialize_firebase,
    mark_instance_terminated,
    record_instance_cleanup_error,
    verify_firebase_token,
    get_user_role,
)
from get_secrets import get_secret
from notify import deliver_emails
from config_helper import get_wireguard_config_options

AWS_REGION = "us-west-1"

FIREBASE_SECRET_NAME = "FirebaseServiceAccount"
DEPLOY_SECRET_NAME = "VPN-Config"
OCI_AUTH_SECRET_NAME = "OCI-Auth"

VALID_ACTIONS = {"deploy", "terminate"}

OCI_REGION = "us-sanjose-1"
OCI_REGION_NAME = "San Jose"

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

def lambda_handler(event, context):
    """
    Handles incoming Lambda requests
    Takes in 'region' and 'instance_name' in the event body
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
    target_region = (body.get("target_region") or "").strip()    

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
    vpn_config_secret = get_secret(DEPLOY_SECRET_NAME, AWS_REGION)
    if not vpn_config_secret:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve secrets from AWS"})
        }
    oci_auth_secret = get_secret(OCI_AUTH_SECRET_NAME, AWS_REGION)
    if not oci_auth_secret:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Failed to retrieve required secret: {OCI_AUTH_SECRET_NAME}"})
        }
    firebaseSecrets = get_secret(FIREBASE_SECRET_NAME, AWS_REGION)
    if not firebaseSecrets:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed retrieving secrets from AWS"})
        }

    if vpn_config_secret.get("OCI_REGION") and vpn_config_secret.get("OCI_REGION") != OCI_REGION:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "OCI secret region does not match configured OCI region"})
        }

    client_private_key = vpn_config_secret.get("WG_CLIENT_PRIVATE_KEY")
    server_public_key = vpn_config_secret.get("WG_SERVER_PUBLIC_KEY")
    sender = vpn_config_secret.get("SES_SENDER")
    admin_email = vpn_config_secret.get("ADMIN_EMAIL")
    if not client_private_key or not server_public_key or not sender or not admin_email:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Missing required secret values"})
        }
    try:
        wireguard_options = get_wireguard_config_options(vpn_config_secret)
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
                            oci_auth_secret,
                            OCI_REGION,
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
        if not email or not target_region:
            print(f"Missing required parameters: {email}, {target_region}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Missing required parameters"})
            }
            
        live_regions = get_live_regions()
        if target_region not in [r["value"] for r in live_regions]:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Target region is not live"})
            }
        
        # Check if the user can make more VPNs
        user_vpn_count = get_user_vpn_count(user_id, user_table)
        vpn_role_max_count = get_max_count_for_role(role, role_table)
        if user_vpn_count >= vpn_role_max_count:
            return {"statusCode": 403, "body": json.dumps({"error": "User's VPN limit reached"})}
        increment_user_count(user_id, user_table)
                    
        # Make sure there are no running instances in the region for that user
        # if there are, just return that instance ID
        vpn = get_user_instances_in_region(user_id, role, target_region)
        if vpn:
            instance_ip = list(vpn.values())[0][0]["ipv4"]
            print(f"VPN {instance_ip} already exists in region {target_region} for user {user_id}")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "isNew": False,
                    "public_ipv4": instance_ip,
                    "client_private_key": client_private_key,
                    "server_public_key": server_public_key
                })
            }

        # Deploy the OCI instance through Resource Manager
        result = deploy_instance(vpn_config_secret, oci_auth_secret, user_id, target_region)
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
            OCI_REGION_NAME,
            sender,
            emails,
            wireguard_options,
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "isNew": True,
                "public_ipv4": public_ip,
                "client_private_key": client_private_key,
                "server_public_key": server_public_key
            })
        }
    else:
        print(f"{action} is not a valid action")
        return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Not a valid action"})
            }
