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
    
    
    
    
def map_users_to_instance_ids(region_instance_map):
    """
    Returns a map in the form:
    {
        "user_id_1": { "region1": ["i-1", "i-2"] },
        "user_id_2": { "region2": ["i-3"] }
    }
    """
    try:
        db = firestore.client()
        user_region_instance_map = {}
        users_ref = db.collection("Users")
        users = users_ref.stream()

        for user_doc in users:
            uid = user_doc.id

            try:
                user_map = {}
                regions = list(region_instance_map.keys())
                user_instances_by_region = get_users_instances(uid, target_regions=regions)

                for region, target_ids in region_instance_map.items():
                    user_instances = user_instances_by_region.get(region, [])
                    matched_ids = [inst["id"] for inst in user_instances if inst["id"] in target_ids]

                    if matched_ids:
                        user_map[region] = matched_ids

                if user_map:
                    user_region_instance_map[uid] = user_map

            except Exception as e:
                print(f"Error processing user {uid}: {e}")

        return user_region_instance_map

    except Exception as e:
        print(f"Error in map_users_to_instance_ids: {e}")
        return {}
    
def get_users_instances(user_id, target_regions=None):
    try:
        db = firestore.client()
        regions_ref = db.collection("Users").document(user_id).collection("Regions")

        if target_regions:
            regions = [regions_ref.document(r).get() for r in target_regions]
        else:
            regions = regions_ref.stream()

        region_instances_map = {}

        for region_doc in regions:
            if not region_doc.exists:
                continue
            region_id = region_doc.id
            instances_ref = regions_ref.document(region_id).collection("Instances")
            query = instances_ref.where("status", "in", ["Running", "Stopped"]) # Live statuses
            docs = query.stream()

            instances = []
            for doc in docs:
                data = doc.to_dict()
                instance = {
                    "id": doc.id,
                    "name": data.get("name"),
                    "status": data.get("status"),
                    "createdAt": data.get("createdAt"),
                    "ipv4": data.get("ipv4")
                }
                instances.append(instance)

            if instances:
                region_instances_map[region_id] = instances

        return region_instances_map
    except Exception as e:
        print(f"Error fetching running instances for user {user_id}: {e}")
        return {}

    
def batch_update_instance_statuses(uid, region_instance_map, status):
    """
    region_instance_map in the form: { "us-east1": ["i-1", "i-2"], "eu-west1": ["i-3"] }
    """
    try:
        db = firestore.client()
        batch = db.batch()

        for region, instance_ids in region_instance_map.items():
            instances_ref = (
                db.collection("Users")
                    .document(uid)
                  .collection("Regions")
                    .document(region)
                  .collection("Instances")
            )

            for instance_id in instance_ids:
                ref = instances_ref.document(instance_id)
                batch.update(ref, {"status": status})

        batch.commit()
        print(f"Batch updated status to '{status}' for instances in: {region_instance_map}")
    except Exception as e:
        print(f"Error in batch update: {e}")