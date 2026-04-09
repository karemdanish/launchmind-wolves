from dotenv import load_dotenv
load_dotenv()

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

try:
    msg = Mail(
        from_email=os.environ["SENDGRID_FROM_EMAIL"],
        to_emails=os.environ["TEST_EMAIL"],
        subject="LaunchMind Test Email",
        html_content="<p>If you see this, SendGrid is working! ✅</p>"
    )

    sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
    r = sg.send(msg)

    print(f"Status: {r.status_code}")

except Exception as e:
    print(f"Error: {str(e)}")