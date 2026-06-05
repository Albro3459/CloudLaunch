import json
from firebase_admin import auth, firestore

from firebase import initialize_firebase, verify_firebase_token, get_user_role
from get_secrets import (
    CloudflareSecretKey,
    SecretSection,
    get_cloudlaunch_secret,
    get_secret_section,
    get_secret_value,
)

AWS_REGION = "us-west-1"
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 4096
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

def validate_password(password):
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters long"
    if len(password) > PASSWORD_MAX_LENGTH:
        return f"Password must be no more than {PASSWORD_MAX_LENGTH} characters long"
    if not any(char.isupper() for char in password):
        return "Password must include an uppercase character"
    if not any(char.islower() for char in password):
        return "Password must include a lowercase character"
    if not any(char.isdigit() for char in password):
        return "Password must include a numeric character"
    if not any(not char.isalnum() for char in password):
        return "Password must include a special character"
    return None

def create_auth_user(email, password):
    try:
        user = auth.create_user(email=email, password=password)
        return user.uid
    except auth.EmailAlreadyExistsError as e:
        print("Error: User already exists:", e)
        return auth.EmailAlreadyExistsError
    except Exception as e:
        print("Error creating auth user:", e)
        return None

def create_firestore_user(uid, email):
    try:
        db = firestore.client()
        db.collection("Users").document(uid).set({"email": email})
        db.collection("Roles").document(uid).set({"role": "user"})
        
        return True
    except Exception as e:
        print("Error creating firestore user:", e)
        return False

def lambda_handler(event, context):
    """
    Creates new user with a user role
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
    email = body.get("email", "").strip()
    password = body.get("password", "")
    if not isinstance(password, str):
        password = ""

    # Validate input
    if not email or not password or not token or \
        len(email) == 0 or len(password) == 0 or len(token) == 0:
        print(f"Missing required parameters: {email}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required parameters"})
        }
    password_error = validate_password(password)
    if password_error:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": password_error})
        }

    try:
        firebaseSecrets = get_secret_section(cloudlaunch_secret, SecretSection.FIREBASE)
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
    if role != "admin": 
        return {"statusCode": 403, "body": json.dumps({"error": "Error: Not admin role"})}
    
    
    uuid = create_auth_user(email, password)
    if not uuid:
        print(f"Failed to create user: {email}")
        return {"statusCode": 403, "body": json.dumps({"error": f"Failed to create user"})}
    success = create_firestore_user(uuid, email)
    if not success:
        if uuid == auth.EmailAlreadyExistsError:
            print(f"Error: Account already exists for user: {email}")
            return {"statusCode": 403, "body": json.dumps({"error": f"Error: Account already exists for user"})}
        
        print(f"Failed to create role for user: {email}")
        return {"statusCode": 403, "body": json.dumps({"error": f"Failed to create role for user"})}

    return {
        "statusCode": 200,
        "body": json.dumps({
            "uuid_created": uuid
        })
    }
