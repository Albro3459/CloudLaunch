import boto3

def get_enabled_regions():
    # Returns the AWS region names that are enabled

    ec2 = boto3.client("ec2")

    try:
        response = ec2.describe_regions(AllRegions=False)
        # We only need RegionName.
        return [r["RegionName"] for r in response["Regions"]]
    except Exception as e:
        print(f"Error checking enabled regions: {e}")
        raise # Actually fail

def supports_instance_in_region(region, instance_type):
    # Returns True if instance_type is supported in the region

    ec2 = boto3.client("ec2", region_name=region)

    try:
        response = ec2.describe_instance_type_offerings(
            LocationType="region",
            Filters=[
                {
                    "Name": "instance-type",
                    "Values": [instance_type]
                }
            ],
            MaxResults=1  # We only care if at least one exists
        )

        # If there are any results, then it is supported
        return len(response.get("InstanceTypeOfferings", [])) > 0
    except Exception as e:
        print(f"Error checking if {region} supports {instance_type}: {e}")
        return False