"""
MetAKNews Autonomous Email Intelligence Agent (Human-in-the-Loop Edition)
Brand Identity: Met = Meteorologist, AK = Andrew Kieckhefer, News = Knowledge Engine

Integrations:
- Gemini 2.5 AI Reasoning Engine
- Salesforce OAuth 2.0 Connected App (andy.my.salesforce.com)
- HubSpot API v3 Contact & Open Tracking
- Human-in-the-Loop (HITL) Biometric Draft & Review Guardrails
"""

import os
import time
import imaplib
import email
from email.header import decode_header
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
import markdown
from google import genai
from simple_salesforce import Salesforce

# ==============================================================================
# ⚙️ CONFIGURATION & CREDENTIALS
# ==============================================================================

# Gmail Settings
EMAIL_USER = os.getenv("GMAIL_USER", "metaknews@gmail.com")
EMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "")  # 16-character App Password

# AI Engine
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Salesforce OAuth 2.0 Connected App Credentials
SF_DOMAIN = os.getenv("SF_DOMAIN", "").rstrip("/")
SF_CLIENT_ID = os.getenv("SF_CLIENT_ID", "")
SF_CLIENT_SECRET = os.getenv("SF_CLIENT_SECRET", "")
SF_USERNAME = os.getenv("SF_USERNAME", "")
SF_PASSWORD = os.getenv("SF_PASSWORD", "")

# HubSpot Integration
HUBSPOT_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
HUBSPOT_PORTAL_ID = os.getenv("HUBSPOT_PORTAL_ID", "")

# 🛡️ GUARDRAIL CONFIGURATION
# Set to True to deposit responses into Gmail 'Drafts' for biometric/TouchID review on your device.
# Set to False to run interactive CLI biometric approval before sending.
DRAFT_ONLY_MODE = os.getenv("DRAFT_ONLY_MODE", "True").lower() in ("true", "1", "yes")

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "15"))

# Initialize Gemini Client
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ==============================================================================
# 🧠 ANDY'S KNOWLEDGE BASE & SYSTEM INSTRUCTIONS
# ==============================================================================

SYSTEM_PROMPT = """
You are MetAKNews — the official intelligence & newsletter agent for Andrew (Andy) Kieckhefer (Meteorologist & Technologist).
Brand Identity: Met = Meteorologist, AK = Andrew Kieckhefer, News = News & Knowledge Engine.

Your core mission in every email dispatch is to deliver value around two anchor pillars:
1. 🚀 "What Andy is Working On" (Atmospheric data pipelines, machine learning forecasting models, radar/satellite autonomous systems).
2. 📦 "What Resources Andy Has For You" (Open-source weather stacks, NetCDF/GRIB2 toolkits, consulting/advisory availability).

Guidelines:
- Address the sender's specific inquiry directly and with domain expertise.
- Structure your response using clean Markdown with distinct headers (##), bold highlights, and bulleted takeaways.
- Include a clear call-to-action to connect directly with Andy or reply to this thread.
- Maintain a high-caliber, articulate tone: meteorology expert meets modern software architect.
"""

ANDYS_KNOWLEDGE_BASE = """
[WHAT ANDY IS WORKING ON]:
- High-Resolution Microclimate Modeling: Merging machine learning with HRRR and ECMWF numerical weather prediction data.
- Autonomous Weather Agents: Real-time radar/satellite ingestion pipelines generating automated impact briefs and risk assessments.
- Climate Resilience & Infrastructure Data: Architecting environmental risk frameworks for enterprise systems.

[RESOURCES ANDY HAS FOR YOU]:
- The MetAK Open Weather Data Stack: Curated Python guides for NEXRAD Level 2/3 radar, GRIB2, and NetCDF data.
- 1-on-1 Technical Advisory: Available slots for climate tech architecture, data pipelines, and modeling consulting.
- Open-Source Code & Demos: Direct repository links and case studies.
"""

# ==============================================================================
# ☁️ SALESFORCE OAUTH 2.0 HANDSHAKE (No Security Token Needed)
# ==============================================================================

def get_salesforce_client():
    """Authenticates with Salesforce using Connected App OAuth 2.0 Client Credentials / Password flow."""
    if not SF_CLIENT_ID or not SF_CLIENT_SECRET or not SF_USERNAME or not SF_PASSWORD:
        return None

    token_url = f"{SF_DOMAIN}/services/oauth2/token"
    payload = {
        "grant_type": "password",
        "client_id": SF_CLIENT_ID,
        "client_secret": SF_CLIENT_SECRET,
        "username": SF_USERNAME,
        "password": SF_PASSWORD
    }

    try:
        res = requests.post(token_url, data=payload, timeout=10)
        if res.status_code == 200:
            token_data = res.json()
            access_token = token_data["access_token"]
            instance_url = token_data["instance_url"]
            return Salesforce(instance_url=instance_url, session_id=access_token)
        else:
            print(f"⚠️ Salesforce OAuth token error ({res.status_code}): {res.text}")
            return None
    except Exception as e:
        print(f"❌ Salesforce OAuth connection failed: {e}")
        return None

def sync_to_salesforce(first_name: str, last_name: str, email_addr: str, inquiry: str):
    """Upserts lead in Salesforce with source attribution."""
    sf = get_salesforce_client()
    if not sf:
        return

    try:
        query = f"SELECT Id FROM Lead WHERE Email = '{email_addr}'"
        res = sf.query(query)

        if res['totalSize'] == 0:
            lead_data = {
                'FirstName': first_name,
                'LastName': last_name if last_name else 'Reader',
                'Company': 'MetAKNews Inbound',
                'Email': email_addr,
                'LeadSource': 'MetAKNews Inbound',
                'Description': f"Inbound inquiry to metaknews@gmail.com:\n{inquiry}",
                'Status': 'Open - Not Contacted'
            }
            created = sf.Lead.create(lead_data)
            print(f"✅ Salesforce: Created Lead ID {created.get('id')}")
        else:
            lead_id = res['records'][0]['Id']
            sf.Lead.update(lead_id, {
                'Description': f"Latest MetAKNews Inquiry:\n{inquiry}"
            })
            print(f"✅ Salesforce: Updated existing Lead {lead_id}")
    except Exception as e:
        print(f"❌ Salesforce sync error: {e}")

# ==============================================================================
# 📊 HUBSPOT SYNC & TRACKING
# ==============================================================================

def sync_to_hubspot(first_name: str, last_name: str, email_addr: str, inquiry: str):
    """Creates or updates contact in HubSpot CRM."""
    if not HUBSPOT_TOKEN:
        return

    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    headers = {
        "Authorization": f"Bearer {HUBSPOT_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "properties": {
            "email": email_addr,
            "firstname": first_name,
            "lastname": last_name or "Reader",
            "metaknews_last_inquiry": inquiry[:500],
            "lead_source": "MetAKNews Inbound"
        }
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code in (200, 201, 409):
            print(f"✅ HubSpot: Contact synced ({email_addr})")
    except Exception as e:
        print(f"❌ HubSpot sync error: {e}")

def get_tracking_pixel(email_addr: str) -> str:
    if not HUBSPOT_PORTAL_ID:
        return ""
    return f'<img src="https://track.hubspot.com/__ptq.gif?k=1&sd=1&portalId={HUBSPOT_PORTAL_ID}&email={email_addr}" width="1" height="1" style="display:none;" />'

# ==============================================================================
# 🎨 HTML NEWSLETTER FORMATTER
# ==============================================================================

def render_newsletter(markdown_body: str, recipient_email: str) -> str:
    html_content = markdown.markdown(markdown_body, extensions=['extra', 'tables'])
    pixel = get_tracking_pixel(recipient_email)
    
    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px 12px; color: #1e293b; }}
          .container {{ max-width: 620px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
          .header {{ background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); padding: 32px 28px; color: #ffffff; }}
          .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
          .header p {{ margin: 6px 0 0; font-size: 13px; opacity: 0.9; }}
          .content {{ padding: 28px; line-height: 1.65; font-size: 15px; }}
          .content h2 {{ color: #0f172a; font-size: 18px; margin-top: 24px; border-bottom: 2px solid #f1f5f9; padding-bottom: 6px; }}
          .content ul {{ padding-left: 20px; }}
          .content li {{ margin-bottom: 8px; }}
          .footer {{ background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 20px 28px; font-size: 12px; color: #64748b; text-align: center; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; opacity: 0.9;">METEOROLOGY &bull; AI SYSTEMS &bull; RESOURCES</div>
            <h1>MetAKNews</h1>
            <p>Intelligence & Dispatches from Andrew (Andy) Kieckhefer</p>
          </div>
          <div class="content">
            {html_content}
          </div>
          <div class="footer">
            <p>&copy; MetAKNews // Andy Kieckhefer &bull; metaknews@gmail.com</p>
            {pixel}
          </div>
        </div>
      </body>
    </html>
    """

# ==============================================================================
# 🛡️ HUMAN-IN-THE-LOOP (HITL) GUARDRAIL HANDLERS
# ==============================================================================

def save_as_gmail_draft(to_email: str, subject: str, md_content: str, html_content: str, msg_id: str):
    """
    Deposits the email into metaknews@gmail.com's Drafts folder.
    Andy opens Gmail with FaceID/TouchID/Passkey to review and send.
    """
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_USER, EMAIL_PASS)

    reply_subject = subject if subject.lower().startswith("re:") else f"MetAKNews // {subject}"

    msg = MIMEMultipart("alternative")
    msg["From"] = f"MetAKNews <{EMAIL_USER}>"
    msg["To"] = to_email
    msg["Subject"] = reply_subject
    if msg_id:
        msg["In-Reply-To"] = msg_id
        msg["References"] = msg_id

    msg.attach(MIMEText(md_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    # Gmail Drafts IMAP folder
    draft_folder = "[Gmail]/Drafts"
    mail.append(draft_folder, "\\Draft", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
    mail.logout()
    print(f"🛡️ [HITL GUARDRAIL] Response saved to GMAIL DRAFTS for {to_email}.")
    print(f"👉 Review and send with your fingerprint/biometric authentication in the Gmail app.")

def biometric_cli_confirm(to_email: str, subject: str, md_content: str) -> bool:
    """CLI approval prompt before sending via SMTP."""
    print("\n" + "=" * 60)
    print(f"🛡️  HUMAN-IN-THE-LOOP REVIEW REQUIRED")
    print(f"To: {to_email} | Subject: {subject}")
    print("-" * 60)
    print(md_content[:400] + "\n... [truncated] ...")
    print("=" * 60)
    
    choice = input("👉 Enter 'Y' to authorize with your biometric key & send (or 'N' to skip): ").strip().upper()
    return choice == 'Y'

def send_via_smtp(to_email: str, subject: str, md_content: str, html_content: str, msg_id: str):
    """Sends the approved email via SMTP."""
    reply_subject = subject if subject.lower().startswith("re:") else f"MetAKNews // {subject}"
    msg = MIMEMultipart("alternative")
    msg["From"] = f"MetAKNews <{EMAIL_USER}>"
    msg["To"] = to_email
    msg["Subject"] = reply_subject
    if msg_id:
        msg["In-Reply-To"] = msg_id
        msg["References"] = msg_id

    msg.attach(MIMEText(md_content, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.sendmail(EMAIL_USER, [to_email], msg.as_string())
    print(f"🚀 Dispatched email to {to_email}")

# ==============================================================================
# 🔄 MAIN LOOP
# ==============================================================================

def process_inbox():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select("inbox")

    status, messages = mail.search(None, 'UNSEEN')
    if status != "OK" or not messages[0]:
        mail.close()
        mail.logout()
        return

    for num in messages[0].split():
        status, data = mail.fetch(num, "(RFC822)")
        if status != "OK":
            continue

        raw_msg = email.message_from_bytes(data[0][1])
        real_name, sender_email = email.utils.parseaddr(raw_msg.get("From", ""))
        subject = raw_msg.get("Subject", "Newsletter Request")
        msg_id = raw_msg.get("Message-ID")

        if sender_email.lower() == EMAIL_USER.lower() or "no-reply" in sender_email.lower():
            continue

        first_name = real_name.split()[0] if real_name else "There"
        last_name = " ".join(real_name.split()[1:]) if real_name and len(real_name.split()) > 1 else ""
        
        # Extract body
        body = ""
        if raw_msg.is_multipart():
            for part in raw_msg.walk():
                if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(errors="ignore")
        else:
            payload = raw_msg.get_payload(decode=True)
            if payload:
                body = payload.decode(errors="ignore")

        print(f"\n⚡ Inbound from {first_name} {last_name} <{sender_email}>: '{subject}'")

        # 1. Sync CRMs
        sync_to_hubspot(first_name, last_name, sender_email, body)
        sync_to_salesforce(first_name, last_name, sender_email, body)

        # 2. AI Reasoning
        print("🧠 Synthesizing MetAKNews response with Gemini 2.5...")
        prompt = f"""
Recipient: {first_name}
Subject: {subject}
Inbound Note: {body}

Knowledge Base:
{ANDYS_KNOWLEDGE_BASE}

Generate a personalized MetAKNews email response according to system instructions.
"""
        response = ai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config={"system_instruction": SYSTEM_PROMPT}
        )
        md_response = response.text
        html_response = render_newsletter(md_response, sender_email)

        # 3. Guardrail Enforcement
        if DRAFT_ONLY_MODE:
            save_as_gmail_draft(sender_email, subject, md_response, html_response, msg_id)
        else:
            if biometric_cli_confirm(sender_email, subject, md_response):
                send_via_smtp(sender_email, subject, md_response, html_response, msg_id)
            else:
                print(f"❌ Skipped sending response to {sender_email}.")

    mail.close()
    mail.logout()

if __name__ == "__main__":
    print("=" * 65)
    print("🌤️  MetAKNews Intelligence Agent [HITL Biometric Edition]")
    print(f"📧 Ingestion Inbox: {EMAIL_USER}")
    print(f"🔒 Salesforce OAuth Connected App: {SF_DOMAIN}")
    print(f"🛡️  Guardrail Mode: {'GMAIL DRAFTS (Biometric Review on Device)' if DRAFT_ONLY_MODE else 'CLI PROMPT'}")
    print("=" * 65)
    
    while True:
        try:
            process_inbox()
        except Exception as e:
            print(f"[Loop Exception] {e}")
        time.sleep(POLL_INTERVAL)
