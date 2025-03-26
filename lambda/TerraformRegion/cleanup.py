import boto3
from firebase import remove_live_region

def terminate_old_vpn_instances(region, tag_value='VPN-*'):
    ec2 = boto3.resource("ec2", region_name=region)
    filters = [
        {"Name": "instance-state-name", "Values": ["running", "pending"]},
        {"Name": "tag:Name", "Values": [tag_value]}
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
    return True

def delete_snapshots(ec2, snapshot_ids):
    for snapshot_id in snapshot_ids:
        try:
            ec2.delete_snapshot(SnapshotId=snapshot_id)
            print(f"Deleted snapshot: {snapshot_id}")
        except Exception as e:
            print(f"Failed to delete snapshot {snapshot_id}: {e}")
            return False
    return True

def deregister_AMIs(ec2, vpn_name='VPN'):
    # Deregister (delete) all AMIs that have "VPN" in the Name
    images = ec2.describe_images(Owners=['self'])['Images']
    vpn_images = [img for img in images if 'Name' in img and vpn_name in img['Name']]

    snapshot_ids = []

    for image in vpn_images:
        image_id = image['ImageId']
        print(f"Processing AMI: {image_id} ({image['Name']})")

        # Get all snapshots associated with the image
        for bd in image.get('BlockDeviceMappings', []):
            ebs = bd.get('Ebs')
            if ebs and 'SnapshotId' in ebs:
                snapshot_ids.append(ebs['SnapshotId'])

        # Deregister the AMI
        try:
            ec2.deregister_image(ImageId=image_id)
            print(f"Deregistered AMI: {image_id}")
        except Exception as e:
            print(f"Failed to deregister AMI {image_id}: {e}")
            return False

    # Delete related snapshots
    return delete_snapshots(ec2, snapshot_ids)
    
def delete_security_groups(ec2, group_name='wireguard-security_group'):
    sgs = ec2.describe_security_groups()['SecurityGroups']
    for sg in sgs:
        if sg['GroupName'] == 'default':
            continue
        if sg['GroupName'] == group_name:
            try:
                ec2.delete_security_group(GroupId=sg['GroupId'])
                print(f"Deleted Security Group: {sg['GroupId']}")
            except Exception as e:
                print(f"Failed to delete Security Group {sg['GroupId']}: {e}")
                return False
    return True
            
def delete_VPCs(ec2, tag_key='Name', tag_value='wireguard-vpc'):
    vpcs = ec2.describe_vpcs(
        Filters=[
            {'Name': f'tag:{tag_key}', 'Values': [tag_value]}
        ]
    )['Vpcs']
    
    for vpc in vpcs:
        vpc_id = vpc['VpcId']
        try:
            # Must delete subnets, gateways, etc. before VPC deletion
            ec2_resource = boto3.resource('ec2', region_name=ec2.meta.region_name)
            vpc_resource = ec2_resource.Vpc(vpc_id)

            # Detach and delete Internet Gateways
            for igw in vpc_resource.internet_gateways.all():
                vpc_resource.detach_internet_gateway(InternetGatewayId=igw.id)
                igw.delete()

            # Delete subnets
            for subnet in vpc_resource.subnets.all():
                subnet.delete()

            # Delete route tables (except main)
            for rt in vpc_resource.route_tables.all():
                is_main = False
                for assoc in rt.associations_attribute:
                    if assoc.get('Main'):
                        is_main = True
                    else:
                        try:
                            ec2.disassociate_route_table(AssociationId=assoc['RouteTableAssociationId'])
                            print(f"Disassociated Route Table: {rt.id}")
                        except Exception as e:
                            print(f"Failed to disassociate RT {rt.id}: {e}")
                            return False
                if not is_main:
                    try:
                        ec2.delete_route_table(RouteTableId=rt.id)
                        print(f"Deleted Route Table: {rt.id}")
                    except Exception as e:
                        print(f"Failed to delete RT {rt.id}: {e}")
                        return False

            # Delete the VPC
            vpc_resource.delete()
            print(f"Deleted VPC: {vpc_id}")
        except Exception as e:
            print(f"Failed to delete VPC {vpc_id}: {e}")
            return False
    return True

def cleanup_region(region, source_region):
    if region == source_region:
        print(f"Cannot cleanup source region")
        return
    
    ec2 = boto3.client('ec2', region_name=region)
    
    # ORDER MATTERS
    
    print(f"Terminating EC2s in {region}")
    A = terminate_old_vpn_instances(region, 'VPN-*')
    
    print(f"Deregistering AMIs and deleting Snapshots in {region}")
    B = deregister_AMIs(ec2, 'VPN')
        
    print(f"Deleting Security Groups in {region}")
    C = delete_security_groups(ec2, 'wireguard-security_group')
    
    print(f"Deleting VPCs, Subnets, IGWs, and Route Tables in {region}")
    D = delete_VPCs(ec2, 'Name', 'wireguard-vpc')
    
    if A and B and C and D:
        print(f"Removing region {region} from Live-Regions collection")
        remove_live_region(region)
        return True
    
    print(f"Cleanup failed for region {region}")
    return False