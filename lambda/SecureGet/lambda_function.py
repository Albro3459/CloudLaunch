import json

from firebase import initialize_firebase, verify_firebase_token, get_user_role
from get_secrets import (
    SecretSection,
    VpnSecretKey,
    get_cloudlaunch_secret,
    get_secret_section,
    get_secret_value,
)

AWS_REGION = "us-west-1"

def lambda_handler(event, context):
    """
    An API to securely get secrets from AWS
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
    requested_keys = body.get("requested_keys", [])

    # Validate input
    if not requested_keys or not isinstance(requested_keys, list):
        print(f"Missing parameters: {requested_keys}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing parameters"})
        }

    # Fetch secrets
    cloudlaunch_secret = get_cloudlaunch_secret(AWS_REGION)
    if not cloudlaunch_secret:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve secrets from AWS"})
        }
    try:
        firebaseSecrets = get_secret_section(cloudlaunch_secret, SecretSection.FIREBASE)
        vpn_config = get_secret_section(cloudlaunch_secret, SecretSection.VPN)
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
    
    
    # Return allowed secret values
    result = {}
    for key in requested_keys:
        if key == "client_private_key":
            result[key] = get_secret_value(vpn_config, VpnSecretKey.CLIENT_PRIVATE_KEY)
        elif key == "server_public_key":
            result[key] = get_secret_value(vpn_config, VpnSecretKey.SERVER_PUBLIC_KEY)
        else:
            result[key] = None # Explicitly show unknown keys

    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
