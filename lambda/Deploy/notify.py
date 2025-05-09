from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config_helper import get_config, build_QR_code

def get_timestamp():
    central = ZoneInfo("America/Chicago")
    now = datetime.now(central)
    tz_label = now.tzname()
    timestamp = now.strftime(f"%Y-%m-%d %a %I:%M:%S %p ({tz_label})")
    return timestamp

def send_VPN_email(ses_client, region, sender, recipient, ip_address, config="", qr_code=""):
    # Get current time in UTC with timezone info
    timestamp = get_timestamp()
    
    subject = f"VPN is now live in {region}!"
    body_text = (
        f"From CloudLaunch,\n\n"
        f"The WireGuard VPN is now live in region: {region}\n\n"
        f"IPv4: {ip_address}\n\n"
        f"Timestamp: {timestamp}\n\n"
        f"Enjoy!"
    )
    try:
        response = ses_client.send_email(
            FromEmailAddress=sender,
            Destination={
                'ToAddresses': [recipient]
            },
            Content={
                'Simple': {
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Text': {
                            'Data': body_text,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            }
        )
        print(f"Email sent from {sender} to {recipient}.")
        print(f"Email message ID: {response['MessageId']}")
        return response
    except Exception as e:
        print(f"Error sending email: {e}")
        return None
    
def deliver_emails(ses_client, client_private_key, server_public_key, ip_address, region, SENDER, emails):
    config = get_config(client_private_key, server_public_key, ip_address)
    if not config:
        print(f"Failed to get Config for {ip_address}")
        return None
        
    qr_code = build_QR_code(config)
    if not config:
        print(f"Failed to build QR Code for {qr_code}")
        return None
    
    for recipient in emails:
        print(f"Delivering email to {recipient}")
        send_VPN_email(ses_client, region, SENDER, recipient, ip_address, config, qr_code)