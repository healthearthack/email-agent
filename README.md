# email-agent

Andy's Gmail email agent with Gemini-generated responses, Gmail Drafts human review, and optional HubSpot and Salesforce synchronization.

## Requirements

- Python 3.13
- Gmail account with an app password
- Gemini API key
- Optional HubSpot and Salesforce credentials

## Install

```bash
python -m venv .venv
```

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

The Python program reads configuration from environment variables. A `.env` file is provided only as a template convention; the application does not automatically load `.env`. In GitHub Actions, configure the values as repository secrets.

## Required GitHub Actions secrets

- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`
- `GEMINI_API_KEY`

## Optional HubSpot secrets

- `HUBSPOT_ACCESS_TOKEN`
- `HUBSPOT_PORTAL_ID`

## Optional Salesforce secrets

- `SF_DOMAIN`
- `SF_CLIENT_ID`
- `SF_CLIENT_SECRET`
- `SF_USERNAME`
- `SF_PASSWORD`
- `SF_SECURITY_TOKEN`

## Validate locally

```powershell
python -m py_compile .\email-agent.py
python -m py_compile '.\metaknews@gmail.com.py'
python -m pip check
```

## Run once locally in PowerShell

```powershell
$env:GMAIL_USER='your-account@gmail.com'
$env:GMAIL_APP_PASSWORD='your-app-password'
$env:GEMINI_API_KEY='your-gemini-api-key'
$env:GEMINI_MODEL='gemini-3.6-flash'
$env:DRAFT_ONLY_MODE='True'
$env:RUN_ONCE='True'
python '.\metaknews@gmail.com.py'
```

The scheduled GitHub Actions workflow runs the same entry point every 15 minutes and creates Gmail drafts for human review.

## Runtime behavior

The scheduled run uses Gmail Drafts only. Messages are inspected without marking them read; a message is marked read only after its draft is created successfully. Automated notifications and mailing-list messages are skipped before Gemini is called. If the Gemini quota is exhausted, the run ends cleanly and leaves the current message unread so a later run can retry it.
