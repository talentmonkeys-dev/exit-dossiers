#!/usr/bin/env python3
"""
TalentMonkeys Lead Generation System
=====================================

A complete lead generation pipeline:
1. Search for companies (via Apollo - more reliable than job boards)
2. Enrich with HR contact data
3. Store in Google Sheets
4. Send approval request to Flavio
5. Send outreach emails to approved leads

Usage:
    python main.py                    # Run full pipeline
    python main.py --search-only      # Only search and enrich
    python main.py --send-approvals   # Send approval email for pending leads
    python main.py --test             # Test all components

Scheduling:
    Add to crontab for daily execution at 8am:
    0 8 * * 1-5 cd /path/to/leadgen && python main.py >> leadgen.log 2>&1
"""

import argparse
import time
import random
from datetime import datetime
from typing import List, Dict

from config import (
    MAX_LEADS_PER_DAY, get_todays_category
)
from apollo_client import ApolloClient
from job_search import JobSearch
from email_client import EmailClient


class LeadGenPipeline:
    """Main lead generation pipeline"""

    def __init__(self, spreadsheet_id: str = None):
        self.apollo = ApolloClient()
        self.search = JobSearch()
        self.email = EmailClient()
        self.spreadsheet_id = spreadsheet_id

        # Only import sheets if spreadsheet_id is provided
        if spreadsheet_id:
            from sheets_client import SheetsClient
            self.sheets = SheetsClient(spreadsheet_id)
        else:
            self.sheets = None

    def run_search_and_enrich(self, limit: int = MAX_LEADS_PER_DAY) -> List[Dict]:
        """
        Step 1 & 2: Search for companies and enrich with HR contacts
        """
        today_category, next_category = get_todays_category()
        print(f"\n{'='*60}")
        print(f"LEAD GENERATION - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"Today's Category: {today_category['name']}")
        print(f"{'='*60}")

        # Search for companies using Apollo (more reliable!)
        print(f"\n[1/3] Searching for companies...")
        companies = self.search.search_companies_apollo(limit=limit * 2)  # Get more to account for filtering
        print(f"Found {len(companies)} companies")

        # Enrich each company with HR contact
        print(f"\n[2/3] Enriching with HR contacts...")
        enriched_leads = []

        for i, company in enumerate(companies):
            if len(enriched_leads) >= limit:
                break

            domain = company.get("company_domain", "")
            name = company.get("company_name", "")

            print(f"  [{i+1}/{len(companies)}] {name} ({domain})...")

            # Check if already contacted (if sheets connected)
            if self.sheets:
                email_check = company.get("hr_email", "")
                if email_check and self.sheets.was_contacted_recently(email_check):
                    print(f"    Skipping - contacted recently")
                    continue

            # Get full enrichment
            lead = self.apollo.get_company_with_hr_contact(domain, name)

            if lead:
                # Add category info
                lead["category"] = today_category["name"]
                lead["scraped_at"] = datetime.now().isoformat()

                enriched_leads.append(lead)
                print(f"    ✓ Found: {lead['hr_full_name']} ({lead['hr_email']})")

                # Rate limiting - be nice to Apollo API
                time.sleep(1)
            else:
                print(f"    ✗ No HR contact found")

        print(f"\n[3/3] Enrichment complete: {len(enriched_leads)} leads with HR contacts")

        return enriched_leads

    def save_to_sheets(self, leads: List[Dict]) -> int:
        """
        Step 3: Save leads to Google Sheets
        """
        if not self.sheets:
            print("Google Sheets not configured, skipping save")
            return 0

        print(f"\nSaving {len(leads)} leads to Google Sheets...")
        saved = 0

        for lead in leads:
            # Convert to sheet format
            sheet_lead = {
                "Datum": datetime.now().strftime("%Y-%m-%d"),
                "Kategorie": lead.get("category", ""),
                "Firma": lead.get("company_name", ""),
                "Mitarbeiter": lead.get("employees", ""),
                "Job Titel": lead.get("hr_title", ""),
                "Job URL": lead.get("company_website", ""),
                "Gehalt": "",
                "HR Kontakt": lead.get("hr_full_name", ""),
                "Email": lead.get("hr_email", ""),
                "Telefon": lead.get("hr_phone", ""),
                "LinkedIn": lead.get("hr_linkedin", ""),
                "Weitere Jobs": "",
                "Status": "Neu",
                "Letzter Kontakt": "",
                "Notizen": f"Industry: {lead.get('industry', '')}"
            }

            if self.sheets.add_lead(sheet_lead):
                saved += 1

        print(f"Saved {saved} new leads to Google Sheets")
        return saved

    def send_approval_request(self, leads: List[Dict]) -> bool:
        """
        Step 4: Send approval request email
        """
        if not leads:
            print("No leads to approve")
            return False

        today_category, next_category = get_todays_category()

        print(f"\nSending approval request for {len(leads)} leads...")
        success = self.email.send_approval_request(
            leads,
            today_category["name"],
            next_category["name"]
        )

        if success:
            print(f"✓ Approval request sent to {self.email.service}")
        else:
            print("✗ Failed to send approval request")

        return success

    def send_outreach_emails(self, leads: List[Dict], delay_range: tuple = (5, 15)) -> int:
        """
        Step 5: Send outreach emails with random delays
        """
        if not self.email.is_business_hours():
            print("Outside business hours, skipping outreach")
            return 0

        print(f"\nSending outreach emails...")
        sent = 0

        for i, lead in enumerate(leads):
            print(f"  [{i+1}/{len(leads)}] {lead.get('hr_email', 'N/A')}...")

            # Random delay between emails
            if i > 0:
                delay = random.randint(*delay_range) * 60  # Convert to seconds
                print(f"    Waiting {delay//60} minutes...")
                time.sleep(delay)

            if self.email.send_outreach_email(lead):
                sent += 1
                print(f"    ✓ Sent")

                # Update sheet status
                if self.sheets:
                    self.sheets.update_lead_status(
                        lead.get("hr_email", lead.get("Email", "")),
                        "Gesendet"
                    )
            else:
                print(f"    ✗ Failed")

        print(f"\nSent {sent}/{len(leads)} outreach emails")
        return sent

    def run_full_pipeline(self, limit: int = MAX_LEADS_PER_DAY, auto_approve: bool = False):
        """
        Run the complete pipeline
        """
        # Step 1 & 2: Search and enrich
        leads = self.run_search_and_enrich(limit)

        if not leads:
            print("\nNo leads found, exiting.")
            return

        # Step 3: Save to sheets
        if self.sheets:
            self.save_to_sheets(leads)

        # Step 4: Send approval request (or auto-approve for testing)
        if auto_approve:
            print("\n[AUTO-APPROVE MODE] Skipping approval, sending outreach directly...")
            self.send_outreach_emails(leads)
        else:
            self.send_approval_request(leads)
            print("\nWaiting for approval via email reply...")
            print("Run with --send-outreach after approval to send emails")

    def test_all_components(self):
        """Test all system components"""
        print("\n" + "="*60)
        print("TESTING ALL COMPONENTS")
        print("="*60)

        # Test Apollo
        print("\n[1] Testing Apollo API...")
        try:
            companies = self.apollo.search_organizations(
                keywords="software",
                locations=["Austria"],
                per_page=3
            )
            print(f"  ✓ Apollo search works - found {len(companies)} companies")

            if companies:
                domain = companies[0].get("primary_domain")
                lead = self.apollo.get_company_with_hr_contact(domain)
                if lead:
                    print(f"  ✓ Apollo enrichment works - {lead['hr_full_name']}")
                else:
                    print(f"  ✗ Apollo enrichment returned no HR contact")
        except Exception as e:
            print(f"  ✗ Apollo error: {e}")

        # Test Email
        print("\n[2] Testing Email...")
        try:
            print(f"  Business hours: {self.email.is_business_hours()}")
            refs = self.email.get_random_references(2)
            print(f"  ✓ Random references: {refs}")
        except Exception as e:
            print(f"  ✗ Email error: {e}")

        # Test Sheets (if configured)
        if self.sheets:
            print("\n[3] Testing Google Sheets...")
            try:
                leads = self.sheets.get_all_leads()
                print(f"  ✓ Sheets works - {len(leads)} existing leads")
            except Exception as e:
                print(f"  ✗ Sheets error: {e}")
        else:
            print("\n[3] Google Sheets not configured (no spreadsheet_id)")

        print("\n" + "="*60)
        print("TESTING COMPLETE")
        print("="*60)


def main():
    parser = argparse.ArgumentParser(description="TalentMonkeys Lead Generation")
    parser.add_argument("--spreadsheet-id", help="Google Sheets spreadsheet ID")
    parser.add_argument("--search-only", action="store_true", help="Only search and enrich, no emails")
    parser.add_argument("--send-outreach", action="store_true", help="Send outreach to approved leads")
    parser.add_argument("--auto-approve", action="store_true", help="Skip approval, send outreach directly")
    parser.add_argument("--test", action="store_true", help="Test all components")
    parser.add_argument("--limit", type=int, default=MAX_LEADS_PER_DAY, help="Max leads to process")

    args = parser.parse_args()

    pipeline = LeadGenPipeline(spreadsheet_id=args.spreadsheet_id)

    if args.test:
        pipeline.test_all_components()
    elif args.search_only:
        leads = pipeline.run_search_and_enrich(args.limit)
        print(f"\n\nFound {len(leads)} leads:")
        for lead in leads:
            print(f"  - {lead['company_name']}: {lead['hr_full_name']} ({lead['hr_email']})")
    elif args.send_outreach:
        # Get approved leads from sheets and send outreach
        if pipeline.sheets:
            leads = pipeline.sheets.get_leads_by_status("Freigegeben")
            if leads:
                pipeline.send_outreach_emails(leads)
            else:
                print("No approved leads found")
        else:
            print("Google Sheets not configured")
    else:
        pipeline.run_full_pipeline(args.limit, auto_approve=args.auto_approve)


if __name__ == "__main__":
    main()
