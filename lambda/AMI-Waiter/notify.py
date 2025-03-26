from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_timestamp():
    pacific = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific)
    tz_label = now.tzname()
    timestamp = now.strftime(f"%Y-%m-%d %H:%M:%S ({tz_label})")
    return timestamp

def send_email(ses_client, region, sender, recipient):
    # Get current time in UTC with timezone info
    timestamp = get_timestamp()
    
    subject = f"Region {region} is now live!"
    body_text = (
        f"From VPN Deployer,\n\n"
        f"The WireGuard AMI is now live in region: {region}\n\n"
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
