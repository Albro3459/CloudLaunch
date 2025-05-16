import json
import time
import boto3
from botocore.exceptions import ClientError

from firebase import add_instance_to_firebase, batch_update_all_instances

def get_available_instance_name(ec2, user_id):
    """
    Find an available instance name
    """
    existing_names = set()
    
    instance_name = "VPN-" + user_id
    
    # Get all instances with 'instance_name'
    response = ec2.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [f"{instance_name}*"]}]
    )

    for reservation in response.get("Reservations", []):
        for instance in reservation.get("Instances", []):
            for tag in instance.get("Tags", []):
                if tag["Key"] == "Name":
                    existing_names.add(tag["Value"])
                    
    # Find the largest number and add 1
    nums = []
    for name in existing_names:
        if name.startswith(instance_name + "-"):
            try:
                num = int(name.split("-")[-1])
                nums.append(num)
            except Exception:
                continue  # ignore non-numbers
              
    num = max(nums) + 1 if len(nums) >= 1 else 1
    
    return f"{instance_name}-{num}"

# Check if Image exists in the target region
def check_image_exists(ec2, target_region, image_id):
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

def deploy_instance(user_id, ec2, target_region, image_id, security_group_id, subnet_id, KeyName):
    """Deploy an EC2 instance and return its public IP address."""
    
    instanceName = get_available_instance_name(ec2, user_id)
    if not instanceName:
        # This will probably never get hit
        print("No VPN name available.")
        return None

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
                    # Save the instance to firebase
                    add_instance_to_firebase(user_id, target_region, instance_id, public_ip, instanceName)
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
    
def restart_instance(user_id, ec2, target_region, instance_id, instance_name):
    """
    Restart a stopped EC2 instance and return its new public IP.
    """
    try:
        ec2.start_instances(InstanceIds=[instance_id])
        print(f"Start request sent for instance {instance_id}")

        # Wait for running state
        waiter = ec2.get_waiter("instance_running")
        waiter.wait(InstanceIds=[instance_id])

        # Wait for public IP to be assigned
        max_retries, interval = 12, 5
        for _ in range(max_retries):
            reservations = ec2.describe_instances(InstanceIds=[instance_id])["Reservations"]
            if reservations:
                instance = reservations[0]["Instances"][0]
                public_ip = instance.get("PublicIpAddress")
                if public_ip:
                    print(f"Instance {instance_id} restarted with public IP: {public_ip}")
                    return instance_id, public_ip
            print("Waiting for public IP assignment...")
            time.sleep(interval)

        print("Public IP not assigned after retries.")
        return None

    except ClientError as e:
        print(f"AWS ClientError: {e}")
        return None
    except BotoCoreError as e:
        print(f"AWS Core Error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error restarting instance: {e}")
        return None
    
## Clean up
def terminate_all_other_instances(LIVE_REGIONS):
    for region in [r["value"] for r in LIVE_REGIONS]:
        ec2 = boto3.client("ec2", region_name=region)
        print(f"Checking region: {region}")
        terminate_old_vpn_instances(ec2)
    batch_update_all_instances("terminated")
    
    
def terminate_old_vpn_instances(ec2):
    filters = [
        {"Name": "instance-state-name", "Values": ["running", "pending"]},
        {"Name": "tag:Name", "Values": ["VPN-*"]}
    ]

    response = ec2.describe_instances(Filters=filters)

    instance_ids = [
        instance["InstanceId"]
        for reservation in response["Reservations"]
        for instance in reservation["Instances"]
    ]

    if instance_ids:
        print(f"Terminating instances: {instance_ids}")
        ec2.terminate_instances(InstanceIds=instance_ids)
    else:
        print("No other instances to terminate.")
        
def batch_update_aws_instances(action, region_instance_map, user_id):
    """
    Used to update multiple instances across multiple regions
    
    Actions are: Stop, Start, or Terminate
    
    region_instance_map (dict): Mapping of regions to lists of instance IDs.
                        Example: {'us-west-1': ['i-123', 'i-456'], 'us-east-1': ['i-789']}
    """
    
    if action not in {"start", "stop", "terminate"}:
        raise ValueError("Invalid action. Must be 'start', 'stop', or 'terminate'.")

    for region, instance_ids in region_instance_map.items():
        ec2 = boto3.client('ec2', region_name=region)

        if not instance_ids:
            continue
        
        try:
            if action == "start":
                for instance_id in instance_ids:
                    restart_instance(user_id, ec2, region, instance_id)
            elif action == "stop":
                ec2.stop_instances(InstanceIds=instance_ids)
            elif action == "terminate":
                ec2.terminate_instances(InstanceIds=instance_ids)

            print(f"{action.capitalize()} request sent for instances in {region}: {instance_ids}")

        except Exception as e:
            print(f"Error in {region} for {action}: {e}")
