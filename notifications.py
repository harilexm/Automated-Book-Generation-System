"""
Email (SMTP) + MS Teams Webhook notifications.

Sends notifications on key events and logs them to Supabase.
Gracefully falls back to console output if channels are not configured.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import config
import db


def send_email(subject: str, body: str) -> bool:
    """
    Send an email notification via SMTP.
    Returns True if sent successfully, False otherwise.
    """
    if not config.EMAIL_CONFIGURED:
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = config.SMTP_USER
        msg["To"] = config.NOTIFICATION_EMAIL
        msg["Subject"] = f"[Book Generator] {subject}"

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.SMTP_USER, config.NOTIFICATION_EMAIL, msg.as_string())

        print(f"  [EMAIL] Sent: {subject}")
        return True

    except Exception as e:
        print(f"  [EMAIL ERROR] Failed to send email: {e}")
        return False


def send_teams_message(message: str) -> bool:
    """
    Send a notification to MS Teams via webhook.
    Returns True if sent successfully, False otherwise.
    """
    if not config.TEAMS_CONFIGURED:
        return False

    try:
        payload = {
            "text": f"📚 **Book Generator** — {message}"
        }
        response = requests.post(
            config.TEAMS_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        print(f"  [TEAMS] Sent: {message[:60]}...")
        return True

    except Exception as e:
        print(f"  [TEAMS ERROR] Failed to send Teams message: {e}")
        return False


def notify(book_id: str | None, event_type: str, message: str) -> None:
    """
    Send notifications via all configured channels and log to DB.

    Channels:
      - Email (SMTP) — if configured
      - MS Teams Webhook — if configured
      - Console — always (fallback)

    Args:
        book_id: Book ID for logging (can be None for system-level events)
        event_type: Event type (e.g., 'outline_ready', 'chapter_waiting', etc.)
        message: Human-readable notification message
    """
    print(f"\n  📢 [{event_type.upper()}] {message}")

    # Try Email
    email_sent = send_email(event_type.replace("_", " ").title(), message)
    if email_sent:
        try:
            db.log_notification(book_id, event_type, message, "email")
        except Exception:
            pass  # Don't fail if logging fails

    # Try Teams
    teams_sent = send_teams_message(message)
    if teams_sent:
        try:
            db.log_notification(book_id, event_type, message, "teams")
        except Exception:
            pass

    # Always log to console channel
    try:
        db.log_notification(book_id, event_type, message, "console")
    except Exception:
        pass  # DB might not be ready during testing

    if not email_sent and not teams_sent:
        print("  [INFO] No external notification channels configured. Logged to console only.")
        print("         Set SMTP or Teams Webhook credentials in .env to enable notifications.")