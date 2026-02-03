#!/usr/bin/env python3
"""
TalentMonkeys Lead Generation System
=====================================

FLOW:
1. Scrape Google Jobs (€65K+ salary only)
2. Enrich with HR contact via Apollo
3. Send outreach email automatically

Usage:
    python main.py                      # Full pipeline
    python main.py --test               # Test all components
    python main.py --dry-run            # Search only, no emails
    python main.py --weekly             # Weekly mode (more queries)

Scheduling (weekly, Monday 8am):
    0 8 * * 1 cd /path/to/leadgen && python main.py >> leadgen.log 2>&1
"""

import argparse
import time
import random
from datetime import datetime
from typing import List, Dict

from config import MAX_LEADS_PER_DAY, get_todays_category, CATEGORIES
from job_scraper import JobScraper
from apollo_client import ApolloClient
from email_client import EmailClient


class LeadGenPipeline:
    """Main lead generation pipeline"""

    def __init__(self, spreadsheet_id: str = None):
        self.scraper = JobScraper()
        self.apollo = ApolloClient()
        self.email = EmailClient()
        self.spreadsheet_id = spreadsheet_id

        # Optional: Google Sheets
        if spreadsheet_id:
            from sheets_client import SheetsClient
            self.sheets = SheetsClient(spreadsheet_id)
        else:
            self.sheets = None

    def run(self,
            min_salary: int = 65000,
            limit: int = MAX_LEADS_PER_DAY,
            weekly_mode: bool = False,
            dry_run: bool = False,
            send_approval: bool = True):
        """
        Run the complete pipeline

        Args:
            min_salary: Minimum salary filter (default: €65,000)
            limit: Max leads to process
            weekly_mode: Use all categories instead of daily rotation
            dry_run: Don't send emails, just search and show results
            send_approval: Send approval email first (vs direct outreach)
        """
        today_category, next_category = get_todays_category()

        print("\n" + "=" * 60)
        print(f"TALENTMONKEYS LEAD GENERATION")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"Min Salary: €{min_salary:,}")
        print(f"Mode: {'Weekly (all categories)' if weekly_mode else f'Daily ({today_category[\"name\"]})'}")
        print("=" * 60)

        # ================================================
        # STEP 1: SCRAPE JOBS
        # ================================================
        print(f"\n[STEP 1] Scraping Google Jobs (€{min_salary//1000}K+)...")

        if weekly_mode:
            # Use queries from all categories
            all_queries = []
            for cat in CATEGORIES:
                all_queries.extend(cat["queries"][:2])  # 2 queries per category
            jobs = self.scraper.search_multiple_categories(
                queries=all_queries,
                min_salary=min_salary,
                limit_per_query=10
            )
        else:
            # Use today's category
            jobs = self.scraper.search_multiple_categories(
                queries=today_category["queries"],
                min_salary=min_salary,
                limit_per_query=15
            )

        print(f"\n✓ Found {len(jobs)} jobs matching criteria")

        if not jobs:
            print("\nNo jobs found. Try different search terms or lower salary threshold.")
            return []

        # ================================================
        # STEP 2: ENRICH WITH HR CONTACTS
        # ================================================
        print(f"\n[STEP 2] Enriching with HR contacts (Apollo)...")

        enriched_leads = []

        for i, job in enumerate(jobs[:limit * 2]):  # Get more to account for failures
            if len(enriched_leads) >= limit:
                break

            company = job["company_name"]
            domain = job["company_domain"]

            print(f"\n  [{i+1}] {company}")
            print(f"      Job: {job['job_title']}")
            print(f"      Salary: {job['salary_text'] or 'Not specified'}")

            if not domain:
                print(f"      ✗ No domain found")
                continue

            # Check if already contacted
            if self.sheets:
                existing = self.sheets.find_lead_by_email(domain)  # Check by domain first
                if existing:
                    print(f"      ✗ Already in database")
                    continue

            # Get HR contact from Apollo
            lead = self.apollo.get_company_with_hr_contact(domain, company)

            if lead:
                # Merge job data with enriched data
                lead.update({
                    "job_title_original": job["job_title"],
                    "job_url": job["job_url"],
                    "job_salary": job["salary_text"],
                    "job_location": job["location"],
                    "category": today_category["name"] if not weekly_mode else "Weekly"
                })
                enriched_leads.append(lead)
                print(f"      ✓ HR Contact: {lead['hr_full_name']} ({lead['hr_email']})")

                # Rate limiting
                time.sleep(1)
            else:
                print(f"      ✗ No HR contact found")

        print(f"\n✓ Enriched {len(enriched_leads)} leads with HR contacts")

        if not enriched_leads:
            print("\nNo leads could be enriched. Check Apollo API quota.")
            return []

        # ================================================
        # STEP 3: SAVE TO SHEETS (if configured)
        # ================================================
        if self.sheets:
            print(f"\n[STEP 3] Saving to Google Sheets...")
            saved = 0
            for lead in enriched_leads:
                sheet_lead = {
                    "Datum": datetime.now().strftime("%Y-%m-%d"),
                    "Kategorie": lead.get("category", ""),
                    "Firma": lead.get("company_name", ""),
                    "Mitarbeiter": lead.get("employees", ""),
                    "Job Titel": lead.get("job_title_original", ""),
                    "Job URL": lead.get("job_url", ""),
                    "Gehalt": lead.get("job_salary", ""),
                    "HR Kontakt": lead.get("hr_full_name", ""),
                    "Email": lead.get("hr_email", ""),
                    "Telefon": lead.get("hr_phone", ""),
                    "LinkedIn": lead.get("hr_linkedin", ""),
                    "Status": "Neu",
                }
                if self.sheets.add_lead(sheet_lead):
                    saved += 1
            print(f"✓ Saved {saved} leads to Google Sheets")

        # DRY RUN - Stop here
        if dry_run:
            print("\n" + "=" * 60)
            print("DRY RUN - No emails sent")
            print("=" * 60)
            self._print_lead_summary(enriched_leads)
            return enriched_leads

        # ================================================
        # STEP 4: SEND EMAILS
        # ================================================
        if send_approval:
            # Send approval request first
            print(f"\n[STEP 4] Sending approval request...")
            self.email.send_approval_request(
                enriched_leads,
                today_category["name"],
                next_category["name"]
            )
            print(f"✓ Approval email sent to {self.email.service}")
            print("\nReply to approve leads, then run with --send-outreach")
        else:
            # Direct outreach (auto-approved)
            print(f"\n[STEP 4] Sending outreach emails...")
            self._send_outreach_with_delays(enriched_leads)

        return enriched_leads

    def _send_outreach_with_delays(self, leads: List[Dict]):
        """Send outreach emails with random delays"""
        if not self.email.is_business_hours():
            print("⚠ Outside business hours (Mo-Fr 8-18). Emails queued.")
            return

        sent = 0
        for i, lead in enumerate(leads):
            # Random delay 5-15 minutes between emails
            if i > 0:
                delay_mins = random.randint(5, 15)
                print(f"  Waiting {delay_mins} minutes...")
                time.sleep(delay_mins * 60)

            email = lead.get("hr_email", "")
            if not email:
                continue

            print(f"  Sending to {email}...")
            if self.email.send_outreach_email(lead):
                sent += 1
                print(f"    ✓ Sent")
                if self.sheets:
                    self.sheets.update_lead_status(email, "Gesendet")
            else:
                print(f"    ✗ Failed")

        print(f"\n✓ Sent {sent}/{len(leads)} outreach emails")

    def _print_lead_summary(self, leads: List[Dict]):
        """Print summary of found leads"""
        print("\n" + "-" * 60)
        print("LEAD SUMMARY")
        print("-" * 60)

        for i, lead in enumerate(leads, 1):
            print(f"\n{i}. {lead.get('company_name', 'Unknown')}")
            print(f"   Job: {lead.get('job_title_original', 'N/A')}")
            print(f"   Salary: {lead.get('job_salary', 'Not specified')}")
            print(f"   HR: {lead.get('hr_full_name', 'N/A')} - {lead.get('hr_email', 'N/A')}")
            print(f"   Employees: {lead.get('employees', 'N/A')}")

    def test_components(self):
        """Test all components"""
        print("\n" + "=" * 60)
        print("TESTING COMPONENTS")
        print("=" * 60)

        # Test Job Scraper
        print("\n[1] Testing Job Scraper (Google Jobs)...")
        try:
            jobs = self.scraper.search_jobs("Marketing Manager", "Austria", 65000, 3)
            if jobs:
                print(f"  ✓ Found {len(jobs)} jobs")
                for j in jobs:
                    print(f"    - {j['company_name']}: {j['job_title']}")
            else:
                print(f"  ⚠ No jobs found (might be API issue)")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        # Test Apollo
        print("\n[2] Testing Apollo API...")
        try:
            companies = self.apollo.search_organizations(
                keywords="software",
                locations=["Austria"],
                per_page=2
            )
            if companies:
                print(f"  ✓ Found {len(companies)} companies")
                domain = companies[0].get("primary_domain", "")
                if domain:
                    lead = self.apollo.get_company_with_hr_contact(domain)
                    if lead:
                        print(f"  ✓ HR Contact: {lead['hr_full_name']}")
            else:
                print(f"  ⚠ No companies found")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        # Test Email
        print("\n[3] Testing Email Setup...")
        print(f"  Business hours: {self.email.is_business_hours()}")
        refs = self.email.get_random_references(2)
        print(f"  ✓ References: {refs}")

        print("\n" + "=" * 60)
        print("TESTING COMPLETE")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="TalentMonkeys Lead Generation - Job Scraping + Enrichment + Outreach"
    )
    parser.add_argument("--spreadsheet-id", help="Google Sheets ID for tracking")
    parser.add_argument("--test", action="store_true", help="Test all components")
    parser.add_argument("--dry-run", action="store_true", help="Search only, no emails")
    parser.add_argument("--weekly", action="store_true", help="Weekly mode (all categories)")
    parser.add_argument("--no-approval", action="store_true", help="Skip approval, send directly")
    parser.add_argument("--min-salary", type=int, default=65000, help="Min salary in EUR (default: 65000)")
    parser.add_argument("--limit", type=int, default=MAX_LEADS_PER_DAY, help="Max leads (default: 50)")

    args = parser.parse_args()

    pipeline = LeadGenPipeline(spreadsheet_id=args.spreadsheet_id)

    if args.test:
        pipeline.test_components()
    else:
        pipeline.run(
            min_salary=args.min_salary,
            limit=args.limit,
            weekly_mode=args.weekly,
            dry_run=args.dry_run,
            send_approval=not args.no_approval
        )


if __name__ == "__main__":
    main()
