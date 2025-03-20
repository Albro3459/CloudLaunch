import boto3
import json
import time
from botocore.exceptions import ClientError
import firebase_admin
from firebase_admin import credentials, auth

# Get secrets from AWS
def get_secret(secret_name, region_name):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager', 
        region_name=region_name
    )
    try:
        response = client.get_secret_value(SecretId=secret_name)
        
        # Handle secrets stored as JSON strings or binary data
        if "SecretString" in response:
            return json.loads(response["SecretString"])  # Convert JSON string to dict
        elif "SecretBinary" in response:
            return response["SecretBinary"]  # No need to convert binary to 
        
    except ClientError as e:
        print(f"Error retrieving secret '{secret_name}': {e}")

    return None

def get_available_instance_name(ec2, instance_name):
    """
    Checks if an instance with the given base_name exists in that ec2 region.
    If it does, appends -1 to -15 to find an available name.
    Returns an available name or None if all 15 are taken.
    """
    existing_names = set()
    
    # Get all instances with 'instance_name'
    response = ec2.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [f"{instance_name}*"]}]
    )

    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            for tag in instance.get("Tags", []):
                if tag["Key"] == "Name":
                    existing_names.add(tag["Value"])

    # Try base name first
    if instance_name not in existing_names:
        return instance_name

    # Try appending -1 to -15
    for i in range(1, 16):
        new_name = f"{instance_name}-{i}"
        if new_name not in existing_names:
            return new_name

    return None

# Check if Image exists in the target region
def check_image_exists(target_region, image_id):
    ec2 = boto3.client("ec2", region_name=target_region)

    try:
        response = ec2.describe_images(
            Owners=["self"],
            Filters=[{"Name": "image-id", "Values": [image_id]}]
        )
        if response["Images"]:
            image = response["Images"][0]
            imageID = image["ImageId"]
            imageName = response["Images"][0].get("Name", "<no name>")  # Prevents KeyError
            print(f"Image {imageName or ''} exists in {target_region}: {imageID}")
            return imageID
            
        print(f"Image ID {image_id} does not exist in {target_region}.")
        return f"Does not exist in region {target_region}"

    except ClientError as e:
        print(f"Error checking Image in {target_region}: {e}")
        return f"Error checking Image in {target_region}"
    except KeyError:
        print(f"Unexpected response format when checking Image in {target_region}.")
        return f"Error checking Image in {target_region}"

def deploy_instance(target_region, image_id, instance_name, security_group_id, subnet_id, KeyName):
    """Deploy an EC2 instance and return its public IP address."""
    ec2 = boto3.client("ec2", region_name=target_region)
    
    instanceName = get_available_instance_name(ec2, instance_name)
    if not instanceName:
        return {"error": "All name variations are taken. Choose a different base name."}

    try:
        response = ec2.run_instances(
            ImageId=image_id,
            InstanceType="t2.micro",
            MinCount=1,
            MaxCount=1,
            SecurityGroupIds=[security_group_id],
            SubnetId=subnet_id,
            KeyName=KeyName, # ssh key
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": instanceName}]
                }
            ]
        )

        instance_id = response["Instances"][0]["InstanceId"]
        print(f"Instance {instance_id} launched in {target_region}")

        # Wait until the instance is running
        waiter = ec2.get_waiter("instance_running")
        waiter.wait(InstanceIds=[instance_id])
        
        # Wait for the public IP assignment
        max_retries, interval = 12, 5
        for _ in range(max_retries):
            reservations = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"]
            if reservations:
                instance = reservations[0]["Instances"][0]
                public_ip = instance.get("PublicIpAddress")
                if public_ip:
                    print(f"Instance {instance_id} has public IP: {public_ip}")
                    return public_ip
            print("Waiting for public IP assignment...")
            time.sleep(interval)
        
        print("Public IP address not assigned after retries.")
        return None
        
    except ClientError as e:
        print(f"Error launching instance in {target_region}: {e}")
        return None
    
# Initialize Firebase Admin SDK
def initialize_firebase(firebaseSecrets):
    if not firebase_admin._apps:  # Ensures Firebase is initialized only once
        cred = credentials.Certificate(firebaseSecrets)
        firebase_admin.initialize_app(cred)
    
# Verify Firebase JWT Token
def verify_firebase_token(token):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        print("Token verification failed:", e)
        return None

def lambda_handler(event, context):
    """
    Handles incoming Lambda requests
    Takes in 'region' and 'instance_name' in the event body
    Token is extracted from the 'Authorization' header
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
    target_region = body.get("region", "").strip()
    instance_name = body.get("instance_name", "").strip()
    
    ## TEMPORARY RESTRICTION
    target_region = 'us-west-1'

    # Validate input
    if not target_region or not instance_name or not token or \
        len(target_region) == 0 or len(instance_name) == 0 or len(token) == 0:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required parameters, {target_region}, {instance_name}"})
        }

    # Fetch secrets
    secrets = get_secret("VPN-Config", target_region)
    if not secrets:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve secrets from AWS"})
        }
    firebaseSecrets = get_secret("FirebaseServiceAccount", target_region)
    if not firebaseSecrets:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed retrieving secrets from AWS"})
        }

    vpn_image_id = secrets.get("VPN_IMAGE_ID")
    key_name = secrets.get("KEY_NAME")
    security_group_id = secrets.get("SECURITY_GROUP_ID")
    subnet_id = secrets.get("SUBNET_ID")
    client_private_key = secrets.get("CLIENT_PRIVATE_KEY")
    server_public_key = secrets.get("SERVER_PUBLIC_KEY")
    
    # Verify token
    if not firebase_admin._apps:
        initialize_firebase(firebaseSecrets) 
    user_data = verify_firebase_token(token)
    if not user_data:
        return {"statusCode": 403, "body": json.dumps({"error": "Invalid or expired token"})}
    

    if not vpn_image_id or not security_group_id or not key_name:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Missing required secret values"})
        }

    # Check if Image exists
    image_id = check_image_exists(target_region, vpn_image_id)

    if "Does not exist in region" in image_id or "Error checking Image" in image_id:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": image_id})
        }

    # Deploy the EC2 instance
    public_ip = deploy_instance(target_region, image_id, instance_name, security_group_id, subnet_id, key_name)

    if not public_ip:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve instance public IP"})
        }

    return {
        "statusCode": 200,
        "body": json.dumps({
            "public_ipv4": public_ip,
            "client_private_key": client_private_key,
            "server_public_key": server_public_key
        })
    }
