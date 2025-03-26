import firebase_admin
from firebase_admin import credentials, auth, firestore

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
    
def remove_live_region(region):
    """
    Removes the given region from the 'Live-Regions' Firestore collection.
    """
    try:
        db = firestore.client()
        doc_ref = db.collection("Live-Regions").document(region)
        doc_ref.delete()
        print(f"Region '{region}' removed from Live-Regions.")
        return True
    except Exception as e:
        print(f"Error removing region from Firestore: {e}")
        return False