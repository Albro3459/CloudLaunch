import boto3
import json
import time
from botocore.exceptions import ClientError

# Function to retrieve secrets from AWS Secrets Manager
def get_secret(secret_name, region_name="us-west-1"):
    """Retrieve a secret from AWS Secrets Manager."""
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager', region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])  # Convert JSON string to dictionary
    except ClientError as e:
        print(f"Error retrieving secret {secret_name}: {e}")
        return None

# Function to check if an AMI exists in the target region
def check_ami_exists(target_region, ami_name):
    """Check if an AMI exists in the target region. If not, return a message."""
    ec2 = boto3.client("ec2", region_name=target_region)

    try:
        response = ec2.describe_images(Owners=["self"])
        for image in response["Images"]:
            if image["Name"] == ami_name:
                print(f"AMI {ami_name} exists in {target_region}: {image['ImageId']}")
                return image["ImageId"]
    except ClientError as e:
        print(f"Error checking AMI in {target_region}: {e}")
        return f"Error checking AMI in {target_region}"

    print(f"AMI {ami_name} does not exist in {target_region}.")
    return f"Does not exist in region {target_region}"

# Function to deploy an EC2 instance
def deploy_instance(target_region, ami_id, instance_name, security_group_id, vpn_key):
    """Deploy an EC2 instance and return its public IP."""
    ec2 = boto3.client("ec2", region_name=target_region)

    try:
        response = ec2.run_instances(
            ImageId=ami_id,
            InstanceType="t2.micro",
            MinCount=1,
            MaxCount=1,
            SecurityGroupIds=[security_group_id],
            KeyName= vpn_key,
            TagSpecifications=[
                {
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": instance_name}]
                }
            ]
        )

        instance_id = response["Instances"][0]["InstanceId"]
        print(f"Instance {instance_id} launched in {target_region}")

        # Wait for the instance to get a public IP
        time.sleep(20)  # Avoid immediate API call spam
        while True:
            instance_info = ec2.describe_instances(InstanceIds=[instance_id])
            public_ip = instance_info["Reservations"][0]["Instances"][0].get("PublicIpAddress")
            if public_ip:
                print(f"Instance {instance_id} has public IP: {public_ip}")
                return public_ip
            time.sleep(5)

    except ClientError as e:
        print(f"Error launching instance in {target_region}: {e}")
        return None

# Lambda handler function
def lambda_handler(event, context):
    """
    Handles incoming Lambda requests.
    Expects 'region', 'ami_name', and 'instance_name' in event payload.
    """
    target_region = event.get("region", "").strip()
    ami_name = event.get("ami_name", "").strip()
    instance_name = event.get("instance_name", "").strip()
    input_token = event.get("token", "").strip()

    # Validate input
    if not target_region or not ami_name or not instance_name:
        return {"error": "Missing required parameters: region, ami_name, instance_name"}

    # Fetch secrets
    secrets = get_secret("VPN-Config", target_region)
    if not secrets:
        return {"error": "Failed to retrieve secrets from AWS"}

    vpn_instance_id = secrets.get("VPN_INSTANCE_ID")
    vpn_key = secrets.get("VPN_KEY")
    security_group_id = secrets.get("SECURITY_GROUP_ID")
    token = secrets.get("TOKEN")

    if token != input_token:
        return {"error": "Invalid token"}

    if not vpn_instance_id or not security_group_id not vpn_key:
        return {"error": "Missing required secret values"}

    # Step 1: Check if AMI exists
    ami_id = check_ami_exists(target_region, ami_name)

    if "Does not exist in region" in ami_id or "Error checking AMI" in ami_id:
        return {"error": ami_id}  # Return error if AMI does not exist

    # Step 2: Deploy the EC2 instance
    public_ip = deploy_instance(target_region, ami_id, instance_name, security_group_id, vpn_key)

    if not public_ip:
        return {"error": "Failed to retrieve instance public IP"}

    return {
        "instance_name": instance_name,
        "public_ip": public_ip
    }
