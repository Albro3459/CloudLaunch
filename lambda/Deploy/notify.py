from datetime import datetime
from zoneinfo import ZoneInfo

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication

from config_helper import get_config, build_QR_code

def get_timestamp():
    central = ZoneInfo("America/Chicago")
    now = datetime.now(central)
    tz_label = now.tzname()
    timestamp = now.strftime(f"%m/%d/%Y %a %I:%M %p ({tz_label})")
    return timestamp

def send_VPN_email(ses_client, region, sender, recipient, ip_address, config, qr_code):
    timestamp = get_timestamp()

    subject = f"VPN is live in {region}!"
    body_text = (
        f"Your VPN is live in: {region}\n\n"
        f"IPv4: {ip_address}\n\n"
        f"Timestamp: {timestamp}\n\n"
        f"Enjoy!"
    )

    # Create MIME message
    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    # Body part
    body = MIMEText(body_text, 'plain')
    msg.attach(body)

    # WireGuard config
    part = MIMEApplication(config.encode('utf-8'))
    part.add_header('Content-Disposition', 'attachment', filename='wireguard.conf')
    msg.attach(part)

    # QR code
    img = MIMEImage(qr_code, name='qrcode.png')
    img.add_header('Content-ID', '<qrcode_image>')
    img.add_header('Content-Disposition', 'inline', filename='qrcode.png')
    msg.attach(img)

    try:
        response = ses_client.send_email(
            FromEmailAddress=sender,
            Destination={'ToAddresses': [recipient]},
            Content={
                'Raw': {'Data': msg.as_string()}
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