import json
from firebase_admin import auth, firestore

from firebase import initialize_firebase, verify_firebase_token, get_user_role
from get_secrets import get_secret
from aws import get_enabled_regions, supports_instance_in_region, get_supported_regions

SOURCE_REGION = "us-west-1"

def lambda_handler(event, context):
    """
    An API to securely get secrets and live regions from AWS
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
    live_regions = body.get("live_regions", False)
    requested_keys = body.get("requested_keys", [])

    # Validate input
    get_live_regions = isinstance(live_regions, bool)
    get_requested_keys = isinstance(requested_keys, list) and len(requested_keys) > 0
    if not get_live_regions or not get_requested_keys:
        if not get_live_regions:
            print(f"Missing param: {live_regions}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Missing param"})
            }
        else:
            print(f"Missing parameters: {requested_keys}")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Missing parameters"})
            }
        
    # Fetch secrets
    secrets = get_secret(f"wireguard/config/{SOURCE_REGION}", SOURCE_REGION)
    if not secrets:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve secrets from AWS"})
        }
    firebaseSecrets = get_secret("FirebaseServiceAccount", SOURCE_REGION)
    if not firebaseSecrets:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed retrieving secrets from AWS"})
        }
    
    # Verify token
    initialize_firebase(firebaseSecrets) 
    user_id = verify_firebase_token(token)
    if not user_id:
        return {"statusCode": 403, "body": json.dumps({"error": "Invalid or expired token"})}
    role = get_user_role(user_id)
    if not role: 
        return {"statusCode": 403, "body": json.dumps({"error": "No user role found"})}
    
    if get_live_regions:
        # Fetch live regions
        instance_type = "t2.micro"
        
        supported_regions = get_supported_regions(instance_type)

        print(f"Instance type {instance_type} is supported in these regions:")
        for r in supported_regions:
            print(r)

        return {
            "statusCode": 200,
            "body": json.dumps(supported_regions)
        }

    elif get_requested_keys:       
        # Get requested AWS Secrets
        result = {}
        for key in requested_keys:
            if key == "client_private_key":
                result[key] = secrets.get("CLIENT_PRIVATE_KEY")
            elif key == "server_public_key":
                result[key] = secrets.get("SERVER_PUBLIC_KEY")
            else:
                result[key] = None # Explicitly show unknown keys

        return {
            "statusCode": 200,
            "body": json.dumps(result)
        }