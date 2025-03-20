import boto3
import json
import time
from botocore.exceptions import ClientError

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
                    "Tags": [{"Key": "Name", "Value": instance_name}]
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

def lambda_handler(event, context):
    """
    Handles incoming Lambda requests
    Takes in 'region', 'instance_name', and 'token' in event
    """
    target_region = event.get("region", "").strip()
    instance_name = event.get("instance_name", "").strip()
    input_token = event.get("token", "").strip()
    
    ## TEMPORARY RESTRICTION
    target_region = 'us-west-1'

    # Validate input
    if not target_region or not instance_name or not input_token or \
        len(target_region) == 0 or len(instance_name) == 0 or len(input_token) == 0:
        return {"error": "Missing required parameters"}

    # Fetch secrets
    secrets = get_secret("VPN-Config", target_region)
    if not secrets:
        return {"error": "Failed to retrieve secrets from AWS"}

    vpn_image_id = secrets.get("VPN_IMAGE_ID")
    key_name = secrets.get("KEY_NAME")
    security_group_id = secrets.get("SECURITY_GROUP_ID")
    subnet_id = secrets.get("SUBNET_ID")
    token = secrets.get("TOKEN")

    if token != input_token:
        return {"error": "Invalid token"}

    if not vpn_image_id or not security_group_id or not key_name:
        return {"error": "Missing required secret values"}

    # Check if Image exists
    image_id = check_image_exists(target_region, vpn_image_id)

    if "Does not exist in region" in image_id or "Error checking AMI" in image_id:
        return {"error": image_id}  # Return error if AMI does not exist

    # Deploy the EC2 instance
    public_ip = deploy_instance(target_region, image_id, instance_name, security_group_id, subnet_id, key_name)

    if not public_ip:
        return {"error": "Failed to retrieve instance public IP"}

    return {
        "instance_name": instance_name,
        "public_ip": public_ip
    }
