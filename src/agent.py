"""
Batch agent for Supply Chain Resilience.
Runs analysis, writes report to data/latest_report.json, and sends alerts on CRITICAL.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from analyzer import analyze_all
from alerts import send_report_alert

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

REPORT_PATH = PROJECT_ROOT / "data" / "latest_report.json"


def main() -> None:
    commodities = analyze_all()
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "commodities": commodities,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    alert_email = os.getenv("ALERT_EMAIL")
    if alert_email:
        critical = [c for c in commodities if c.get("status") == "CRITICAL"]
        if critical:
            send_report_alert(
                commodities=critical,
                recipient_email=alert_email,
                severity_filter="CRITICAL",
            )


if __name__ == "__main__":
    main()
