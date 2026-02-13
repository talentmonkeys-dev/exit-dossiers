"""
TalentMonkeys Lead Generation - Apollo.io API Client
"""
import requests
import time
from typing import Optional, Dict, List, Any
from config import APOLLO_API_KEY, HR_TITLES, MIN_EMPLOYEES


class ApolloClient:
    """Client for Apollo.io API"""

    BASE_URL = "https://api.apollo.io/api/v1"

    def __init__(self, api_key: str = APOLLO_API_KEY):
        self.api_key = api_key
        self.headers = {
            "x-api-key": api_key,
            "Cache-Control": "no-cache",
            "accept": "application/json",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make API request with error handling"""
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            if method == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            else:
                response = requests.get(url, headers=self.headers, params=data, timeout=30)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                print(f"  Rate limited, waiting 60s...")
                time.sleep(60)
                return self._request(method, endpoint, data)
            else:
                print(f"  Apollo API error {response.status_code}: {response.text[:200]}")
                return None

        except Exception as e:
            print(f"  Apollo API exception: {e}")
            return None

    def enrich_organization(self, domain: str) -> Optional[Dict]:
        """Get organization data by domain"""
        data = {"domain": domain}
        result = self._request("POST", "organizations/enrich", data)

        if result and "organization" in result:
            return result["organization"]
        return None

    def search_people(self, domain: str, titles: List[str] = None) -> List[Dict]:
        """Search for people at an organization using the new API endpoint"""
        if titles is None:
            titles = HR_TITLES

        data = {
            "organization_domains": [domain],
            "person_titles": titles,
            "per_page": 5
        }

        # Use new API endpoint (mixed_people/search is deprecated)
        result = self._request("POST", "mixed_people/api_search", data)

        if result and "people" in result:
            return result["people"]
        return []

    def match_person(self, first_name: str, last_name: str, organization_name: str) -> Optional[Dict]:
        """Get verified contact info for a person"""
        data = {
            "first_name": first_name,
            "last_name": last_name,
            "organization_name": organization_name,
            "reveal_personal_emails": False,
            "reveal_phone_number": False  # Phone requires webhook, skip for now
        }

        result = self._request("POST", "people/match", data)

        if result and "person" in result:
            return result["person"]
        return None

    def search_organizations(self,
                            keywords: str = None,
                            locations: List[str] = None,
                            min_employees: int = MIN_EMPLOYEES,
                            max_employees: int = 500,
                            page: int = 1,
                            per_page: int = 25) -> List[Dict]:
        """
        Search for organizations directly in Apollo
        This is a better approach than Serper for finding companies!
        """
        data = {
            "per_page": per_page,
            "page": page,
            "organization_num_employees_ranges": [f"{min_employees},{max_employees}"],
        }

        if keywords:
            data["q_keywords"] = keywords

        if locations:
            data["organization_locations"] = locations
        else:
            # Default to Austria
            data["organization_locations"] = ["Austria"]

        result = self._request("POST", "mixed_companies/search", data)

        if result and "organizations" in result:
            return result["organizations"]
        return []

    def bulk_reveal(self, person_ids: List[str]) -> List[Dict]:
        """Reveal contact info for people using bulk_match endpoint"""
        if not person_ids:
            return []

        data = {
            "reveal_personal_emails": True,
            "details": [{"id": pid} for pid in person_ids]
        }

        result = self._request("POST", "people/bulk_match", data)

        if result and "matches" in result:
            return result["matches"]
        return []

    def get_company_with_hr_contact(self, domain: str, company_name: str = None) -> Optional[Dict]:
        """
        Full enrichment: Get company data + HR contact in one call
        Returns enriched lead data ready for outreach
        """
        # Step 1: Enrich organization
        org = self.enrich_organization(domain)

        if not org:
            return None

        # Check employee count
        employees = org.get("estimated_num_employees", 0)
        if employees < MIN_EMPLOYEES:
            print(f"  Skipping {domain}: only {employees} employees")
            return None

        # Step 2: Find HR contacts
        people = self.search_people(domain)

        if not people:
            print(f"  No HR contacts found for {domain}")
            return None

        # Get person ID for revealing contact info
        person_id = people[0].get("id")
        if not person_id:
            print(f"  No person ID for HR contact at {domain}")
            return None

        # Step 3: Use bulk_match to reveal email (more reliable than people/match)
        revealed = self.bulk_reveal([person_id])

        if not revealed:
            print(f"  Could not reveal contact info for {domain}")
            return None

        hr_contact = revealed[0]
        email = hr_contact.get("email", "")

        # Check if email matches the company domain (person may have changed jobs)
        if email and not email.endswith(f"@{domain}") and not email.endswith(domain.replace(".at", ".com")):
            # Person may have changed jobs - check organization
            contact_org = hr_contact.get("organization", {}).get("name", "").lower()
            company_lower = (company_name or org.get("name", "")).lower()
            if contact_org and company_lower not in contact_org and contact_org not in company_lower:
                print(f"  Contact {hr_contact.get('name')} no longer at {company_name} (now at {contact_org})")
                # Try next person if available
                if len(people) > 1:
                    person_id = people[1].get("id")
                    revealed = self.bulk_reveal([person_id])
                    if revealed:
                        hr_contact = revealed[0]
                        email = hr_contact.get("email", "")

        # Build enriched lead data (even without email - LinkedIn is valuable too)
        linkedin_url = hr_contact.get("linkedin_url", "")

        if not email and not linkedin_url:
            print(f"  No contact info found for {domain}")
            return None

        # Build enriched lead data
        return {
            "company_name": org.get("name", ""),
            "company_domain": domain,
            "company_website": org.get("website_url", f"https://{domain}"),
            "employees": employees,
            "industry": org.get("industry", ""),
            "linkedin_url": org.get("linkedin_url", ""),
            "hr_first_name": hr_contact.get("first_name", ""),
            "hr_last_name": hr_contact.get("last_name", ""),
            "hr_full_name": hr_contact.get("name", f"{hr_contact.get('first_name', '')} {hr_contact.get('last_name', '')}").strip(),
            "hr_title": hr_contact.get("title", ""),
            "hr_email": email,
            "hr_email_verified": hr_contact.get("email_status") == "verified",
            "hr_phone": None,  # Phone requires webhook
            "hr_linkedin": hr_contact.get("linkedin_url", "")
        }


def test_apollo():
    """Test Apollo API"""
    client = ApolloClient()

    print("Testing Apollo API...")

    # Test organization search (better than Serper!)
    print("\n1. Searching for Austrian companies...")
    companies = client.search_organizations(
        keywords="software",
        locations=["Austria", "Vienna"],
        min_employees=50,
        max_employees=500,
        per_page=5
    )

    for c in companies:
        print(f"  - {c.get('name')} ({c.get('primary_domain')}) - {c.get('estimated_num_employees')} employees")

    if companies:
        # Test full enrichment
        domain = companies[0].get("primary_domain")
        print(f"\n2. Full enrichment for {domain}...")
        lead = client.get_company_with_hr_contact(domain)

        if lead:
            print(f"  Company: {lead['company_name']}")
            print(f"  HR Contact: {lead['hr_full_name']} ({lead['hr_title']})")
            print(f"  Email: {lead['hr_email']} (verified: {lead['hr_email_verified']})")
            print(f"  Phone: {lead['hr_phone']}")


if __name__ == "__main__":
    test_apollo()
