import json
import boto3
from collections import defaultdict

from vpn_manager import batch_update_aws_instances, check_image_exists, deploy_instance, terminate_all_other_instances
from role_manager import get_max_count_for_role, get_user_vpn_count, increment_user_count
from firebase import batch_update_instance_statuses, get_user_instances_in_region, get_live_regions, get_users_instances, initialize_firebase, verify_firebase_token, get_user_role
from get_secrets import get_secret
from notify import deliver_emails

CLEANUP_VPNS = True
SOURCE_REGION = "us-west-1"
SENDER="CloudLaunch <noreply@cloudlaunch.live>"
ADMIN="brodsky.alex22@gmail.com"
VALID_ACTIONS = {"deploy", "terminate"}

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
    if not target_region and action.lower() == "terminate":
        secrets = get_secret(f"wireguard/config/{SOURCE_REGION}", SOURCE_REGION)
    else:
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
        
    # Perform Action        

    if action.lower() == "terminate":
        if role != "admin":
            return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}
        if not targets or not isinstance(targets, dict):
            print(f"Invalid or missing targets: {targets}")
            return {"statusCode": 400, "body": json.dumps({"error": "Invalid or missing targets"})}

        
        # targets = {
        #     "userID": {
        #         "us-west-1": ["i-0123"],
        #         "us-east-1": ["i-0456"]
        #     }
        # }
        
        print(f"User {user_id}: terminating {targets}")
        
        # defaultdict(...) to avoid missing key errors
        region_instance_map = defaultdict(list)
        for uid, regions in targets.items():
            for region, instance_ids in regions.items():
                region_instance_map[region].extend(instance_ids)

        # dict(defaultdict) converts to regular dict
        batch_update_aws_instances(action.lower(), dict(region_instance_map))
        
        # Call Firestore update per user
        for uid, region_map in targets.items():
            batch_update_instance_statuses(uid, region_map, "Terminated")
            
        return {
            "statusCode": 200,
            "body": json.dumps({
                "action_completed": action.lower()
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
            
        if not vpn_image_id or not security_group_id or not key_name:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Missing required secret values"})
            }
        
        
        ec2 = boto3.client("ec2", region_name=target_region)

        # Check if Image exists
        image_id = check_image_exists(ec2, target_region, vpn_image_id)
        if "Image does not exist in region" in image_id or "Error checking Image" in image_id:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": image_id})
            }
                    
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
                
        # Clean Up other instances:
        if CLEANUP_VPNS:
            # Terminate all instances for all users
            # Also update statuses for all users instances in Firestore
            terminate_all_other_instances(live_regions)

        # Deploy the EC2 instance
        result = deploy_instance(user_id, ec2, target_region, image_id, security_group_id, subnet_id, key_name)
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
            
        # Send emails
        ses_client = boto3.client('sesv2', region_name=SOURCE_REGION)
        emails = [email]
        if email != ADMIN:
            emails.append(ADMIN)
        
        deliver_emails(ses_client, client_private_key, server_public_key, public_ip, target_region, SENDER, emails)

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