import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

## This works too, but Simple is simpler :)
# def build_raw_email(region, sender, recipient):
#     subject = f"Region {region} is now live!"
#     body_text = f"The WireGuard AMI is now live in region: {region}"

#     msg = MIMEMultipart()
#     msg['Subject'] = subject
#     msg['From'] = sender
#     msg['To'] = recipient
#     msg['Date'] = email.utils.formatdate()
#     msg['Message-ID'] = email.utils.make_msgid()
#     msg['Reply-To'] = sender

#     body = MIMEText(body_text, 'plain')
#     msg.attach(body)

#     return msg.as_bytes()

# def send_email(ses_client, region, sender, recipient):
#     raw_email = build_raw_email(region, sender, recipient)
#     try:
#         response = ses_client.send_email(
#             FromEmailAddress=sender,
#             Destination={
#                 'ToAddresses': [recipient]
#             },
#             Content={
#                 'Raw': {
#                     'Data': raw_email
#                 }
#             }
#         )
        # print(f"Email sent from {sender} to {recipient}.")
        # print(f"Email message ID: {response['MessageId']}")
#         return response
#     except Exception as e:
#         print(f"Error sending email: {e}")
#         return None

def send_email(ses_client, region, sender, recipient):
    subject = f"Region {region} is now live!"
    body_text = f"From VPN Deployer,\n\nThe WireGuard AMI is now live in region: {region}\n\nEnjoy!"

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
