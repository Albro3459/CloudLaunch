import json
from enum import StrEnum

import boto3
from botocore.exceptions import ClientError

SECRET_NAME = "CloudLaunch"

class SecretSection(StrEnum):
    AWS = "aws"
    FIREBASE = "firebase"
    OCI = "oci"
    VPN = "vpn"

class AwsSecretKey(StrEnum):
    SES_SENDER = "SES_SENDER"
    ADMIN_EMAIL = "ADMIN_EMAIL"

class OciSecretKey(StrEnum):
    REGION = "OCI_REGION"
    REGION_NAME = "OCI_REGION_NAME"
    USER_OCID = "OCI_USER_OCID"
    TENANCY_OCID = "OCI_TENANCY_OCID"
    FINGERPRINT = "OCI_FINGERPRINT"
    PRIVATE_KEY = "OCI_PRIVATE_KEY"
    COMPARTMENT_ID = "OCI_COMPARTMENT_ID"
    AVAILABILITY_DOMAIN = "OCI_AVAILABILITY_DOMAIN"
    SUBNET_ID = "OCI_SUBNET_ID"
    SOURCE_IMAGE_ID = "OCI_SOURCE_IMAGE_ID"
    SSH_AUTHORIZED_KEYS_JSON = "OCI_SSH_AUTHORIZED_KEYS_JSON"
    HASHED_PASSWORD = "OCI_HASHED_PASSWORD"
    INSTANCE_SHAPE = "OCI_INSTANCE_SHAPE"
    INSTANCE_MEMORY_GBS = "OCI_INSTANCE_MEMORY_GBS"
    INSTANCE_OCPUS = "OCI_INSTANCE_OCPUS"
    BOOT_VOLUME_SIZE_GBS = "OCI_BOOT_VOLUME_SIZE_GBS"
    BOOT_VOLUME_VPUS_PER_GB = "OCI_BOOT_VOLUME_VPUS_PER_GB"
    IPV6_SUBNET_CIDR = "OCI_IPV6_SUBNET_CIDR"

class VpnSecretKey(StrEnum):
    INTERFACE = "WG_INTERFACE"
    LISTEN_PORT = "WG_LISTEN_PORT"
    ADDRESS_V4 = "WG_ADDRESS_V4"
    ADDRESS_V6 = "WG_ADDRESS_V6"
    CLIENT_ADDRESS_V4 = "WG_CLIENT_ADDRESS_V4"
    CLIENT_ADDRESS_V6 = "WG_CLIENT_ADDRESS_V6"
    DNS_ADDRESS_V4 = "WG_DNS_ADDRESS_V4"
    DNS_ADDRESS_V6 = "WG_DNS_ADDRESS_V6"
    NETWORK_V4 = "WG_NETWORK_V4"
    NETWORK_V6 = "WG_NETWORK_V6"
    RATE_LIMIT = "WG_RATE_LIMIT"
    RATE_LIMIT_BURST = "WG_RATE_LIMIT_BURST"
    SERVER_PRIVATE_KEY = "WG_SERVER_PRIVATE_KEY"
    SERVER_PUBLIC_KEY = "WG_SERVER_PUBLIC_KEY"
    CLIENT_PRIVATE_KEY = "WG_CLIENT_PRIVATE_KEY"
    CLIENT_PUBLIC_KEY = "WG_CLIENT_PUBLIC_KEY"
    CLIENT_ALLOWED_IPS_V4 = "WG_CLIENT_ALLOWED_IPS_V4"
    CLIENT_ALLOWED_IPS_V6 = "WG_CLIENT_ALLOWED_IPS_V6"
    PEER_ALLOWED_IPV4 = "WG_PEER_ALLOWED_IPV4"
    PEER_ALLOWED_IPV6 = "WG_PEER_ALLOWED_IPV6"
    PEER_PERSISTENT_KEEPALIVE = "WG_PEER_PERSISTENT_KEEPALIVE"

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

def get_cloudlaunch_secret(region_name):
    return get_secret(SECRET_NAME, region_name)

def get_secret_section(secret_values: dict, section: SecretSection):
    value = (secret_values or {}).get(section.value)
    if isinstance(value, dict) and value:
        return value
    raise ValueError(f"Missing required secret section: {section.value}")

def get_secret_value(secret_values: dict, key: StrEnum):
    value = (secret_values or {}).get(key.value)
    if value not in (None, ""):
        return value
    raise ValueError(f"Missing required secret value for key: {key.value}")
