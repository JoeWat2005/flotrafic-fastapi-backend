import os
import smtplib
from email.message import EmailMessage

EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_FROM = os.getenv("EMAIL_FROM")

EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "false").lower() == "true"


def send_email(to: str, subject: str, body: str):
    if not EMAIL_ENABLED:
        print("📧 EMAIL (dev mode)")
        print("To:", to)
        print("Subject:", subject)
        print("📧 Body hidden in dev mode")
        print("📧 END EMAIL")
        return

    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
