import json

from config_helper import get_config, get_wireguard_config_options
from firebase import initialize_firebase, verify_firebase_token, get_user_role
from get_secrets import (
    CloudflareSecretKey,
    OciSecretKey,
    SecretSection,
    VpnSecretKey,
    get_cloudlaunch_secret,
    get_secret_section,
    get_secret_value,
)

AWS_REGION = "us-west-1"
VALID_REQUESTS = {"region", "config"}
WORKER_SECRET_HEADER = "x-cloudlaunch-worker-secret"


def _get_header(headers, name, default=""):
    target = name.lower()
    for header_name, header_value in headers.items():
        if header_name.lower() == target:
            return header_value
    return default


def _worker_secret_is_valid(headers, expected_secret):
    provided_secret = _get_header(headers, WORKER_SECRET_HEADER, "")
    return bool(expected_secret) and provided_secret == expected_secret

def lambda_handler(event, context):
    """
    An API to securely get secrets from AWS
    """
    headers = event.get("headers", {})

    cloudlaunch_secret = get_cloudlaunch_secret(AWS_REGION)
    if not cloudlaunch_secret:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve secrets from AWS"})
        }

    try:
        cloudflare_config = get_secret_section(cloudlaunch_secret, SecretSection.CLOUDFLARE)
        worker_secret = get_secret_value(cloudflare_config, CloudflareSecretKey.WORKER_SECRET)
    except ValueError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    if not _worker_secret_is_valid(headers, worker_secret):
        return {"statusCode": 403, "body": json.dumps({"error": "Forbidden"})}

    auth_header = _get_header(headers, "Authorization", "").strip()
    token = auth_header.replace("Bearer ", "")

    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON body"})
        }

    # Extract required values
    requested = (body.get("requested") or "").strip().lower()
    ip_addresses = body.get("ip_addresses") or {}

    # Validate input
    if requested not in VALID_REQUESTS:
        print(f"Missing or invalid request: {requested}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing or invalid request"})
        }

    try:
        firebaseSecrets = get_secret_section(cloudlaunch_secret, SecretSection.FIREBASE)
        oci_config = get_secret_section(cloudlaunch_secret, SecretSection.OCI)
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

    try:
        if requested == "region":
            result = {
                "region": {
                    "oci_region": get_secret_value(oci_config, OciSecretKey.REGION),
                    "oci_region_name": get_secret_value(oci_config, OciSecretKey.REGION_NAME),
                }
            }
        else:
            if not isinstance(ip_addresses, dict):
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid ip_addresses"})
                }

            public_ipv4 = (ip_addresses.get("public_ipv4") or "").strip()
            if not public_ipv4:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Missing public_ipv4"})
                }

            client_private_key = get_secret_value(vpn_config, VpnSecretKey.CLIENT_PRIVATE_KEY)
            server_public_key = get_secret_value(vpn_config, VpnSecretKey.SERVER_PUBLIC_KEY)
            wireguard_options = get_wireguard_config_options(vpn_config)
            result = {
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
    except ValueError as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    return {
        "statusCode": 200,
        "body": json.dumps(result)
    }
