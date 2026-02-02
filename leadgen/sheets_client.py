"""
TalentMonkeys Lead Generation - Google Sheets Client
"""
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

from config import SHEET_NAME, CONTACT_COOLDOWN_DAYS


# Scopes for Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Column mapping
COLUMNS = [
    "Datum", "Kategorie", "Firma", "Mitarbeiter", "Job Titel",
    "Job URL", "Gehalt", "HR Kontakt", "Email", "Telefon",
    "LinkedIn", "Weitere Jobs", "Status", "Letzter Kontakt", "Notizen"
]


class SheetsClient:
    """Google Sheets client for lead management"""

    def __init__(self, spreadsheet_id: str = None):
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Sheets API"""
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), 'token.pickle')
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
                    print("Please create it with your Google Cloud credentials.")
                    print("See: https://developers.google.com/sheets/api/quickstart/python")
                    return

                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save token
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('sheets', 'v4', credentials=creds)

    def create_spreadsheet(self, title: str = SHEET_NAME) -> str:
        """Create a new spreadsheet and return its ID"""
        spreadsheet = {
            'properties': {'title': title},
            'sheets': [{
                'properties': {'title': SHEET_NAME}
            }]
        }

        result = self.service.spreadsheets().create(
            body=spreadsheet,
            fields='spreadsheetId'
        ).execute()

        self.spreadsheet_id = result['spreadsheetId']
        print(f"Created spreadsheet: https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}")

        # Add headers
        self._add_headers()

        return self.spreadsheet_id

    def _add_headers(self):
        """Add header row to sheet"""
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{SHEET_NAME}!A1:{chr(64 + len(COLUMNS))}1",
            valueInputOption='RAW',
            body={'values': [COLUMNS]}
        ).execute()

    def get_all_leads(self) -> List[Dict]:
        """Get all leads from sheet"""
        if not self.service or not self.spreadsheet_id:
            return []

        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{SHEET_NAME}!A:O"
        ).execute()

        rows = result.get('values', [])

        if len(rows) < 2:  # Only header or empty
            return []

        # Convert to list of dicts
        headers = rows[0]
        leads = []

        for row in rows[1:]:
            lead = {}
            for i, header in enumerate(headers):
                lead[header] = row[i] if i < len(row) else ""
            leads.append(lead)

        return leads

    def find_lead_by_email(self, email: str) -> Optional[Dict]:
        """Find a lead by email address"""
        leads = self.get_all_leads()

        for lead in leads:
            if lead.get("Email", "").lower() == email.lower():
                return lead

        return None

    def was_contacted_recently(self, email: str) -> bool:
        """Check if lead was contacted within cooldown period"""
        lead = self.find_lead_by_email(email)

        if not lead:
            return False

        last_contact = lead.get("Letzter Kontakt", "")

        if not last_contact:
            return False

        try:
            contact_date = datetime.strptime(last_contact, "%Y-%m-%d")
            cooldown_date = datetime.now() - timedelta(days=CONTACT_COOLDOWN_DAYS)
            return contact_date > cooldown_date
        except:
            return False

    def add_lead(self, lead: Dict) -> bool:
        """Add a new lead to the sheet"""
        if not self.service or not self.spreadsheet_id:
            return False

        # Check for duplicate
        if self.find_lead_by_email(lead.get("Email", "")):
            print(f"  Lead already exists: {lead.get('Email')}")
            return False

        # Build row data
        row = [
            lead.get("Datum", datetime.now().strftime("%Y-%m-%d")),
            lead.get("Kategorie", ""),
            lead.get("Firma", ""),
            str(lead.get("Mitarbeiter", "")),
            lead.get("Job Titel", ""),
            lead.get("Job URL", ""),
            lead.get("Gehalt", ""),
            lead.get("HR Kontakt", ""),
            lead.get("Email", ""),
            lead.get("Telefon", ""),
            lead.get("LinkedIn", ""),
            lead.get("Weitere Jobs", ""),
            lead.get("Status", "Neu"),
            lead.get("Letzter Kontakt", ""),
            lead.get("Notizen", "")
        ]

        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{SHEET_NAME}!A:O",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [row]}
        ).execute()

        return True

    def update_lead_status(self, email: str, status: str, notes: str = None):
        """Update lead status by email"""
        if not self.service or not self.spreadsheet_id:
            return False

        # Find the row
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=f"{SHEET_NAME}!A:O"
        ).execute()

        rows = result.get('values', [])

        for i, row in enumerate(rows):
            if len(row) > 8 and row[8].lower() == email.lower():  # Email is column I (index 8)
                # Update status (column M, index 12)
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{SHEET_NAME}!M{i+1}",
                    valueInputOption='RAW',
                    body={'values': [[status]]}
                ).execute()

                # Update last contact (column N, index 13)
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"{SHEET_NAME}!N{i+1}",
                    valueInputOption='RAW',
                    body={'values': [[datetime.now().strftime("%Y-%m-%d")]]}
                ).execute()

                # Update notes if provided
                if notes:
                    current_notes = row[14] if len(row) > 14 else ""
                    new_notes = f"{current_notes}\n{datetime.now().strftime('%Y-%m-%d')}: {notes}".strip()
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f"{SHEET_NAME}!O{i+1}",
                        valueInputOption='RAW',
                        body={'values': [[new_notes]]}
                    ).execute()

                return True

        return False

    def get_leads_by_status(self, status: str) -> List[Dict]:
        """Get all leads with a specific status"""
        leads = self.get_all_leads()
        return [l for l in leads if l.get("Status", "").lower() == status.lower()]


def test_sheets():
    """Test Google Sheets integration"""
    print("Testing Google Sheets client...")
    print("Note: You need credentials.json in the leadgen folder")

    # Check for credentials
    creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    if not os.path.exists(creds_path):
        print(f"\nCredentials file not found at: {creds_path}")
        print("\nTo set up:")
        print("1. Go to Google Cloud Console")
        print("2. Create OAuth 2.0 credentials")
        print("3. Download as credentials.json")
        print("4. Place in the leadgen folder")
        return

    client = SheetsClient()

    # For testing, you can create a new spreadsheet
    # spreadsheet_id = client.create_spreadsheet("TalentMonkeys Leads Test")

    print("Google Sheets client initialized successfully!")


if __name__ == "__main__":
    test_sheets()
