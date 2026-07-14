"""
Email notifications via Gmail SMTP (app password auth).

Two emails are sent per property submission:
  - An internal notification to admin@kairoco.co.uk with full submission
    details and the Drive folder link.
  - A short confirmation to the property owner with their Property ID.

Email failures are logged but never raise — a slow/broken mail server
should not cause an otherwise-successful submission to fail. See the
router for how this is handled.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger("kairoco.email")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


def _send(to_address: str, subject: str, html_body: str) -> None:
    settings = get_settings()

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.GMAIL_ADDRESS
    message["To"] = to_address
    message.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(settings.GMAIL_ADDRESS, settings.GMAIL_APP_PASSWORD)
        server.sendmail(settings.GMAIL_ADDRESS, to_address, message.as_string())


def send_admin_notification(
    *,
    property_id: str,
    full_name: str,
    email: str,
    phone: str,
    property_address: str,
    bedrooms: int,
    guests: int,
    features: str,
    smoking_allowed: str,
    pets_allowed: str,
    drive_folder_link: str,
) -> None:
    settings = get_settings()
    subject = f"New Property Submission — {property_id}"
    body = f"""
    <h2>New Property Submission</h2>
    <p><strong>Property ID:</strong> {property_id}</p>
    <h3>Owner Details</h3>
    <ul>
      <li><strong>Name:</strong> {full_name}</li>
      <li><strong>Email:</strong> {email}</li>
      <li><strong>Phone:</strong> {phone}</li>
    </ul>
    <h3>Property Details</h3>
    <ul>
      <li><strong>Address:</strong> {property_address}</li>
      <li><strong>Bedrooms:</strong> {bedrooms}</li>
      <li><strong>Guests:</strong> {guests}</li>
      <li><strong>Features:</strong> {features or "—"}</li>
      <li><strong>Smoking Allowed:</strong> {smoking_allowed}</li>
      <li><strong>Pets Allowed:</strong> {pets_allowed}</li>
    </ul>
    <p><strong>Photos:</strong> <a href="{drive_folder_link}">{drive_folder_link}</a></p>
    """
    try:
        _send(settings.ADMIN_EMAIL, subject, body)
    except Exception:
        logger.exception("Failed to send admin notification email for %s", property_id)


def send_owner_confirmation(*, owner_email: str, owner_name: str, property_id: str) -> None:
    subject = "Kairoco — Your Property Submission Reference"
    body = f"""
    <p>Hi {owner_name},</p>
    <p>Thank you for submitting your property to Kairoco. Your reference number is:</p>
    <h2>{property_id}</h2>
    <p>Our team will review your submission and be in touch shortly.</p>
    <p>— Kairoco</p>
    """
    try:
        _send(owner_email, subject, body)
    except Exception:
        logger.exception("Failed to send owner confirmation email for %s", property_id)
