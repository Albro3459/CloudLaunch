import json
import boto3

from vpn_manager import check_image_exists, deploy_instance, shutdown_all_other_instances
from role_manager import get_max_count_for_role, get_user_vpn_count, increment_user_count
from firebase import get_live_regions, initialize_firebase, verify_firebase_token, get_user_role
from get_secrets import get_secret

CLEANUP_VPNS = True

dynamodb = boto3.resource("dynamodb")
user_table = dynamodb.Table("vpn-users")
role_table = dynamodb.Table("vpn-roles")

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
    target_region = body.get("region", "").strip()
    instance_name = body.get("instance_name", "").strip()

    # Validate input
    if not instance_name or len(instance_name) == 0:
        instance_name = "VPN"
    if not target_region or not token or \
        len(target_region) == 0 or len(token) == 0:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required parameters: {target_region}"})
        }

    # Fetch secrets
    secrets = get_secret(f"wireguard/config/{target_region}", target_region)
    if not secrets:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve secrets from AWS"})
        }
    firebaseSecrets = get_secret("FirebaseServiceAccount", "us-west-1")
    if not firebaseSecrets:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed retrieving secrets from AWS"})
        }

    vpn_image_id = secrets.get("VPN_IMAGE_ID")
    key_name = secrets.get("KEY_NAME")
    security_group_id = secrets.get("SECURITY_GROUP_ID")
    subnet_id = secrets.get("SUBNET_ID")
    client_private_key = secrets.get("CLIENT_PRIVATE_KEY")
    server_public_key = secrets.get("SERVER_PUBLIC_KEY")
    
    # Verify token
    initialize_firebase(firebaseSecrets)
    user_id = verify_firebase_token(token)
    if not user_id:
        return {"statusCode": 403, "body": json.dumps({"error": "Invalid or expired token"})}
    role = get_user_role(user_id)
    if not role: 
        return {"statusCode": 403, "body": json.dumps({"error": "No user role found"})}
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
        
    if not vpn_image_id or not security_group_id or not key_name:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Missing required secret values"})
        }

    # Check if Image exists
    image_id = check_image_exists(target_region, vpn_image_id)
    if "Image does not exist in region" in image_id or "Error checking Image" in image_id:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": image_id})
        }
        
    # Clean Up up other instances:
    if CLEANUP_VPNS:
        shutdown_all_other_instances(live_regions)

    # Deploy the EC2 instance
    result = deploy_instance(target_region, image_id, instance_name, security_group_id, subnet_id, key_name)
    if not result:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to deploy instance"})
        }
    instance_id, public_ip = result

    if not public_ip:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve instance public IP"})
        }
    if not instance_id:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve instance ID"})
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "public_ipv4": public_ip,
            "client_private_key": client_private_key,
            "server_public_key": server_public_key
        })
    }