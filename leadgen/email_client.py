"""
TalentMonkeys Lead Generation - Email Client (Gmail API)
"""
import os
import base64
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

from config import (
    APPROVAL_EMAIL, SENDER_NAME, COMPANY_NAME, COMPANY_WEBSITE,
    REFERENCE_CUSTOMERS, BUSINESS_HOURS_START, BUSINESS_HOURS_END
)


# Scopes for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']


class EmailClient:
    """Gmail client for sending emails"""

    def __init__(self):
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), 'gmail_token.pickle')
        creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')

        # Load existing token
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_path):
                    print("ERROR: credentials.json not found!")
                    return

                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save token
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)

    def _create_message(self, to: str, subject: str, body: str) -> Dict:
        """Create email message"""
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        message.attach(MIMEText(body, 'plain'))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw}

    def send_email(self, to: str, subject: str, body: str) -> bool:
        """Send an email"""
        if not self.service:
            print("Gmail service not initialized")
            return False

        try:
            message = self._create_message(to, subject, body)
            self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

    def is_business_hours(self) -> bool:
        """Check if current time is within business hours (Vienna)"""
        now = datetime.now()
        # Check weekday (0=Monday, 6=Sunday)
        if now.weekday() > 4:  # Weekend
            return False
        # Check hours
        return BUSINESS_HOURS_START <= now.hour < BUSINESS_HOURS_END

    def get_random_references(self, count: int = 2) -> List[str]:
        """Get random reference customers"""
        return random.sample(REFERENCE_CUSTOMERS, min(count, len(REFERENCE_CUSTOMERS)))

    # ==========================================
    # APPROVAL EMAIL
    # ==========================================

    def send_approval_request(self, leads: List[Dict], category: str, next_category: str) -> bool:
        """Send approval request email to Flavio"""
        date = datetime.now().strftime("%Y-%m-%d")

        # Build leads list
        leads_text = ""
        for i, lead in enumerate(leads, 1):
            leads_text += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LEAD {i}:
🏢 Firma: {lead.get('Firma', lead.get('company_name', 'Unknown'))}
💼 Position: {lead.get('Job Titel', lead.get('hr_title', 'HR Contact'))}
💰 Mitarbeiter: {lead.get('Mitarbeiter', lead.get('employees', 'N/A'))}
👤 HR: {lead.get('HR Kontakt', lead.get('hr_full_name', 'N/A'))}
📧 {lead.get('Email', lead.get('hr_email', 'N/A'))}
📞 {lead.get('Telefon', lead.get('hr_phone', 'N/A'))}
🔗 {lead.get('LinkedIn', lead.get('hr_linkedin', 'N/A'))}

→ "{i} OK" oder "{i} SKIP"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        body = f"""Hallo Flavio,

Heute: {category} Leads

Hier sind {len(leads)} Leads zur Freigabe:
{leads_text}

Antworte mit: "1 OK, 2 OK, 3 SKIP, 4 OK" etc.

Morgen: {next_category} Leads

Viele Grüße,
Dein Lead Generation System"""

        subject = f"🎯 {len(leads)} neue {category} Leads zur Freigabe - {date}"

        return self.send_email(APPROVAL_EMAIL, subject, body)

    # ==========================================
    # OUTREACH EMAIL
    # ==========================================

    def create_outreach_email(self, lead: Dict) -> tuple:
        """Create personalized outreach email"""
        first_name = lead.get('vorname', lead.get('hr_first_name', ''))
        if not first_name:
            full_name = lead.get('HR Kontakt', lead.get('hr_full_name', ''))
            first_name = full_name.split()[0] if full_name else 'Guten Tag'

        job_title = lead.get('Job Titel', lead.get('hr_title', 'offene Position'))
        company = lead.get('Firma', lead.get('company_name', 'Ihr Unternehmen'))

        # Get random references
        refs = self.get_random_references(2)

        subject = job_title

        body = f"""Hallo {first_name},

ich bin auf Ihre offene {job_title} Position aufmerksam geworden.

Wir bei {COMPANY_NAME} sind auf genau solche Positionen spezialisiert und arbeiten rein erfolgsbasiert. Sie zahlen nur bei erfolgreicher Besetzung.

Firmen wie {refs[0]} und {refs[1]} vertrauen bereits auf uns.

Hätten Sie diese Woche kurz Zeit für ein Telefonat?

Beste Grüße
{SENDER_NAME}

{COMPANY_NAME}
{COMPANY_WEBSITE}"""

        return subject, body

    def send_outreach_email(self, lead: Dict) -> bool:
        """Send outreach email to a lead"""
        if not self.is_business_hours():
            print("  Outside business hours, skipping...")
            return False

        email = lead.get('Email', lead.get('hr_email', ''))
        if not email:
            print("  No email address, skipping...")
            return False

        subject, body = self.create_outreach_email(lead)
        return self.send_email(email, subject, body)

    # ==========================================
    # NEGATIVE RESPONSE HANDLING
    # ==========================================

    def create_friendly_reply(self, first_name: str) -> tuple:
        """Create friendly response to negative reply"""
        subject = "Re: Ihre Anfrage"

        body = f"""Hallo {first_name},

vielen Dank für Ihre Rückmeldung.

Sollte sich in Zukunft Bedarf ergeben, stehe ich gerne zur Verfügung.

Alles Gute!

Beste Grüße
{SENDER_NAME}
{COMPANY_NAME}"""

        return subject, body

    def send_friendly_reply(self, to: str, first_name: str) -> bool:
        """Send friendly reply to negative response"""
        subject, body = self.create_friendly_reply(first_name)
        return self.send_email(to, subject, body)


# ==========================================
# NEGATIVE RESPONSE DETECTION
# ==========================================

NEGATIVE_KEYWORDS = [
    "kein interesse", "nicht interessiert", "keine weiteren", "bitte nicht mehr",
    "abbestellen", "unsubscribe", "remove", "stop", "nein danke", "no thank",
    "nicht kontaktieren", "aus dem verteiler", "kein bedarf", "nicht benötigt",
    "please stop", "do not contact", "keine emails", "spam",
    "entfernen sie mich", "abmelden", "nicht mehr kontaktieren"
]

POSITIVE_KEYWORDS = [
    "interesse", "interessiert", "ja gerne", "vereinbaren",
    "termin", "telefonat", "gespräch", "kontaktieren sie",
    "rufen sie", "anrufen", "weiter", "mehr erfahren",
    "sounds good", "let's talk", "call me"
]


def detect_response_type(text: str) -> str:
    """Detect if response is negative, positive, or neutral"""
    lower = text.lower()

    is_negative = any(kw in lower for kw in NEGATIVE_KEYWORDS)
    is_positive = any(kw in lower for kw in POSITIVE_KEYWORDS)

    if is_negative:
        return "negative"
    elif is_positive and not is_negative:
        return "positive"
    else:
        return "neutral"


def test_email():
    """Test email functionality"""
    print("Testing Email client...")
    print("Note: You need credentials.json in the leadgen folder")

    creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    if not os.path.exists(creds_path):
        print(f"\nCredentials file not found at: {creds_path}")
        return

    client = EmailClient()

    # Test reference selection
    refs = client.get_random_references(2)
    print(f"Random references: {refs}")

    # Test business hours check
    print(f"Is business hours: {client.is_business_hours()}")

    # Test email creation
    test_lead = {
        "hr_first_name": "Max",
        "hr_title": "HR Manager",
        "company_name": "Test GmbH"
    }
    subject, body = client.create_outreach_email(test_lead)
    print(f"\nSample email:")
    print(f"Subject: {subject}")
    print(f"Body:\n{body}")


if __name__ == "__main__":
    test_email()
