"""
Alerts module for Supply Chain Resilience Agent.
Sends email via Resend when supply chain risks are detected.
"""
import logging
import os
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
    email = bool(os.getenv("RESEND_API_KEY"))
    return {"email": email, "sms": False}


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
        # Resend requires a verified 'from' domain for production usage.
        # For quick starts, many accounts can use onboarding@resend.dev.
        from_addr = os.getenv("RESEND_FROM") or "onboarding@resend.dev"
        params = {
            "from": from_addr,
            "to": [recipient],
            "subject": subject,
            "text": body,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        # Avoid noisy stack traces for common configuration issues (invalid key, unverified from, etc.).
        logger.error("Resend email failed: %s", e)
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
        result["email"] = _send_email_resend(recipient_email, subject, body)

    # SMS is intentionally disabled in this build.
    result["sms"] = False

    if not cfg["email"]:
        result["error"] = "Email not configured. Set RESEND_API_KEY (and optionally RESEND_FROM)."

    return result
