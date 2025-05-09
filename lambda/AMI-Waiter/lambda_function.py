import json
import traceback
import boto3
import time
import firebase_admin
from firebase_admin import credentials, auth, firestore

from get_secrets import get_secret
from firebase import initialize_firebase, is_region_live, update_live_regions, verify_firebase_token, get_user_role
from notify import send_image_email, send_VPN_email
from configHelper import get_config, build_QR_code

SOURCE_REGION = "us-west-1"
SENDER="brodsky.alex22@gmail.com"
RECIPIENT="brodsky.alex22@gmail.com"

def check_for_image(ami_id, region, timeout=600, poll_interval=15):
    # Waits until AMI is live and sets the region to live in Firebase
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

def check_for_vpn(instance_name, region, timeout=600, poll_interval=15):
    """
    Waits for an EC2 instance with the given name tag to be running and assigned a public IPv4 address.
    Returns the public IPv4 address if found within timeout, else returns None.
    """
    ec2 = boto3.client("ec2", region_name=region)
    start_time = time.time()

    while (time.time() - start_time) < timeout:
        try:
            # Find instance by tag Name
            response = ec2.describe_instances(
                Filters=[
                    {"Name": "tag:Name", "Values": [instance_name]},
                    {"Name": "instance-state-name", "Values": ["running"]}
                ]
            )
            reservations = response.get("Reservations", [])
            if reservations and reservations[0]["Instances"]:
                instance = reservations[0]["Instances"][0]
                public_ip = instance.get("PublicIpAddress")
                if public_ip:
                    print(f"Instance {instance['InstanceId']} is running with public IP: {public_ip}")
                    return public_ip
                else:
                    print(f"Instance {instance['InstanceId']} is running but no public IP yet.")
            else:
                print(f"No running instance found with name: {instance_name}")
        except Exception as e:
            print(f"Error checking instance status: {e}")
            return None

        attempt = int((time.time() - start_time) / poll_interval) + 1
        elapsed = round(time.time() - start_time, 2)
        print(f"[Attempt {attempt}] | Elapsed: {elapsed}s | Still waiting for public IP...")
        time.sleep(poll_interval)

    print(f"Timeout: Instance {instance_name} did not get a public IP in time.")
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
    wait_type = body.get("wait_type", "").strip()
    region = body.get("region", "").strip()
    email = body.get("email", "").strip()
    if not wait_type or not region or not email:
        print(f"Missing type, region, or email parameters: {wait_type}, {region}, {email}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required parameters: {wait_type}, {region}, {email}"})
        }
        
    secret_name = f"wireguard/config/{SOURCE_REGION}"
    secrets = get_secret(secret_name, SOURCE_REGION)
    if not secrets:
        raise Exception(f"Secret {secret_name} not found")
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
    

    if wait_type.lower() == "vpn":
        instance_name = body.get("instance_name", "").strip()
        email = body.get("email", "").strip()
        if not instance_name or not email:
            print("Missing instance name or email parameters.")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Missing required parameters: {instance_name}, {email}"})
            }
        
        ip_address = check_for_vpn(instance_name, region)
        if not ip_address:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Failed to wait for VPN: {instance_name}"})
            }
            
        client_private_key = secrets.get("CLIENT_PRIVATE_KEY")
        server_public_key = secrets.get("SERVER_PUBLIC_KEY")

        config = get_config(client_private_key, server_public_key, ip_address)
        if not config:
            print("Config failed to be created")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Failed to create config."})
            }

        qr_code = build_QR_code(config)
        if not qr_code:
            print("QR code failed to generate")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Failed to generate QR code."})
            }
        
        emails = [email]
        emails.append(RECIPIENT)
        ses_client = boto3.client('sesv2', region_name=SOURCE_REGION)
        for recipient in emails:
            if not send_VPN_email(ses_client, region, SENDER, recipient, ip_address, config, qr_code):
                print(f"Email failed to send to {recipient}")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": f"Failed to send email."})
                }
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "ip_address": ip_address,
                "email": email,
                "region": region
            })
        }


    elif wait_type.lower() == "image":
        ami_id = body.get("ami_id", "").strip()
        print(f"AMI ID: {ami_id}, Region: {region}")
        if not ami_id:
            print("Missing required ami_id parameter.")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": f"Missing required parameter: {ami_id}"})
            }
        try:            
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
            if not send_image_email(ses_client, region, SENDER, RECIPIENT):
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
            
    print("Failed to specify type")
    return {
        "statusCode": 400,
        "body": json.dumps({"error": f"Failed to specify type."})
    }