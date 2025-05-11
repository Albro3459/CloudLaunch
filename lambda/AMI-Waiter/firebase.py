import firebase_admin
from firebase_admin import credentials, auth, firestore

REGION_NAME_MAP = {
    "us-east-1": "Virginia",
    "us-east-2": "Ohio",
    "us-west-1": "California",
    "us-west-2": "Oregon",
    "ap-southeast-4": "Australia (Melbourne)",
    "ap-southeast-2": "Australia (Sydney)",
    "sa-east-1": "Brazil",
    "ca-central-1": "Canada",
    "eu-west-3": "France",
    "eu-central-1": "Germany",
    "ap-east-1": "Hong Kong",
    "ap-south-2": "India (Hyderabad)",
    "ap-south-1": "India (Mumbai)",
    "ap-southeast-3": "Indonesia",
    "eu-west-1": "Ireland",
    "ap-northeast-3": "Japan (Osaka)",
    "ap-northeast-1": "Japan (Tokyo)",
    "ap-southeast-1": "Singapore",
    "af-south-1": "South Africa",
    "ap-northeast-2": "South Korea",
    "eu-south-1": "Spain",
    "eu-north-1": "Sweden",
    "me-central-1": "United Arab Emirates",
    "eu-west-2": "United Kingdom",
}

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
        doc_ref = db.collection("Users").document(uid)
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
