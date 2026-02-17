"""
MCP Server for Supply Chain Resilience Agent.
Exposes tools for LLM-driven investigation and on-demand alerts.
"""
import json
from pathlib import Path

from fastmcp import FastMCP

from analyzer import DEFAULT_COMMODITIES, analyze_all, analyze_commodity
from alerts import is_configured, send_report_alert

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = PROJECT_ROOT / "data" / "latest_report.json"

mcp = FastMCP("Supply Chain Resilience Agent")


@mcp.tool
def investigate_commodity(commodity: str) -> dict:
    """
    Fetch live price data from Open Prices API for a commodity and compute risk.
    Use for real-time supply chain investigation.
    """
    return analyze_commodity(commodity)


@mcp.tool
def get_supply_chain_report() -> dict:
    """Return the latest cached report from data/latest_report.json."""
    if not REPORT_PATH.exists():
        return {
            "error": "Report not yet generated. Run the daily scan or investigate_commodity."
        }
    with open(REPORT_PATH) as f:
        return json.load(f)


@mcp.tool
def list_commodities() -> list[str]:
    """Return the standard commodity list tracked by the agent (rice, milk, eggs, oil, wheat)."""
    return list(DEFAULT_COMMODITIES)


@mcp.tool
def compare_commodities(commodities: list[str]) -> dict:
    """
    Fetch and analyze each commodity, return a comparative risk summary.
    Use when comparing supply chain risk across multiple commodities.
    """
    results = [analyze_commodity(c) for c in commodities]
    critical = [r for r in results if r.get("status") == "CRITICAL"]
    warning = [r for r in results if r.get("status") == "WARNING"]
    stable = [r for r in results if r.get("status") == "STABLE"]
    return {
        "commodities": results,
        "summary": {
            "critical_count": len(critical),
            "warning_count": len(warning),
            "stable_count": len(stable),
            "highest_risk": (
                max(results, key=lambda r: r.get("risk_score") or 0)
                if results
                else None
            ),
        },
    }


@mcp.tool
def send_supply_chain_alert(
    recipient_email: str,
    recipient_phone: str | None = None,
    commodity: str | None = None,
    include_warnings: bool = False,
) -> dict:
    """
    Send email and/or SMS alert with supply chain risk summary.
    If commodity is set, analyze only that commodity. Otherwise analyze all tracked commodities.
    Only sends CRITICAL by default; set include_warnings=True to include WARNING items.
    """
    cfg = is_configured()
    if not cfg["email"] and not cfg["sms"]:
        return {
            "error": "Email not configured. Set RESEND_API_KEY (and optionally RESEND_FROM)."
        }

    if commodity:
        commodities = [analyze_commodity(commodity)]
    else:
        commodities = analyze_all()

    severity_filter = "WARNING" if include_warnings else "CRITICAL"
    filtered = (
        [c for c in commodities if c.get("status") in ("CRITICAL", "WARNING")]
        if include_warnings
        else [c for c in commodities if c.get("status") == "CRITICAL"]
    )

    if not filtered:
        return {
            "sent": False,
            "message": "No CRITICAL or WARNING commodities to alert on.",
        }

    result = send_report_alert(
        commodities=filtered,
        recipient_email=recipient_email,
        recipient_phone=recipient_phone,
        severity_filter=severity_filter,
    )
    return {
        "sent": result.get("email") or result.get("sms"),
        "email": result.get("email", False),
        "sms": result.get("sms", False),
        "error": result.get("error"),
    }


if __name__ == "__main__":
    mcp.run()
