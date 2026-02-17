# Setup Guide – Next Steps

Follow these steps to finish configuring the Supply Chain Resilience Agent.

---

## 1. MCP in Cursor

Your `.cursor/mcp.json` is already configured. To activate the Supply Chain server:

1. **Restart Cursor** (or reload the window: `Ctrl+Shift+P` → "Developer: Reload Window")
2. Open **Settings → MCP** and confirm `supply-chain-resilience` is listed
3. Try a prompt: "What's the rice supply chain risk?" – the LLM will use the MCP tools

If the server fails to start, ensure you're in the project root and run:
```bash
python src/server.py
```
Any import or path errors will appear in the terminal.

---

## 2. Alerts (Configured)

Your `.env` is set with:
- **Resend API** for email
- **ALERT_EMAIL** for batch alerts

To test alerts locally:
```bash
python src/agent.py
```
If any commodity is CRITICAL, an email is sent to `ALERT_EMAIL`.

---

## 3. Push to GitHub

Create a new repository on GitHub, then:

```bash
cd "d:\Projects\open_food_MCP project"
git add .
git commit -m "Initial commit: Supply Chain Resilience Agent"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

Replace `YOUR_USERNAME` and `YOUR_REPO_NAME` with your GitHub details.

---

## 4. Enable GitHub Pages

1. Open the repo on GitHub → **Settings** → **Pages**
2. Under **Build and deployment**:
   - **Source:** Deploy from a branch
   - **Branch:** `main` → `/ (root)` → Save
3. Wait 1–2 minutes for deployment
4. Open: `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/frontend/`

---

## 5. Add GitHub Secrets (Optional – for automated alerts)

To receive email alerts when the daily scan finds CRITICAL commodities:

1. Open the repo on GitHub → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** for each:

| Secret Name | Description |
|-------------|-------------|
| `ALERT_EMAIL` | Recipient address (e.g. ops@company.com) |
| `RESEND_API_KEY` | Your Resend API key |

If you use SMTP instead of Resend, add:
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`

For SMS (Twilio):
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`

---

## 6. Trigger the Daily Scan Manually

The workflow runs at 08:00 UTC. To run it now:

1. Go to **Actions** → **Daily Supply Chain Scan**
2. Click **Run workflow** → **Run workflow**

After it finishes, the dashboard will show the new report.
