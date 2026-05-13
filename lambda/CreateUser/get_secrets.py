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
