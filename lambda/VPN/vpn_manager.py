import time
import boto3
from botocore.exceptions import ClientError

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
    if instance_name not in existing_names and instance_name != "VPN":
        return instance_name

    # Try appending -1 to -50
    for i in range(1, 50):
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
        return f"Image does not exist in region {target_region}"

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
                    return instance_id, public_ip
            print("Waiting for public IP assignment...")
            time.sleep(interval)
        
        print("Public IP address not assigned after retries.")
        return None
        
    except ClientError as e:
        print(f"AWS ClientError: {e}")
        return None
    except BotoCoreError as e:
        print(f"AWS Core Error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error launching instance: {e}")
        return None
    
def shutdown_all_other_instances(LIVE_REGIONS):
    for region in [r["value"] for r in LIVE_REGIONS]:
        ec2 = boto3.resource("ec2", region_name=region)
        print(f"Checking region: {region}")
        terminate_old_vpn_instances(ec2)
    
    
def terminate_old_vpn_instances(ec2):
    filters = [
        {"Name": "instance-state-name", "Values": ["running", "pending"]},
        {"Name": "tag:Name", "Values": ["VPN-*"]}
    ]

    instances_to_terminate = []
    for instance in ec2.instances.filter(Filters=filters):
        print(f"Marking for termination: {instance.id} ({instance.public_ip_address})")
        instances_to_terminate.append(instance.id)

    if instances_to_terminate:
        ec2.instances.filter(InstanceIds=instances_to_terminate).terminate()
        print(f"Terminated instances: {instances_to_terminate}")
    else:
        print("No other instances to terminate.")
