"""
Email notification service using SMTP.

Credentials come exclusively from environment variables (via config).
If SMTP is not configured, notifications are recorded as FAILED and can be
retried later. No secrets are hard-coded.
"""
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

import streamlit as st

from audit_service import log_action
from config import (
    EMAIL_ENABLED,
    EMAIL_FROM,
    EMAIL_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USE_TLS,
    SMTP_USER,
)
from database import get_session
from models import Notification
from utils import generate_id


def _make_message(to_email, subject, body, attachment_path=None) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((EMAIL_FROM_NAME, EMAIL_FROM))
    msg["To"] = to_email
    msg.set_content(body)
    if attachment_path:
        try:
            with open(attachment_path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="application",
                    subtype="pdf",
                    filename=attachment_path.split("/")[-1].split("\\")[-1],
                )
        except OSError:
            pass
    return msg


def _smtp_send(msg: EmailMessage) -> None:
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        if SMTP_USE_TLS:
            server.starttls()
            server.ehlo()
        if SMTP_USER:
            server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)


def _record_notification(recipient, recipient_type, email_address, subject,
                         certificate_id=None, appointment_id=None,
                         status="Pending", failure_reason=None,
                         sent_now=None):
    """Record a notification row. Returns the notification object."""
    db = get_session()
    try:
        notif = Notification(
            notification_no=generate_id("NOT"),
            certificate_id=certificate_id,
            appointment_id=appointment_id,
            recipient=recipient,
            recipient_type=recipient_type,
            email_address=email_address,
            subject=subject,
            sent_at=sent_now,
            status=status,
            failure_reason=failure_reason,
        )
        db.add(notif)
        db.commit()
        return notif
    except Exception:  # noqa: BLE001
        db.rollback()
        return None
    finally:
        db.close()


def send_email(recipient, recipient_type, email_address, subject, body,
               attachment_path=None, certificate_id=None, appointment_id=None):
    """Send an email and record a notification. Never raises.

    Returns (success: bool, message: str, notification_id: int|None).
    """
    if not EMAIL_ENABLED:
        notif = _record_notification(
            recipient, recipient_type, email_address, subject,
            certificate_id=certificate_id, appointment_id=appointment_id,
            status="Failed",
            failure_reason="SMTP not configured. Add credentials to .env to enable email.",
        )
        log_action("EMAIL_FAILED", "email", record_id=appointment_id or certificate_id,
                   details="SMTP not configured")
        nid = notif.id if notif else None
        return False, "SMTP not configured. Notification recorded for retry.", nid

    try:
        msg = _make_message(email_address, subject, body, attachment_path)
        _smtp_send(msg)
        now = __import__("datetime").datetime.utcnow()
        notif = _record_notification(
            recipient, recipient_type, email_address, subject,
            certificate_id=certificate_id, appointment_id=appointment_id,
            status="Sent", sent_now=now,
        )
        log_action("EMAIL_SENT", "email", record_id=appointment_id or certificate_id,
                   details=f"email to {recipient_type} ({email_address})")
        nid = notif.id if notif else None
        return True, f"Email sent to {email_address}", nid
    except Exception as exc:  # noqa: BLE001
        notif = _record_notification(
            recipient, recipient_type, email_address, subject,
            certificate_id=certificate_id, appointment_id=appointment_id,
            status="Failed", failure_reason=str(exc)[:300],
        )
        log_action("EMAIL_FAILED", "email", record_id=appointment_id or certificate_id,
                   details=f"Delivery error for {recipient_type}")
        nid = notif.id if notif else None
        return False, "Email delivery failed. Please retry.", nid


# ---------------------------------------------------------------------------
# High-level email builders
# ---------------------------------------------------------------------------
def send_appointment_confirmation(student, doctor, appointment):
    subject = f"Appointment Confirmed – {appointment.appointment_no}"
    body = (
        f"Dear {student.full_name},\n\n"
        f"Your appointment has been booked successfully.\n\n"
        f"Appointment ID: {appointment.appointment_no}\n"
        f"Doctor: Dr. {doctor.full_name}\n"
        f"Date: {appointment.appointment_date}\n"
        f"Time: {appointment.appointment_time}\n"
        f"Status: {appointment.status}\n\n"
        f"Please arrive 10 minutes early.\n\n"
        f"Regards,\nGujarat Vidyapith Health Centre"
    )
    return send_email(
        student.full_name, "student", student.user.email, subject, body,
        appointment_id=appointment.id,
    )

