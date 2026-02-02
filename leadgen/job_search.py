"""
TalentMonkeys Lead Generation - Job/Company Search Module

Two approaches:
1. Serper API - Search for job postings (less reliable for company data)
2. Apollo API - Search for companies directly (RECOMMENDED!)
"""
import requests
import re
from typing import List, Dict, Optional
from config import (
    SERPER_API_KEY, BLACKLIST, RECRUITING_KEYWORDS,
    CATEGORIES, get_todays_category
)
from apollo_client import ApolloClient


class JobSearch:
    """Search for companies with open positions"""

    def __init__(self):
        self.apollo = ApolloClient()

    def is_blacklisted(self, company_name: str) -> bool:
        """Check if company is on blacklist"""
        if not company_name:
            return True
        lower = company_name.lower()
        return any(bl.lower() in lower for bl in BLACKLIST)

    def is_recruiting_agency(self, company_name: str, description: str = "") -> bool:
        """Check if company is a recruiting agency"""
        if not company_name:
            return True
        text = f"{company_name} {description}".lower()
        return any(kw in text for kw in RECRUITING_KEYWORDS)

    def clean_company_name(self, name: str) -> str:
        """Clean company name from legal suffixes"""
        if not name:
            return ""
        patterns = [
            r'\s*(GmbH|AG|SE|KG|OG|e\.U\.|& Co\.?|Corp\.?|Inc\.?|Ltd\.?|Ges\.?m\.?b\.?H\.?|Co\.? KG)\s*',
        ]
        result = name
        for pattern in patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        return result.strip().rstrip('.,- ')

    # ==========================================
    # METHOD 1: Apollo Company Search (BETTER!)
    # ==========================================

    def search_companies_apollo(self,
                                 industry_keywords: List[str] = None,
                                 locations: List[str] = None,
                                 min_employees: int = 50,
                                 max_employees: int = 500,
                                 limit: int = 50) -> List[Dict]:
        """
        Search for companies using Apollo's database
        This is MORE RELIABLE than Serper for finding real companies!
        """
        if locations is None:
            locations = ["Austria", "Vienna", "Graz", "Linz", "Salzburg"]

        all_companies = []
        seen_domains = set()

        # Map category to industry keywords
        category_keywords = {
            "IT": ["software", "technology", "IT services", "SaaS", "cloud"],
            "Sales": ["sales", "commerce", "retail", "distribution"],
            "Marketing": ["marketing", "advertising", "media", "digital"],
            "Finance": ["finance", "banking", "insurance", "investment"],
            "HR": ["human resources", "recruiting", "staffing"],
            "Engineering": ["engineering", "manufacturing", "industrial"],
            "Operations": ["logistics", "supply chain", "operations"]
        }

        # Get today's category
        today_category, next_category = get_todays_category()
        keywords = industry_keywords or category_keywords.get(today_category["name"], [""])

        print(f"Searching Apollo for companies in {today_category['name']}...")

        for keyword in keywords[:3]:  # Limit to 3 keywords to save API calls
            print(f"  Keyword: {keyword}")

            companies = self.apollo.search_organizations(
                keywords=keyword,
                locations=locations,
                min_employees=min_employees,
                max_employees=max_employees,
                per_page=25
            )

            for company in companies:
                domain = company.get("primary_domain", "")
                name = company.get("name", "")

                # Skip duplicates
                if domain in seen_domains:
                    continue
                seen_domains.add(domain)

                # Skip blacklisted
                if self.is_blacklisted(name):
                    print(f"    Skipping blacklisted: {name}")
                    continue

                # Skip recruiting agencies
                if self.is_recruiting_agency(name, company.get("industry", "")):
                    print(f"    Skipping recruiter: {name}")
                    continue

                all_companies.append({
                    "company_name": name,
                    "company_name_clean": self.clean_company_name(name),
                    "company_domain": domain,
                    "employees": company.get("estimated_num_employees", 0),
                    "industry": company.get("industry", ""),
                    "linkedin_url": company.get("linkedin_url", ""),
                    "category": today_category["name"],
                    "source": "apollo"
                })

                if len(all_companies) >= limit:
                    break

            if len(all_companies) >= limit:
                break

        print(f"Found {len(all_companies)} companies via Apollo")
        return all_companies[:limit]

    # ==========================================
    # METHOD 2: Serper Google Search (Backup)
    # ==========================================

    def search_jobs_serper(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for jobs using Serper API
        Returns job listing URLs from karriere.at, stepstone.at, linkedin
        """
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

        # Add job sites to query
        full_query = f"{query} site:karriere.at OR site:stepstone.at OR site:linkedin.com/jobs"

        data = {
            "q": full_query,
            "location": "Austria",
            "gl": "at",
            "hl": "de",
            "num": limit
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return self._parse_serper_results(result, query)
            else:
                print(f"Serper API error: {response.status_code}")
                return []

        except Exception as e:
            print(f"Serper API exception: {e}")
            return []

    def _parse_serper_results(self, result: Dict, category: str) -> List[Dict]:
        """Parse Serper search results"""
        jobs = []
        seen_urls = set()

        for item in result.get("organic", []):
            url = item.get("link", "")
            title = item.get("title", "")

            # Skip generic portal pages
            if url in ["https://www.karriere.at/", "https://www.stepstone.at/"]:
                continue
            if re.match(r'https?://\w+\.linkedin\.com/jobs/?$', url):
                continue

            # Skip duplicates
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Try to extract company from title
            company = self._extract_company_from_title(title)

            # Skip blacklisted
            if self.is_blacklisted(company) or self.is_blacklisted(title):
                continue

            jobs.append({
                "job_title": title,
                "job_url": url,
                "snippet": item.get("snippet", ""),
                "company_name": company,
                "category": category,
                "source": "serper"
            })

        return jobs

    def _extract_company_from_title(self, title: str) -> Optional[str]:
        """Try to extract company name from job title"""
        patterns = [
            r'bei\s+([A-Za-zÄÖÜäöüß\s&\-\.]+?)(?:\s*[-–|]|$)',
            r'at\s+([A-Za-zÄÖÜäöüß\s&\-\.]+?)(?:\s*[-–|]|$)',
            r'[-–|]\s*([A-Za-zÄÖÜäöüß\s&\-\.]+?)(?:\s*[-–|]|$)'
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match and len(match.group(1).strip()) > 2:
                return match.group(1).strip()

        return None


def test_search():
    """Test search functionality"""
    search = JobSearch()

    print("=" * 60)
    print("TESTING APOLLO COMPANY SEARCH (Recommended)")
    print("=" * 60)

    companies = search.search_companies_apollo(limit=10)

    for i, c in enumerate(companies, 1):
        print(f"\n{i}. {c['company_name']}")
        print(f"   Domain: {c['company_domain']}")
        print(f"   Employees: {c['employees']}")
        print(f"   Industry: {c['industry']}")

    print("\n" + "=" * 60)
    print("TESTING SERPER JOB SEARCH (Backup)")
    print("=" * 60)

    jobs = search.search_jobs_serper("Sales Manager Austria", limit=5)

    for i, j in enumerate(jobs, 1):
        print(f"\n{i}. {j['job_title'][:60]}...")
        print(f"   Company: {j.get('company_name', 'Unknown')}")
        print(f"   URL: {j['job_url'][:60]}...")


if __name__ == "__main__":
    test_search()
