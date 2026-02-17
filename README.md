# Supply Chain Resilience Agent

Monitor food price volatility to detect supply chain risks. In supply chain theory, when a logistics network is working well, prices for a standardized commodity (e.g., 1kg rice) should be similar across a region. **Low variance = stable supply chain. High variance = possible hoarding, delivery failure, or local shortages.**

This project combines:

- **MCP server** – LLM-driven investigation and on-demand alerts via Cursor
- **Daily batch scan** – Automated analysis and report generation via GitHub Actions
- **Static dashboard** – Dark-mode UI on GitHub Pages
- **Alerts** – Email (Resend/SMTP) and optional SMS (Twilio) when commodities hit CRITICAL status

---

## Project Overview

| Component | Description |
|-----------|-------------|
| **Price dispersion = risk** | Coefficient of Variation (CV = std/mean) maps to CRITICAL (>0.5), WARNING (>0.3), or STABLE (≤0.3) |
| **Open Prices API** | Data source: `https://prices.openfoodfacts.org/api/v1/prices` |
| **Commodities** | rice, milk, eggs, oil, wheat |

---

## MCP Setup

Use the Supply Chain Resilience tools from Cursor or another MCP client.

1. **Install dependencies:**
   ```bash
   pip install -r src/requirements.txt
   ```

2. **Project config:** `.cursor/mcp.json` is already configured. Ensure `cwd` points to the project root.

3. **Restart Cursor** so it picks up the MCP server. The tools will appear in the MCP panel:
   - `investigate_commodity` – Live risk analysis for a commodity
   - `get_supply_chain_report` – Latest cached report
   - `list_commodities` – Tracked commodity list
   - `compare_commodities` – Comparative risk across commodities
   - `send_supply_chain_alert` – Send email/SMS alert

4. **Run manually (optional):**
   ```bash
   python src/server.py
   ```

---

## Alerts Setup

Configure email and optional SMS for automated (batch) and on-demand (MCP) alerts.

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Email – choose one:**
   - **Resend:** Set `RESEND_API_KEY` (free tier: 100 emails/day)
   - **SMTP:** Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` (works with Gmail, Outlook, etc.)

3. **SMS (optional):** Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`

4. **Batch alerts:** Set `ALERT_EMAIL` to receive automated emails when any commodity is CRITICAL.

**GitHub Actions:** Add these as repository secrets (Settings → Secrets and variables → Actions). The daily workflow will use them when sending alerts.

---

## Enable GitHub Pages

1. Go to **Repository Settings → Pages**
2. Under **Build and deployment**, choose **Deploy from a branch**
3. **Branch:** `main` (or your default branch)
4. **Folder:** `/ (root)`
5. Save

Your dashboard will be at: `https://<username>.github.io/<repo>/frontend/`

---

## How the Daily Scan Works

1. **Schedule:** GitHub Actions runs daily at 08:00 UTC (`cron: '0 8 * * *'`)
2. **Steps:** Checkout → Setup Python → Install deps → Run `python src/agent.py`
3. **Agent:** Fetches price data for rice, milk, eggs, oil, wheat; computes CV and status; writes `data/latest_report.json`
4. **Alerts:** If any commodity is CRITICAL and `ALERT_EMAIL` is set, sends an email
5. **Commit:** Pushes `data/latest_report.json` back to the repo so GitHub Pages and the dashboard can read it

---

## Local Development

```bash
# Run the batch agent (generates data/latest_report.json)
python src/agent.py

# Run the MCP server (for Cursor integration)
python src/server.py
```

Use `.env` (copy from `.env.example`) to test alerts locally.

---

## Project Structure

```
.github/workflows/daily_scan.yml   # Daily cron workflow
.cursor/mcp.json                  # Cursor MCP config
src/
  analyzer.py                     # Price fetch, CV, risk analysis
  agent.py                        # Batch script, writes report
  alerts.py                       # Email/SMS delivery
  server.py                       # FastMCP server with tools
  requirements.txt
.env.example                      # Env var template
frontend/
  index.html
  style.css
  app.js
data/
  latest_report.json              # Generated report
.gitignore
README.md
```
