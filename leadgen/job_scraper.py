"""
TalentMonkeys Lead Generation - Job Scraper

Scrapes REAL job postings from Google Jobs with salary filtering.
Uses Serper's Google Jobs API which returns structured data including:
- Job title
- Company name
- Salary (when available)
- Location
- Job description
"""
import requests
import re
from typing import List, Dict, Optional
from config import SERPER_API_KEY, BLACKLIST, RECRUITING_KEYWORDS


class JobScraper:
    """Scrapes job postings from Google Jobs"""

    SERPER_URL = "https://google.serper.dev/jobs"

    def __init__(self):
        self.headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

    def search_jobs(self,
                    query: str,
                    location: str = "Austria",
                    min_salary: int = 65000,
                    limit: int = 50) -> List[Dict]:
        """
        Search for jobs using Google Jobs API

        Args:
            query: Job search query (e.g., "Sales Manager")
            location: Location filter
            min_salary: Minimum salary in EUR (default: 65000)
            limit: Maximum number of jobs to return
        """
        # Add salary to query for better filtering
        salary_query = f"{query} €{min_salary//1000}k+ OR {min_salary}+ EUR"

        data = {
            "q": query,
            "location": location,
            "gl": "at",
            "hl": "de",
            "num": 100  # Get more to filter
        }

        try:
            response = requests.post(
                self.SERPER_URL,
                headers=self.headers,
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                jobs = self._parse_jobs(result, min_salary)
                return jobs[:limit]
            else:
                print(f"Serper Jobs API error: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return []

        except Exception as e:
            print(f"Serper Jobs API exception: {e}")
            return []

    def _parse_jobs(self, result: Dict, min_salary: int) -> List[Dict]:
        """Parse and filter job results"""
        jobs = []
        seen_companies = set()

        for job in result.get("jobs", []):
            company = job.get("companyName", "")
            title = job.get("title", "")

            # Skip if no company
            if not company:
                continue

            # Skip duplicates (one job per company)
            company_key = company.lower().strip()
            if company_key in seen_companies:
                continue

            # Skip blacklisted companies
            if self._is_blacklisted(company):
                continue

            # Skip recruiting agencies
            if self._is_recruiting_agency(company, title):
                continue

            # Extract and check salary
            salary_info = self._extract_salary(job)

            if salary_info["salary_num"] and salary_info["salary_num"] < min_salary:
                continue  # Skip low salary jobs

            seen_companies.add(company_key)

            # Extract company domain
            domain = self._extract_domain(company, job.get("link", ""))

            jobs.append({
                "job_title": title,
                "company_name": company,
                "company_name_clean": self._clean_company_name(company),
                "company_domain": domain,
                "location": job.get("location", ""),
                "salary_text": salary_info["salary_text"],
                "salary_num": salary_info["salary_num"],
                "job_url": job.get("link", ""),
                "job_description": job.get("snippet", ""),
                "posted_date": job.get("date", ""),
                "source": job.get("source", "Google Jobs"),
                "extensions": job.get("extensions", [])
            })

        return jobs

    def _extract_salary(self, job: Dict) -> Dict:
        """Extract salary information from job data"""
        salary_text = ""
        salary_num = None

        # Check extensions for salary info
        extensions = job.get("extensions", [])
        for ext in extensions:
            ext_lower = ext.lower()
            # Look for salary patterns
            if "€" in ext or "eur" in ext_lower or "gehalt" in ext_lower:
                salary_text = ext
                salary_num = self._parse_salary_number(ext)
                break

        # Check detected extensions
        detected = job.get("detected_extensions", {})
        if detected.get("salary"):
            salary_text = detected["salary"]
            salary_num = self._parse_salary_number(salary_text)

        # Check snippet for salary mentions
        if not salary_num:
            snippet = job.get("snippet", "")
            salary_num = self._parse_salary_number(snippet)
            if salary_num:
                salary_text = f"~€{salary_num:,}"

        return {"salary_text": salary_text, "salary_num": salary_num}

    def _parse_salary_number(self, text: str) -> Optional[int]:
        """Parse salary number from text"""
        if not text:
            return None

        text = text.lower().replace(".", "").replace(",", "")

        # Pattern: €65.000 or 65000 EUR or 65k
        patterns = [
            r'€\s*(\d{2,3})\.?(\d{3})',  # €65.000 or €65000
            r'(\d{2,3})\.?(\d{3})\s*(?:€|eur)',  # 65.000€ or 65000 EUR
            r'€\s*(\d{2,3})k',  # €65k
            r'(\d{2,3})k\s*(?:€|eur)',  # 65k EUR
            r'ab\s*€?\s*(\d{2,3})\.?(\d{3})',  # ab €65.000
            r'(\d{2,3})\.?(\d{3})\s*(?:brutto|jahresgehalt|annual)',  # 65000 brutto
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return int(groups[0]) * 1000 + int(groups[1]) if groups[1] else int(groups[0]) * 1000
                elif len(groups) == 1:
                    num = int(groups[0])
                    return num * 1000 if num < 1000 else num

        return None

    def _extract_domain(self, company: str, job_url: str) -> str:
        """Extract company domain from company name or job URL"""
        # Try to get from job URL first
        if job_url:
            # LinkedIn job URLs often have company info
            if "linkedin.com" in job_url:
                match = re.search(r'/company/([^/]+)', job_url)
                if match:
                    return f"{match.group(1)}.com"

            # karriere.at URLs
            if "karriere.at" in job_url:
                match = re.search(r'/firma/([^/]+)', job_url)
                if match:
                    return f"{match.group(1)}.at"

        # Generate from company name
        clean = company.lower()
        clean = re.sub(r'\s*(gmbh|ag|se|kg|co\.?\s*kg|& co\.?|inc\.?|ltd\.?|ges\.?m\.?b\.?h\.?)\s*', '', clean)
        clean = re.sub(r'[^a-z0-9]', '', clean)

        if clean:
            return f"{clean}.at"

        return ""

    def _clean_company_name(self, name: str) -> str:
        """Clean company name"""
        if not name:
            return ""
        result = re.sub(
            r'\s*(GmbH|AG|SE|KG|OG|e\.U\.|& Co\.?|Corp\.?|Inc\.?|Ltd\.?|Ges\.?m\.?b\.?H\.?|Co\.? KG)\s*',
            '', name, flags=re.IGNORECASE
        )
        return result.strip().rstrip('.,- ')

    def _is_blacklisted(self, company: str) -> bool:
        """Check if company is blacklisted"""
        if not company:
            return True
        lower = company.lower()
        return any(bl.lower() in lower for bl in BLACKLIST)

    def _is_recruiting_agency(self, company: str, title: str = "") -> bool:
        """Check if company is a recruiting agency"""
        text = f"{company} {title}".lower()
        return any(kw in text for kw in RECRUITING_KEYWORDS)

    def search_multiple_categories(self,
                                   queries: List[str],
                                   location: str = "Austria",
                                   min_salary: int = 65000,
                                   limit_per_query: int = 20) -> List[Dict]:
        """Search multiple job categories"""
        all_jobs = []
        seen_companies = set()

        for query in queries:
            print(f"  Searching: {query}...")
            jobs = self.search_jobs(query, location, min_salary, limit_per_query)

            for job in jobs:
                company_key = job["company_name"].lower().strip()
                if company_key not in seen_companies:
                    seen_companies.add(company_key)
                    all_jobs.append(job)

            print(f"    Found {len(jobs)} jobs")

        return all_jobs


def test_job_scraper():
    """Test job scraper"""
    scraper = JobScraper()

    print("=" * 60)
    print("TESTING JOB SCRAPER (Google Jobs via Serper)")
    print("=" * 60)

    # Test single search
    print("\nSearching for Sales Manager jobs in Austria (€65K+)...")
    jobs = scraper.search_jobs(
        query="Sales Manager",
        location="Austria",
        min_salary=65000,
        limit=10
    )

    print(f"\nFound {len(jobs)} jobs:\n")

    for i, job in enumerate(jobs, 1):
        print(f"{i}. {job['job_title']}")
        print(f"   Company: {job['company_name']}")
        print(f"   Domain: {job['company_domain']}")
        print(f"   Salary: {job['salary_text'] or 'Not specified'}")
        print(f"   Location: {job['location']}")
        print(f"   URL: {job['job_url'][:60]}...")
        print()


if __name__ == "__main__":
    test_job_scraper()
