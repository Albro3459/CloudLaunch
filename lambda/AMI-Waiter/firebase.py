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
    
def is_region_live(region):
    """
    Checks if the given region exists in the 'Live-Regions' Firestore collection.
    """
    try:
        db = firestore.client()
        doc = db.collection("Live-Regions").document(region).get()
        return doc.exists
    except Exception as e:
        print(f"Error checking if region is live: {e}")
        return False
    
def update_live_regions(region):
    """
    Adds or updates the given region in the 'Live-Regions' Firestore collection.
    Uses a human-readable name if available.
    """
    try:
        db = firestore.client()
        region_name = REGION_NAME_MAP.get(region, region)
        doc_ref = db.collection("Live-Regions").document(region)
        doc_ref.set({
            "name": region_name
        })
        print(f"Region '{region}' added to Live-Regions with name '{region_name}'.")
        return True
    except Exception as e:
        print(f"Error updating live regions in Firestore: {e}")
        return False
