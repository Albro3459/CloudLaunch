import json
from firebase_admin import auth, firestore

from firebase import initialize_firebase, verify_firebase_token, get_user_role
from get_secrets import get_secret

SOURCE_REGION = "us-west-1"

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
    email = body.get("email", "").strip()
    password = body.get("password", "").strip()

    # Validate input
    if not email or not password or not token or \
        len(email) == 0 or len(password) == 0 or len(token) == 0:
        print(f"Missing required parameters: {email}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required parameters"})
        }

    # Fetch secrets
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