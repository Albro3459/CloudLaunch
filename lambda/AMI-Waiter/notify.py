from datetime import datetime
from zoneinfo import ZoneInfo

def get_timestamp():
    central = ZoneInfo("America/Chicago")
    now = datetime.now(central)
    tz_label = now.tzname()
    timestamp = now.strftime(f"%m/%d/%Y %a %I:%M %p ({tz_label})")
    return timestamp

def send_email(ses_client, region, sender, recipient):
    # Get current time in UTC with timezone info
    timestamp = get_timestamp()
    
    subject = f"Region {region} is live!"
    body_text = (
        f"The WireGuard AMI is live in: {region}\n\n"
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
