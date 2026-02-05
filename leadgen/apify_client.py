"""
TalentMonkeys Lead Generation - Apify LinkedIn Jobs Scraper Client

Uses Apify's LinkedIn Jobs Scraper to find job postings with structured data.
Note: LinkedIn scraping can take 2-5 minutes per run due to rate limits.
"""
import os
import requests
import time
from typing import List, Dict, Optional
from config import BLACKLIST, RECRUITING_KEYWORDS

# Apify API settings (set via environment variable)
APIFY_TOKEN = os.getenv("APIFY_API_KEY", "")
APIFY_ACTOR = "curious_coder~linkedin-jobs-scraper"
APIFY_BASE_URL = "https://api.apify.com/v2"


class ApifyJobScraper:
    """Scrapes LinkedIn jobs via Apify"""

    def __init__(self, token: str = APIFY_TOKEN):
        self.token = token
        self.headers = {"Content-Type": "application/json"}

    def _build_linkedin_url(self, query: str, location: str = "Austria") -> str:
        """Build LinkedIn job search URL"""
        import urllib.parse
        keywords = urllib.parse.quote(query)
        loc = urllib.parse.quote(location)
        # f_TPR=r604800 = last week
        return f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={loc}&f_TPR=r604800"

    def start_scrape(self, queries: List[str], location: str = "Austria", max_items: int = 20) -> Optional[str]:
        """
        Start an async LinkedIn scrape job.
        Returns run_id that can be used to check status and get results.
        """
        urls = [self._build_linkedin_url(q, location) for q in queries]

        payload = {
            "urls": urls,
            "maxItems": max_items
        }

        url = f"{APIFY_BASE_URL}/acts/{APIFY_ACTOR}/runs?token={self.token}"

        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=30)
            if resp.status_code == 201:
                run_id = resp.json()["data"]["id"]
                print(f"  Apify run started: {run_id}")
                return run_id
            else:
                print(f"  Apify error: {resp.status_code} - {resp.text[:200]}")
                return None
        except Exception as e:
            print(f"  Apify exception: {e}")
            return None

    def check_status(self, run_id: str) -> str:
        """Check status of a scrape run. Returns: RUNNING, SUCCEEDED, FAILED, TIMED-OUT, ABORTED"""
        url = f"{APIFY_BASE_URL}/actor-runs/{run_id}?token={self.token}"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.json()["data"]["status"]
            return "UNKNOWN"
        except Exception as e:
            print(f"  Status check error: {e}")
            return "ERROR"

    def get_results(self, run_id: str) -> List[Dict]:
        """Get results from a completed scrape run"""
        # First get the dataset ID
        url = f"{APIFY_BASE_URL}/actor-runs/{run_id}?token={self.token}"
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                return []

            dataset_id = resp.json()["data"]["defaultDatasetId"]

            # Get items from dataset
            items_url = f"{APIFY_BASE_URL}/datasets/{dataset_id}/items?token={self.token}"
            items_resp = requests.get(items_url, timeout=30)

            if items_resp.status_code == 200:
                return items_resp.json()
            return []
        except Exception as e:
            print(f"  Results error: {e}")
            return []

    def scrape_and_wait(self, queries: List[str], location: str = "Austria",
                        max_items: int = 20, timeout_minutes: int = 5) -> List[Dict]:
        """
        Start scrape and wait for results (blocking).
        Use for smaller queries or when you need immediate results.
        """
        run_id = self.start_scrape(queries, location, max_items)
        if not run_id:
            return []

        print(f"  Waiting for LinkedIn scrape (max {timeout_minutes} min)...")
        max_checks = timeout_minutes * 6  # Check every 10 seconds

        for i in range(max_checks):
            time.sleep(10)
            status = self.check_status(run_id)
            print(f"    Status: {status}")

            if status == "SUCCEEDED":
                raw_jobs = self.get_results(run_id)
                return self._parse_jobs(raw_jobs)
            elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                print(f"  Scrape failed: {status}")
                return []

        print("  Scrape timed out")
        return []

    def _parse_jobs(self, raw_jobs: List[Dict]) -> List[Dict]:
        """Parse Apify job data into standard format"""
        jobs = []
        seen_companies = set()

        for job in raw_jobs:
            company = job.get("companyName", "")
            title = job.get("title", "")

            # Skip if no company
            if not company:
                continue

            # Skip duplicates
            company_key = company.lower().strip()
            if company_key in seen_companies:
                continue

            # Skip blacklisted
            if self._is_blacklisted(company):
                continue

            # Skip recruiting agencies
            if self._is_recruiting_agency(company, title):
                continue

            seen_companies.add(company_key)

            # Extract salary if available
            salary = job.get("salary", "")

            jobs.append({
                "job_title": title,
                "company_name": company,
                "company_name_clean": self._clean_company_name(company),
                "company_domain": self._guess_domain(company),
                "location": job.get("location", "Austria"),
                "salary_text": salary,
                "salary_num": self._parse_salary(salary),
                "job_url": job.get("jobUrl", ""),
                "job_description": job.get("description", "")[:500],
                "posted_date": job.get("postedDate", ""),
                "source": "LinkedIn (Apify)",
                "company_linkedin": job.get("companyUrl", ""),
                "applicants": job.get("applicantsCount", "")
            })

        return jobs

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

    def _clean_company_name(self, name: str) -> str:
        """Clean company name"""
        import re
        if not name:
            return ""
        result = re.sub(
            r'\s*(GmbH|AG|SE|KG|OG|e\.U\.|& Co\.?|Corp\.?|Inc\.?|Ltd\.?)\s*',
            '', name, flags=re.IGNORECASE
        )
        return result.strip().rstrip('.,- ')

    def _guess_domain(self, company: str) -> str:
        """Guess company domain from name"""
        import re
        clean = company.lower()
        clean = re.sub(r'\s*(gmbh|ag|se|kg|& co\.?|inc\.?|ltd\.?)\s*', '', clean)
        clean = re.sub(r'[^a-z0-9]', '', clean)
        if clean:
            return f"{clean}.com"  # Try .com first, Apollo will handle .at
        return ""

    def _parse_salary(self, salary_text: str) -> Optional[int]:
        """Parse salary number from text"""
        import re
        if not salary_text:
            return None

        text = salary_text.lower().replace(",", "").replace(".", "")
        # Try to find number
        match = re.search(r'(\d{2,3})[\s]?(\d{3})', text)
        if match:
            return int(match.group(1)) * 1000 + int(match.group(2))

        match = re.search(r'(\d{2,3})k', text)
        if match:
            return int(match.group(1)) * 1000

        return None


def test_apify():
    """Test Apify scraper"""
    scraper = ApifyJobScraper()

    print("=" * 60)
    print("TESTING APIFY LINKEDIN JOBS SCRAPER")
    print("=" * 60)

    # Start a scrape (non-blocking)
    print("\nStarting LinkedIn scrape for 'Sales Manager' in Austria...")
    run_id = scraper.start_scrape(["Sales Manager"], "Austria", max_items=5)

    if run_id:
        print(f"\nRun started! ID: {run_id}")
        print("Check status with: scraper.check_status(run_id)")
        print("Get results with: scraper.get_results(run_id)")
        print("\nNote: LinkedIn scrapes typically take 2-5 minutes.")

        # Optionally wait for results
        print("\nWaiting for results (this may take a few minutes)...")
        jobs = scraper.scrape_and_wait(["Marketing Manager"], "Austria", max_items=3, timeout_minutes=3)

        if jobs:
            print(f"\nFound {len(jobs)} jobs:")
            for job in jobs:
                print(f"\n  {job['job_title']}")
                print(f"    Company: {job['company_name']}")
                print(f"    Location: {job['location']}")


if __name__ == "__main__":
    test_apify()
