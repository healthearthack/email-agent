import imaplib
import email
from email.header import decode_header
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import os
import requests
import markdown
from google import genai
from simple_salesforce import Salesforce

# ==========================================
# ⚙️ CONFIGURATION & CREDENTIALS
# ==========================================
EMAIL_USER = os.getenv("GMAIL_USER", "metaknews@gmail.com")
EMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD", "your-16-char-app-password")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-gemini-api-key")

# HubSpot Config
HUBSPOT_TOKEN = os.getenv("HUBSPOT_ACCESS_TOKEN", "your-hubspot-token")
HUBSPOT_PORTAL_ID = os.getenv("HUBSPOT_PORTAL_ID", "your-hubspot-portal-id")

# Salesforce Config
SF_USERNAME = os.getenv("SF_USERNAME", "your-sf-username")
SF_PASSWORD = os.getenv("SF_PASSWORD", "your-sf-password")
SF_TOKEN = os.getenv("SF_SECURITY_TOKEN", "your-sf-token")
SF_DOMAIN = os.getenv("SF_DOMAIN", "login")  # 'login' or 'test' for sandbox

IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"

# Initialize Gemini Client
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 🧠 ANDY'S KNOWLEDGE BASE & SYSTEM PROMPT
# ==========================================
SYSTEM_PROMPT = """
You are MetAKNews — the official intelligence & newsletter agent for Andrew (Andy) Kieckhefer (Meteorologist & Technologist).
Brand Identity: Met = Meteorologist, AK = Andrew Kieckhefer, News = News & Resources.

Your core mission in every email is to deliver value around two anchor pillars:
1. 🚀 "What Andy is Working On" (Current projects, meteorology tech, AI pipelines, atmospheric data analysis, active builds).
2. 📦 "What Resources Andy Has For You" (Curated toolkits, weather data frameworks, advisory availability, code libraries).

Instructions:
- If the sender asked a specific question or topic, address it thoughtfully in the opening section.
- Naturally transition into Andy's current radar/projects and relevant resources.
- Write with an articulate, engaging, and professional tone (expert meteorologist meets modern technologist).
- Format your response using clean Markdown with distinct headers (##), bold highlights, and bullet points.
- Include a clear call-to-action (CTA) to connect with Andy or reply directly.
"""

ANDYS_CURRENT_CONTEXT = """
[CURRENT PROJECTS - WHAT ANDY IS WORKING ON]:
- High-Resolution Atmospheric Modeling: Integrating machine learning with NWP (Numerical Weather Prediction) data for hyper-local microclimate forecasting.
- Autonomous Weather Agents: Building agentic workflows that ingest live radar, satellite, and meteorological feeds to generate automated impact memos.
- Climate Resilience & Data Architecture: Consulting with infrastructure teams on environmental risk modeling and extreme weather mitigation.

[FEATURED RESOURCES FOR YOU]:
- The MetAK Open Weather Data Stack: A curated guide to high-performance Python libraries for GRIB2, NetCDF, and radar visualizer workflows.
- 1-on-1 Strategy & Advisory: Andy is opening 2 slots this month for climate tech consulting and custom data pipeline design.
- Direct Contact: Reply directly to this thread or book time directly on Andy's calendar.
"""

# ==========================================
# 🔗 CRM INTEGRATIONS (HubSpot & Salesforce)
# ==========================================
def sync_to_hubspot(first_name, last_name, email_addr, inquiry_summary):
    """Creates or updates contact in HubSpot and logs inquiry."""
    if not HUBSPOT_TOKEN or HUBSPOT_TOKEN.startswith("your-"):
        print("ℹ️ HubSpot token not configured, skipping sync.")
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
            "lastname": last_name,
            "metaknews_last_inquiry": inquiry_summary,
            "lead_source": "MetAKNews Inbound"
        }
    }
    try:
        res = requests.post(url, json=payload, headers=headers)
        if res.status_code in [200, 201]:
            print(f"✅ HubSpot: Contact synced ({email_addr})")
        elif res.status_code == 409:
            # Contact exists, update instead
            print(f"ℹ️ HubSpot: Contact exists, updating record...")
        else:
            print(f"⚠️ HubSpot sync response: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ HubSpot sync error: {e}")

def sync_to_salesforce(first_name, last_name, email_addr, inquiry_summary):
    """Pushes lead to Salesforce."""
    if not SF_USERNAME or SF_USERNAME.startswith("your-"):
        print("ℹ️ Salesforce credentials not configured, skipping sync.")
        return

    try:
        sf = Salesforce(username=SF_USERNAME, password=SF_PASSWORD, security_token=SF_TOKEN, domain=SF_DOMAIN)
        
        # Check if lead already exists
        query = f"SELECT Id FROM Lead WHERE Email = '{email_addr}'"
        existing = sf.query(query)

        if existing['totalSize'] == 0:
            lead_data = {
                'FirstName': first_name,
                'LastName': last_name if last_name else "Inquirer",
                'Company': 'MetAKNews Reader / Individual',
                'Email': email_addr,
                'LeadSource': 'MetAKNews Inbound',
                'Description': f"Inbound via metaknews@gmail.com:\n{inquiry_summary}",
                'Status': 'Open - Not Contacted'
            }
            res = sf.Lead.create(lead_data)
            print(f"✅ Salesforce: New Lead created with ID {res.get('id')}")
        else:
            lead_id = existing['records'][0]['Id']
            sf.Lead.update(lead_id, {
                'Description': f"Updated MetAKNews Inquiry:\n{inquiry_summary}"
            })
            print(f"✅ Salesforce: Existing Lead {lead_id} updated.")
    except Exception as e:
        print(f"❌ Salesforce sync error: {e}")

# ==========================================
# 📧 EMAIL PARSER & SENDER
# ==========================================
def clean_subject(header_val):
    if not header_val:
        return "Newsletter & Resource Dispatch"
    decoded, encoding = decode_header(header_val)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(encoding or "utf-8", errors="ignore")
    return str(decoded)

def get_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get("Content-Disposition"))
            if ctype == "text/plain" and "attachment" not in cdispo:
                payload = part.get_payload(decode=True)
                if payload:
                    body += payload.decode(errors="ignore")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode(errors="ignore")
    return body.strip()

def parse_sender_name(from_header):
    real_name, email_addr = email.utils.parseaddr(from_header)
    first_name = "There"
    last_name = ""
    if real_name:
        parts = real_name.split()
        first_name = parts[0]
        if len(parts) > 1:
            last_name = " ".join(parts[1:])
    return first_name, last_name, email_addr

def generate_newsletter_content(first_name, subject, user_inquiry):
    user_prompt = f"""
Recipient First Name: {first_name}
Subject: {subject}
Sender's Message / Request:
{user_inquiry}

Andy's Current Knowledge Base:
{ANDYS_CURRENT_CONTEXT}

Generate the personalized MetAKNews email response according to your system instructions.
"""
    response = ai_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[user_prompt],
        config={"system_instruction": SYSTEM_PROMPT}
    )
    return response.text

def send_metak_email(to_email, original_subject, body_markdown, original_msg_id):
    reply_subject = original_subject if original_subject.lower().startswith("re:") else f"MetAKNews // {original_subject}"

    # Render Markdown to HTML
    html_body = markdown.markdown(body_markdown, extensions=['extra', 'tables'])

    # Optional HubSpot tracking pixel injection
    tracking_pixel = ""
    if HUBSPOT_PORTAL_ID and not HUBSPOT_PORTAL_ID.startswith("your-"):
        tracking_pixel = f'<img src="https://track.hubspot.com/__ptq.gif?k=1&sd=1&portalId={HUBSPOT_PORTAL_ID}&email={to_email}" width="1" height="1" style="display:none;" />'

    # Polished MetAKNews Newsletter Template
    styled_html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8fafc;
            margin: 0;
            padding: 24px 12px;
            color: #1e293b;
          }}
          .container {{
            max-width: 620px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
          }}
          .header {{
            background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
            padding: 32px 28px;
            color: #ffffff;
          }}
          .header h1 {{
            margin: 0;
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.5px;
          }}
          .header p {{
            margin: 6px 0 0 0;
            font-size: 13px;
            opacity: 0.9;
          }}
          .content {{
            padding: 28px;
            line-height: 1.65;
            font-size: 15px;
          }}
          .content h2 {{
            color: #0f172a;
            font-size: 18px;
            margin-top: 24px;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 6px;
          }}
          .content ul {{
            padding-left: 20px;
          }}
          .content li {{
            margin-bottom: 8px;
          }}
          .footer {{
            background-color: #f8fafc;
            border-top: 1px solid #e2e8f0;
            padding: 20px 28px;
            font-size: 12px;
            color: #64748b;
            text-align: center;
          }}
          .badge {{
            display: inline-block;
            background: #e0f2fe;
            color: #0369a1;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            margin-bottom: 8px;
          }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <span class="badge" style="background: rgba(255,255,255,0.2); color: #fff;">METEOROLOGY &bull; TECH &bull; RESOURCES</span>
            <h1>MetAKNews</h1>
            <p>Dispatches & Resource Intelligence from Andrew (Andy) Kieckhefer</p>
          </div>
          <div class="content">
            {html_body}
          </div>
          <div class="footer">
            <p>You received this because you reached out to <strong>metaknews@gmail.com</strong>.</p>
            <p>&copy; MetAKNews // Andy Kieckhefer &bull; All Rights Reserved</p>
            {tracking_pixel}
          </div>
        </div>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = f"MetAKNews <{EMAIL_USER}>"
    msg["To"] = to_email
    msg["Subject"] = reply_subject
    if original_msg_id:
        msg["In-Reply-To"] = original_msg_id
        msg["References"] = original_msg_id

    msg.attach(MIMEText(body_markdown, "plain"))
    msg.attach(MIMEText(styled_html, "html"))

    with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, [to_email], msg.as_string())

# ==========================================
# 🔄 MAIN AGENT POLLING LOOP
# ==========================================
def process_inbox():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
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

        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        from_header = msg.get("From", "")
        first_name, last_name, sender_email = parse_sender_name(from_header)
        subject = clean_subject(msg.get("Subject"))
        msg_id = msg.get("Message-ID")

        # Skip automated loops / self-emails
        if sender_email.lower() == EMAIL_USER.lower() or "no-reply" in sender_email.lower():
            continue

        print(f"\n📬 Inbound interaction from {first_name} {last_name} <{sender_email}>: '{subject}'")

        body = get_email_body(msg)
        inquiry_summary = body[:300] if body else "General newsletter request"

        # 1. Sync to HubSpot & Salesforce
        print("📊 Syncing lead data to HubSpot and Salesforce...")
        sync_to_hubspot(first_name, last_name, sender_email, inquiry_summary)
        sync_to_salesforce(first_name, last_name, sender_email, inquiry_summary)

        # 2. Generate personalized MetAKNews dispatch
        print("🧠 Crafting personalized MetAKNews edition with Gemini...")
        newsletter_md = generate_newsletter_content(first_name, subject, body)

        # 3. Deliver formatted email
        print(f"🚀 Sending MetAKNews dispatch to {sender_email}...")
        send_metak_email(sender_email, subject, newsletter_md, msg_id)
        print("✨ Completed successfully!")

    mail.close()
    mail.logout()

if __name__ == "__main__":
    print("=" * 60)
    print("🌤️  MetAKNews Agent Activated (Andy Kieckhefer)")
    print(f"📧 Listening on: {EMAIL_USER}")
    print("=" * 60)
    while True:
        try:
            process_inbox()
        except Exception as e:
            print(f"⚠️ Loop exception: {e}")
        time.sleep(15)
