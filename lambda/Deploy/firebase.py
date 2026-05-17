import firebase_admin
from firebase_admin import credentials, auth, firestore

from datetime import datetime, timezone

from vpn_status import ACTIVE_VPN_STATUSES, VPNStatus, normalize_vpn_status


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _get_region_ref(uid, region):
    db = firestore.client()
    return (
        db.collection("Users")
          .document(uid)
          .collection("Regions")
          .document(region)
    )


def _ensure_region_exists(region_ref):
    # Firestore subcollections behave more predictably when the parent doc exists.
    region_ref.set({"created": firestore.SERVER_TIMESTAMP}, merge=True)


def _get_instance_ref(uid, region, instance_id):
    region_ref = _get_region_ref(uid, region)
    return region_ref, region_ref.collection("Instances").document(instance_id)

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

def get_users_instances(user_id, regions_filter=None):
    try:
        db = firestore.client()
        regions_ref = db.collection("Users").document(user_id).collection("Regions")

        if regions_filter:
            regions = [regions_ref.document(r).get() for r in regions_filter]
        else:
            regions = regions_ref.stream()

        region_instances_map = {}

        for region_doc in regions:
            if not region_doc.exists:
                continue
            region_id = region_doc.id
            instances_ref = regions_ref.document(region_id).collection("Instances")
            query = instances_ref.where("status", "in", ACTIVE_VPN_STATUSES)
            docs = query.stream()

            instances = []
            for doc in docs:
                data = doc.to_dict()
                status = normalize_vpn_status(data.get("status"))
                if not status:
                    continue
                instance = {
                    "id": doc.id,
                    "name": data.get("name"),
                    "status": status,
                    "createdAt": data.get("createdAt"),
                    "ipv4": data.get("ipv4"),
                    "wireguardConfig": data.get("wireguardConfig"),
                }
                instances.append(instance)

            if instances:
                region_instances_map[region_id] = instances

        return region_instances_map
    except Exception as e:
        print(f"Error fetching running instances for user {user_id}: {e}")
        return {}
    
def get_user_instances_in_region(user_id, role, region):
    # Returns 1+ VPNs (region_instance_map) in the requested region or None

    # Commenting this out because the Admin doesn't want to get back another user's VPN when trying to create a new one, they only want their own.
    # The Admin can see the other user's VPNs in the table
    # if role == "admin":
    #     usersIDs = get_all_user_ids()
        
    #     for uid in usersIDs:
    #         region_instances_map = get_users_instances(uid, [region])
    #         if region_instances_map:
    #             # Just need there to be at least 1 in the region
    #             return region_instances_map
            
    #     return None
    
    # else:
        region_instances = get_users_instances(user_id, [region])
        return region_instances if region_instances else None


def get_instance(uid, region, instance_id):
    try:
        _, instance_ref = _get_instance_ref(uid, region, instance_id)
        doc = instance_ref.get()
        if not doc.exists:
            return None

        data = doc.to_dict() or {}
        data["id"] = doc.id
        data["status"] = normalize_vpn_status(data.get("status"))
        return data
    except Exception as e:
        print(f"Error fetching instance {instance_id}: {e}")
        return None


def upsert_stack_backed_instance_record(uid, region, stack_id, instance_name):
    region_ref, instance_ref = _get_instance_ref(uid, region, stack_id)
    _ensure_region_exists(region_ref)

    instance_ref.set({
        "createdAt": _utc_now_iso(),
        "instanceOcid": None,
        "ipv4": None,
        "lastError": None,
        "name": instance_name,
        "status": VPNStatus.PENDING.value,
    }, merge=True)
    print(f"Stack-backed instance record {stack_id} saved for user {uid} in region {region}.")


def attach_instance_ocid(uid, region, stack_id, instance_ocid):
    region_ref, instance_ref = _get_instance_ref(uid, region, stack_id)
    _ensure_region_exists(region_ref)

    instance_ref.set({
        "instanceOcid": instance_ocid,
        "lastError": None,
    }, merge=True)
    print(f"Instance OCID attached to record {stack_id} for user {uid} in region {region}.")


def mark_instance_running(uid, region, stack_id, ipv4):
    region_ref, instance_ref = _get_instance_ref(uid, region, stack_id)
    _ensure_region_exists(region_ref)

    instance_ref.set({
        "ipv4": ipv4,
        "lastError": None,
        "status": VPNStatus.RUNNING.value,
    }, merge=True)
    print(f"Instance record {stack_id} marked Running for user {uid} in region {region}.")


def save_instance_wireguard_config(uid, region, instance_id, wireguard_config):
    region_ref, instance_ref = _get_instance_ref(uid, region, instance_id)
    _ensure_region_exists(region_ref)

    instance_ref.set({
        "wireguardConfig": wireguard_config,
    }, merge=True)
    print(f"WireGuard config saved for instance {instance_id} in region {region} for user {uid}.")


def mark_instance_failed(uid, region, stack_id, error_message):
    region_ref, instance_ref = _get_instance_ref(uid, region, stack_id)
    _ensure_region_exists(region_ref)

    instance_ref.set({
        "lastError": error_message,
        "status": VPNStatus.FAILED.value,
    }, merge=True)
    print(f"Instance record {stack_id} marked Failed for user {uid} in region {region}.")


def mark_instance_terminated(uid, region, instance_id):
    region_ref, instance_ref = _get_instance_ref(uid, region, instance_id)
    _ensure_region_exists(region_ref)

    instance_ref.set({
        "lastError": None,
        "status": VPNStatus.TERMINATED.value,
        "terminatedAt": _utc_now_iso(),
    }, merge=True)
    print(f"Instance {instance_id} in region {region} marked Terminated for user {uid}.")


def record_instance_cleanup_error(uid, region, instance_id, error_message):
    region_ref, instance_ref = _get_instance_ref(uid, region, instance_id)
    _ensure_region_exists(region_ref)

    instance_ref.set({
        "lastError": error_message,
    }, merge=True)
    print(f"Cleanup error recorded for instance {instance_id} in region {region} for user {uid}.")


def update_instance_status(uid, region, instance_id, status):
    try:
        normalized_status = normalize_vpn_status(status)
        if not normalized_status:
            raise ValueError(f"Invalid VPN status: {status}")

        _, instance_ref = _get_instance_ref(uid, region, instance_id)

        instance_ref.update({"status": normalized_status.value})
        print(f"Instance {instance_id} in region {region} updated for user {uid}.")
    except Exception as e:
        print(f"Error updating instance status: {e}")
        
def batch_update_instance_statuses(uid, region_instance_map, status):
    """
    region_instance_map in the form: { "us-east1": ["i-1", "i-2"], "eu-west1": ["i-3"] }
    """
    try:
        normalized_status = normalize_vpn_status(status)
        if not normalized_status:
            raise ValueError(f"Invalid VPN status: {status}")

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
                batch.update(ref, {"status": normalized_status.value})

        batch.commit()
        print(f"Batch updated status to '{normalized_status.value}' for instances in: {region_instance_map}")
    except Exception as e:
        print(f"Error in batch update: {e}")

        
def batch_update_all_instances(status):
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
