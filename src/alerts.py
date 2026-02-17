"""
Alerts module for Supply Chain Resilience Agent.
Sends email (Resend/SMTP) and optional SMS (Twilio) when supply chain risks are detected.
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_env() -> None:
    """Load .env if python-dotenv is available."""
    try:
        from pathlib import Path

        from dotenv import load_dotenv

        project_root = Path(__file__).resolve().parent.parent
        load_dotenv(project_root / ".env")
    except ImportError:
        pass


def is_configured() -> dict[str, bool]:
    """Returns {'email': bool, 'sms': bool} for availability check."""
    _load_env()
    email = bool(os.getenv("RESEND_API_KEY")) or all(
        os.getenv(k)
        for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM")
    )
    sms = all(
        os.getenv(k)
        for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER")
    )
    return {"email": email, "sms": sms}


def _format_alert_body(commodities: list[dict], severity_filter: str) -> str:
    """
    Format commodities list into email/SMS body.
    severity_filter="CRITICAL" -> only CRITICAL
    severity_filter="WARNING" -> CRITICAL and WARNING
    """
    include_warning = severity_filter == "WARNING"
    lines = ["Supply Chain Resilience Alert", "=" * 30, ""]
    for c in commodities:
        status = c.get("status", "?")
        if status not in ("CRITICAL", "WARNING"):
            continue
        if status == "WARNING" and not include_warning:
            continue
        name = c.get("name", "?")
        risk = c.get("risk_score")
        mean = c.get("mean_price")
        curr = c.get("currency", "")
        size = c.get("sample_size", 0)
        risk_str = f"{risk:.4f}" if risk is not None else "N/A"
        mean_str = f"{mean} {curr}" if mean is not None else "N/A"
        lines.append(f"- {name}: {status} (risk={risk_str}, avg={mean_str}, n={size})")
    return "\n".join(lines)


def _send_email_resend(recipient: str, subject: str, body: str) -> bool:
    """Send email via Resend API."""
    try:
        import resend

        resend.api_key = os.getenv("RESEND_API_KEY")
        from_addr = os.getenv("SMTP_FROM") or "alerts@resend.dev"
        params = {
            "from": from_addr,
            "to": [recipient],
            "subject": subject,
            "text": body,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        logger.exception("Resend email failed: %s", e)
        return False


def _send_email_smtp(recipient: str, subject: str, body: str) -> bool:
    """Send email via SMTP."""
    try:
        host = os.getenv("SMTP_HOST", "")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        from_addr = os.getenv("SMTP_FROM", user)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = recipient
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(from_addr, [recipient], msg.as_string())
        return True
    except Exception as e:
        logger.exception("SMTP email failed: %s", e)
        return False


def _send_sms_twilio(recipient: str, body: str) -> bool:
    """Send SMS via Twilio."""
    try:
        from twilio.rest import Client

        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        from_num = os.getenv("TWILIO_PHONE_NUMBER")
        if not all((sid, token, from_num)):
            return False
        client = Client(sid, token)
        client.messages.create(body=body[:1600], from_=from_num, to=recipient)
        return True
    except ImportError:
        logger.warning("twilio package not installed")
        return False
    except Exception as e:
        logger.exception("Twilio SMS failed: %s", e)
        return False


def send_report_alert(
    commodities: list[dict],
    recipient_email: str,
    recipient_phone: str | None = None,
    severity_filter: str = "CRITICAL",
) -> dict[str, Any]:
    """
    Format report summary and send via email and/or SMS.
    Only includes commodities matching severity (CRITICAL by default).
    Returns {'email': bool, 'sms': bool, 'error': str|None}. No-op if not configured.
    """
    _load_env()
    result: dict[str, Any] = {"email": False, "sms": False, "error": None}

    if not commodities:
        result["error"] = "No commodities to report"
        return result

    body = _format_alert_body(commodities, severity_filter)
    subject = "Supply Chain Resilience Alert - CRITICAL Risk Detected"

    cfg = is_configured()

    if cfg["email"] and recipient_email:
        if os.getenv("RESEND_API_KEY"):
            result["email"] = _send_email_resend(recipient_email, subject, body)
        else:
            result["email"] = _send_email_smtp(recipient_email, subject, body)

    if cfg["sms"] and recipient_phone:
        result["sms"] = _send_sms_twilio(recipient_phone, body)

    if not cfg["email"] and not cfg["sms"]:
        result["error"] = "Email/SMS not configured. Set RESEND_API_KEY or SMTP_* env vars."

    return result
