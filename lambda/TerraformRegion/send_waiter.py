import json
import requests

def send_waiter_request(region, ami_id, request_url, token):
    """
    Sends a POST request to the Waiter API to wait for the AMI to become available.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "ami_id": ami_id,
        "region": region
    }
    try:
        response = requests.post(
            request_url, 
            headers=headers, 
            data=json.dumps(payload), 
            timeout=1 # add a timeout because we are calling and moving on
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        # No need to process result — we're ignoring it for now
    except requests.exceptions.Timeout:
        print("Waiter API call successfully timed out (as expected). Moving on.")
    except Exception as e:
        print(f"Waiter API Error: {str(e)}")