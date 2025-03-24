import json
import traceback
import boto3
import time

from get_secrets import get_secret

# Terraforms a new region for VPN deployments

SOURCE_REGION = "us-west-1"

def check_if_ami_exists(ec2, base_name, max_attempts=50):
    """
    Checking existing images to see if it already exists
    """
    try:
        response = ec2.describe_images(
            Owners=['self'],
            Filters=[{"Name": "name", "Values": [base_name, f"{base_name}-*"]}]
        )

        for image in response.get("Images", []):
            name = image.get("Name", "")
            if name == base_name or name.startswith(f"{base_name}-"):
                print(f"Found existing AMI: {name} → {image['ImageId']}")
                return image["ImageId"]

        return ""
    except Exception as e:
        print(f"Error checking for existing AMIs: {e}")
        return None

def copy_image(target_region, source_vpn_image_id):
    ec2 = boto3.client("ec2", region_name=target_region)
    ami_name = f"{target_region}-VPN-image-EC2-v2"
    
    existing_image_id = check_if_ami_exists(ec2, ami_name)
    if existing_image_id != "":
        print(f"AMI Image in {target_region} already exists: {existing_image_id}")
        return existing_image_id
    
    try:
        response = ec2.copy_image(
            SourceRegion=SOURCE_REGION,
            SourceImageId=source_vpn_image_id,
            Name=ami_name
        )
        vpn_image_id = response['ImageId']
        print(f"Copying AMI to {target_region}, new AMI: {ami_name}, ID: {vpn_image_id}")

        # # Wait for AMI to become available
        # print("Waiting for AMI to become available...")
        # waiter = ec2.get_waiter('image_available')
        # waiter.wait(ImageIds=[vpn_image_id])
        # print(f"AMI copy complete. AMI ID: {vpn_image_id}")
        
        return vpn_image_id
    except Exception as e:
        print(f"Failed to copy AMI: {e}")
        return None

def create_VPC(region):
    ec2 = boto3.client("ec2", region_name=region)

    # Step 1: Create VPC with IPv4 + IPv6
    vpc_response = ec2.create_vpc(
        CidrBlock='172.31.0.0/16',
        AmazonProvidedIpv6CidrBlock=True,
        InstanceTenancy='default'
    )

    vpc_id = vpc_response['Vpc']['VpcId']
    print(f"Created VPC: {vpc_id}")

    # Enable DNS
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsSupport={'Value': True})

    # Tag VPC
    ec2.create_tags(Resources=[vpc_id], Tags=[{'Key': 'Name', 'Value': 'wireguard-vpc'}])

    # Get assigned IPv6 CIDR
    describe = ec2.describe_vpcs(VpcIds=[vpc_id])
    ipv6_cidr = describe['Vpcs'][0]['Ipv6CidrBlockAssociationSet'][0]['Ipv6CidrBlock']
    print(f"IPv6 CIDR Block: {ipv6_cidr}")

    # Internet Gateway
    igw = ec2.create_internet_gateway()
    ec2.attach_internet_gateway(InternetGatewayId=igw['InternetGateway']['InternetGatewayId'], VpcId=vpc_id)

    # Subnet with both IPv4 + IPv6
    subnet_id = create_subnet(ec2, vpc_id, ipv6_cidr)

    # Route Table
    route_table = ec2.create_route_table(VpcId=vpc_id)
    route_table_id = route_table['RouteTable']['RouteTableId']
    ec2.create_route(RouteTableId=route_table_id, DestinationCidrBlock='0.0.0.0/0', GatewayId=igw['InternetGateway']['InternetGatewayId'])
    ec2.create_route(RouteTableId=route_table_id, DestinationIpv6CidrBlock='::/0', GatewayId=igw['InternetGateway']['InternetGatewayId'])
    ec2.associate_route_table(RouteTableId=route_table_id, SubnetId=subnet_id)

    # Enable auto-assign public IPv4 + IPv6
    ec2.modify_subnet_attribute(SubnetId=subnet_id, MapPublicIpOnLaunch={"Value": True})
    ec2.modify_subnet_attribute(SubnetId=subnet_id, AssignIpv6AddressOnCreation={"Value": True})

    print(f"VPC/Subnet/IGW setup complete in {region}")
    return vpc_id, subnet_id

def create_subnet(ec2, vpc_id, ipv6_cidr):
    # Use the first /64 from the /56 block
    base_ipv6 = ipv6_cidr.replace("::/56", "::/64")

    subnet = ec2.create_subnet(
        VpcId=vpc_id,
        CidrBlock='172.31.1.0/24',
        Ipv6CidrBlock=base_ipv6,
        AvailabilityZone=ec2.describe_availability_zones()['AvailabilityZones'][0]['ZoneName']
    )
    subnet_id = subnet['Subnet']['SubnetId']
    print(f"Created Subnet: {subnet_id} with IPv6 block: {base_ipv6}")
    return subnet_id
    
def create_security_group(region, vpc_id):
    ec2 = boto3.client("ec2", region_name=region)
    security_group = ec2.create_security_group(
        GroupName="wireguard-security_group",
        Description="Allow WireGuard and SSH (IPv4 + IPv6)",
        VpcId=vpc_id
    )
    security_group_id = security_group['GroupId']

    ec2.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            # WireGuard UDP 51820 (IPv4 + IPv6)
            {
                'IpProtocol': 'udp',
                'FromPort': 51820,
                'ToPort': 51820,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                'Ipv6Ranges': [{'CidrIpv6': '::/0'}]
            },
            # SSH TCP 22 (IPv4 + IPv6)
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                'Ipv6Ranges': [{'CidrIpv6': '::/0'}]
            }
        ]
    )
    print(f"Security Group created: {security_group_id}")
    return security_group_id

def import_key_pair(region, key_name, public_key_material):
    ec2 = boto3.client('ec2', region_name=region)
    
    try:
        response = ec2.import_key_pair(
            KeyName=key_name,
            PublicKeyMaterial=public_key_material.encode('utf-8')
        )
        print(f"Key pair '{key_name}' imported in {region}")
        return response['KeyName']
    except ec2.exceptions.ClientError as e:
        if "InvalidKeyPair.Duplicate" in str(e):
            print(f"Key pair '{key_name}' already exists in {region} — skipping import")
            return key_name
        else:
            raise
        
def create_secrets_manager(region, values_dict):
    secrets = boto3.client('secretsmanager', region_name=region)
    secret_name = f"wireguard/config/{region}"
    secret_string = json.dumps(values_dict)

    try:
        response = secrets.create_secret(
            Name=secret_name,
            SecretString=secret_string
        )
        print(f"Secret created: {secret_name}")
        return response['ARN']

    except secrets.exceptions.ResourceExistsException:
        print(f"Secret already exists: {secret_name} — updating instead...")
        response = secrets.update_secret(
            SecretId=secret_name,
            SecretString=secret_string
        )
        print(f"Secret updated: {secret_name}")
        return response['ARN']


def lambda_handler(event, context):
    # Terraforms a new region for VPN deployments
    # headers = event.get("headers", {})
    # auth_header = headers.get("Authorization", headers.get("authorization", "")).strip() # AWS is case-sensitive
    # token = auth_header.replace("Bearer ", "")
    
    try:
        body = json.loads(event.get("body", "{}"))
        print("EVENT:", json.dumps(event))
        print("BODY:", json.dumps(body))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON body"})
        }

    # Extract required values
    target_region = body.get("target_region", "").strip()
    print("TARGET REGION:", target_region)
    if not target_region or \
        len(target_region) == 0:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Missing required parameters: {target_region}"})
        }
    try:
        secrets = get_secret("VPN-Config", SOURCE_REGION)
        if not secrets:
            raise Exception("Secret 'VPN-Config' not found")

        source_vpn_image_id = secrets.get("VPN_IMAGE_ID")
        source_key_name = secrets.get("KEY_NAME")
        # source_security_group_id = secrets.get("SECURITY_GROUP_ID")
        # source_subnet_id = secrets.get("SUBNET_ID")
        source_client_private_key = secrets.get("CLIENT_PRIVATE_KEY")
        source_server_public_key = secrets.get("SERVER_PUBLIC_KEY")
        source_public_key_material = secrets.get("PUBLIC_KEY_MATERIAL")

        # --- Step 1: Copy AMI ---
        new_vpn_image_id = copy_image(target_region, source_vpn_image_id)
        if not new_vpn_image_id:
            raise Exception("AMI Image couldn't be created")

        # --- Step 2: Create VPC, Subnet, IGW, Route Table ---
        vpc_id, subnet_id = create_VPC(target_region)

        # --- Step 3: Create Security Group ---
        security_group_id = create_security_group(target_region, vpc_id)
        
        # --- Step 3: Import SSH Key ---
        import_key_pair(target_region, source_key_name, source_public_key_material)

        # --- Step 5: Create Secret in Secrets Manager ---
        secret_data = {
            "VPN_IMAGE_ID": new_vpn_image_id,
            "SECURITY_GROUP_ID": security_group_id,
            "SUBNET_ID": subnet_id,
            "KEY_NAME": source_key_name,
            "CLIENT_PRIVATE_KEY": source_client_private_key,
            "SERVER_PUBLIC_KEY": source_server_public_key
        }
        secrets_manager_arn = create_secrets_manager(target_region, secret_data)

        # --- Step 5: Output Summary ---
        print("\n=== Region Setup Summary ===")
        print(f"AMI Image ID: {new_vpn_image_id}")
        print(f"VPC ID: {vpc_id}")
        print(f"Subnet ID: {subnet_id}")
        print(f"Security Group ID: {security_group_id}")
        print(f"Secret Manager ARN: {secrets_manager_arn}")
        
        return {
            "statusCode": 200,
            "body": {
                "region": target_region,
                "vpn_image_id": new_vpn_image_id,
                "subnet_id": subnet_id,
                "security_group_id": security_group_id,
                "secret_arn": secrets_manager_arn
            }
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
