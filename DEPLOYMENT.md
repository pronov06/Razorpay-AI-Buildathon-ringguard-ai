# 🚀 Streamlit Community Cloud — Deployment Guide

This guide walks you through deploying RingGuard AI from your GitHub repository to [Streamlit Community Cloud](https://streamlit.io/cloud) in under 10 minutes.

---

## Prerequisites

- A [GitHub](https://github.com) account
- A [Streamlit Community Cloud](https://share.streamlit.io) account (free)
- Your Gemini API key from [Google AI Studio](https://aistudio.google.com) *(optional)*

---

## Step 1 — Prepare Your Repository

### 1a. Create the repository on GitHub

Go to [github.com/new](https://github.com/new):

- Repository name: `ringguard-ai`
- Visibility: **Public** *(required for free Streamlit deployment)*
- Do NOT initialise with README (you already have one)

### 1b. Push your local project

```bash
cd ringguard-ai

git init
git add .
git commit -m "feat: initial RingGuard AI submission"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ringguard-ai.git
git push -u origin main
```

### 1c. Verify `.gitignore` excludes secrets

Create `.gitignore` if it doesn't exist:

```gitignore
# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Streamlit secrets — NEVER commit your API key
.streamlit/secrets.toml

# Editor
.vscode/
.idea/
```

Commit it:
```bash
git add .gitignore
git commit -m "chore: add gitignore"
git push
```

---

## Step 2 — Connect to Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click **"Sign in with GitHub"** and authorise
3. Click **"New app"**

Fill in the form:

| Field | Value |
|---|---|
| Repository | `YOUR_USERNAME/ringguard-ai` |
| Branch | `main` |
| Main file path | `app.py` |
| App URL (optional) | `ringguard-ai` |

---

## Step 3 — Add Your Gemini API Key as a Secret

**Do this BEFORE clicking Deploy:**

1. Click **"Advanced settings"** on the deploy form
2. Click **"Secrets"**
3. Paste the following (replace with your real key):

```toml
GEMINI_API_KEY = "AIzaSy_YOUR_ACTUAL_KEY_HERE"
```

4. Click **"Save"**

> **Why this works:** Streamlit reads `st.secrets` which maps to the secrets you set here. The app reads `os.environ.get("GEMINI_API_KEY")` — Streamlit automatically injects secrets as environment variables.

---

## Step 4 — Deploy

Click **"Deploy!"**

Streamlit will:
1. Clone your repo
2. Install `requirements.txt` automatically
3. Run `streamlit run app.py`
4. Give you a public URL like `https://ringguard-ai.streamlit.app`

First deploy takes ~2–3 minutes.

---

## Step 5 — Verify the Deployment

Once live, check:

- [ ] Hero banner loads with live badge
- [ ] Overview tab shows 3 rings detected
- [ ] Ring Network Graph tab renders the interactive graph
- [ ] Merchant Explorer — pick any merchant from the sidebar
- [ ] Audit Ledger — click "Run Audit Sync" and verify a new entry appears
- [ ] Console (Streamlit Cloud logs) shows no errors

---

## Handling the Data Files

The `data/` folder (pre-generated JSON files) **should be committed to GitHub** so the deployed app has data on first load without needing to run `synthetic_data.py`.

Verify they're in your repo:
```bash
git status data/
# Should show: data/merchants.json, data/transactions.json, data/returns.json
```

If they're missing:
```bash
python synthetic_data.py
git add data/
git commit -m "chore: add synthetic data files"
git push
```

---

## Updating the App

Any push to `main` triggers an automatic redeploy:

```bash
# Make your changes, then:
git add .
git commit -m "fix: updated detection threshold"
git push
# Streamlit Cloud auto-redeploys in ~60 seconds
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError` | Ensure all packages are in `requirements.txt` |
| `FileNotFoundError: data/merchants.json` | Commit the `data/` folder to GitHub |
| `GEMINI_API_KEY not set` warning | Add key in Streamlit Cloud → App Settings → Secrets |
| App crashes on startup | Check Streamlit Cloud logs (Manage app → Logs) |
| Audit log not persisting | Expected — Streamlit Cloud has ephemeral filesystem; logs reset on restart. Use a database for production. |

---

## Production Considerations

For a production deployment beyond a hackathon demo:

| Concern | Recommendation |
|---|---|
| **Audit log persistence** | Replace `audit_log.json` with PostgreSQL or Firestore |
| **Real transaction data** | Connect to Razorpay API webhooks instead of synthetic JSON |
| **Auth** | Add `streamlit-authenticator` or Streamlit's built-in auth |
| **Scale** | Move detection to a background worker (Celery / Cloud Run) |
| **Monitoring** | Add Sentry for error tracking |

