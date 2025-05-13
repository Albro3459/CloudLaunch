import firebase_admin
from firebase_admin import credentials, auth, firestore

from datetime import datetime, timezone

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
    
def get_all_user_ids():
    try:
        db = firestore.client()
        users = db.collection("Users").stream()
        return [user.id for user in users]
    except Exception as e:
        print(f"Error fetching user IDs: {e}")
        return []
    
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

# Get the live regions from Firestore
def get_live_regions():
    try:
        db = firestore.client()
        docs = db.collection("Live-Regions").stream()
        regions = [{"name": doc.to_dict().get("name"), "value": doc.id} for doc in docs]
        regions.sort(key=lambda r: r["name"].lower())
        return regions
    except Exception as e:
        print(f"Error fetching live regions from Firestore: {e}")
        return []

def get_users_instances(user_id):
    try:
        db = firestore.client()
        regions_ref = db.collection("Users").document(user_id).collection("Regions")
        regions = regions_ref.stream()

        region_instances_map = {}

        for region_doc in regions:
            region_id = region_doc.id
            instances_ref = regions_ref.document(region_id).collection("Instances")
            query = instances_ref.where("status", "!=", "terminated")
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


    
def add_instance_to_firebase(uid, region, instance_id, ipv4, instanceName):
    try:
        db = firestore.client()
        instance_ref = (
            db.collection("Users")
                .document(uid)
              .collection("Regions")
                .document(region)
              .collection("Instances")
              . document(instance_id)
        )
        
        instance_data = {
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "ipv4": ipv4,
            "name": instanceName,
            "status": "running"
        }
        
        instance_ref.set(instance_data)
        print(f"Instance {instance_id} saved for user {uid} in region {region}.")
    except Exception as e:
        print(f"Error saving instance: {e}")
        
def update_instance_status(uid, region, instance_id, status):
    try:
        db = firestore.client()
        instance_ref = (
            db.collection("Users")
                .document(uid)
              .collection("Regions")
                .document(region)
              .collection("Instances")
              . document(instance_id)
        )   
             
        instance_ref.update({"status": status})
        print(f"Instance {instance_id} in region {region} updated for user {uid}.")
    except Exception as e:
        print(f"Error updating instance status: {e}")
        
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

        
def batch_update_all_users_instances(status="terminated"):
    try:
        db = firestore.client()
        users = db.collection("Users").stream()

        for user in users:
            region_instances = get_users_instances(user.id)
            
            # Map to ids
            region_instance_map = {
                region: [instance["id"] for instance in instances]
                for region, instances in region_instances.items()
            }
            
            if region_instance_map:
                print(f"Updating {len(region_instance_map)} instances for user {user.id}")
                batch_update_instance_statuses(user.id, region_instance_map, status)
            else:
                print(f"No active instances to update for user {user.id}")
    except Exception as e:
        print(f"Error in batch update loop: {e}")