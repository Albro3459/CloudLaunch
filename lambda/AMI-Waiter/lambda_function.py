import json
import traceback
import boto3
import time
import firebase_admin
from firebase_admin import credentials, auth, firestore

from get_secrets import get_secret
from firebase import initialize_firebase, is_region_live, update_live_regions, verify_firebase_token, get_user_role
from notify import send_email

SOURCE_REGION = "us-west-1"
SENDER="CloudLaunch <noreply@cloudlaunch.live>"
ADMIN="brodsky.alex22@gmail.com"

# Waits until AMI is live and sets the region to live in Firebase

def check_for_image(ami_id, region, timeout=600, poll_interval=15):
    """
    Poll for the AMI status for up to `timeout` seconds.
    Returns the AMI ID if it becomes available, otherwise returns None.
    """
    ec2 = boto3.client("ec2", region_name=region)
    start_time = time.time()
    
    while (time.time() - start_time) < timeout:
        try:
            response = ec2.describe_images(ImageIds=[ami_id])
            images = response.get('Images', [])
            state = "unknown"
            if not images:
                print(f"No images found for AMI ID: {ami_id}. Exiting...")
                return None
            else:
                state = images[0]['State']
                if state == "available":
                    print(f"AMI copy complete. AMI ID: {ami_id}")
                    return ami_id
        except Exception as e:
            print(f"Error checking image status: {e}")
            return None
            
        attempt = int((time.time() - start_time) / poll_interval) + 1
        elapsed = round(time.time() - start_time, 2)
        print(f"[Attempt {attempt}] | Elapsed: {elapsed}s | AMI state: {state}. Waiting...")
        time.sleep(poll_interval)
    
    print("Timeout: AMI did not become available within the expected time.")
    return None

def lambda_handler(event, context):
    # Checks if AMI is ready in region
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
    ami_id = body.get("ami_id", "").strip()
    region = body.get("region", "").strip()
    print(f"AMI ID: {ami_id}, Region: {region}")
    if not ami_id or not region or \
        len(ami_id) == 0 or len(region) == 0:
        print("Missing required parameters.")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required parameters, {ami_id}, {region}"})
        }
    try:
        secret_name = f"wireguard/config/{SOURCE_REGION}"
        secrets = get_secret(secret_name, SOURCE_REGION)
        if not secrets:
            raise Exception("Secret {secret_name} not found")
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
            print("Token verification failed.")
            return {"statusCode": 403, "body": json.dumps({"error": "Invalid or expired token"})}
        role = get_user_role(user_id)
        if not role: 
            print("No role found for user.")
            return {"statusCode": 403, "body": json.dumps({"error": "No user role found"})}
        if role != "admin":
            print(f"Unauthorized role: {role}")
            return {"statusCode": 403, "body": json.dumps({"error": "Unauthorized"})}
        
        if is_region_live(region):
            print(f"Region {region} already marked as live.")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "ami_id": ami_id,
                    "region": region
                })
            }
        
        if check_for_image(ami_id, region) != ami_id:
            print(f"AMI {ami_id} not available in {region}.")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"AMI {ami_id} not available in {region}"})
            }
            
        if not update_live_regions(region):
            print(f"Failed to update Firebase for region: {region}")
            return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Failed to update Firebase for: {region}"})
        }
            
        print(f"AMI ID: {ami_id} ready in Region: {region}")
        
        ses_client = boto3.client('sesv2', region_name=SOURCE_REGION)
        sent_email = send_email(ses_client, region, SENDER, ADMIN)
        if not sent_email:
            print("Email failed to send")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Failed to send email."})
            }
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "ami_id": ami_id,
                "region": region
            })
        }
        
    except Exception as e:
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "message": "Failed to bootstrap VPN region"
            })
        }