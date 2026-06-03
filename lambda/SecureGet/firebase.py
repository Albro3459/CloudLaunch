import firebase_admin
from firebase_admin import credentials, auth, firestore

from vpn_status import ACTIVE_VPN_STATUSES, normalize_vpn_status

# Initialize Firebase Admin SDK
def initialize_firebase(firebaseSecrets):
    if not firebase_admin._apps:  # Ensures Firebase is initialized only once
        cred = credentials.Certificate(firebaseSecrets)
        firebase_admin.initialize_app(cred)
    
# Verify Firebase JWT Token
def verify_firebase_token(token):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token.get("uid")
    except Exception as e:
        print("Token verification failed:", e)
        return None
    
# Get User Role from Firestore using UID
def get_user_role(uid):
    try:
        db = firestore.client()
        doc_ref = db.collection("Roles").document(uid)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return data.get("role", None) # None is the fallback
        else:
            print(f"No role found for UID: {uid}")
            return None
    except Exception as e:
        print("Error fetching role:", e)
        return None


def get_active_instance_count_for_region(region):
    try:
        db = firestore.client()
        users_ref = db.collection("Users")
        count = 0

        for user_doc in users_ref.stream():
            instances_ref = (
                users_ref
                .document(user_doc.id)
                .collection("Regions")
                .document(region)
                .collection("Instances")
            )

            for instance_doc in instances_ref.stream():
                instance = instance_doc.to_dict() or {}
                status = normalize_vpn_status(instance.get("status"))
                if status and status.value in ACTIVE_VPN_STATUSES:
                    count += 1

        return count
    except Exception as e:
        error_message = f"Error counting active instances for region {region}: {e}"
        print(error_message)
        raise RuntimeError(error_message) from e
