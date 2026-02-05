"""
TalentMonkeys Lead Generation - Job Scraper

Scrapes REAL job postings from multiple sources:
1. Google Search (via Serper) targeting Austrian job sites
2. LinkedIn Jobs (via Apify) - optional, takes longer but has better data
"""
import requests
import re
from typing import List, Dict, Optional
from config import SERPER_API_KEY, BLACKLIST, RECRUITING_KEYWORDS


class JobScraper:
    """Scrapes job postings from Google Jobs"""

    # Use regular search endpoint targeting job sites
    SERPER_URL = "https://google.serper.dev/search"

    # Austrian locations to filter for
    AUSTRIA_LOCATIONS = [
        "austria", "österreich", "oesterreich",
        "wien", "vienna", "graz", "linz", "salzburg", "innsbruck",
        "klagenfurt", "villach", "wels", "st. pölten", "dornbirn",
        "wiener neustadt", "steyr", "feldkirch", "bregenz", "leonding",
        "lower austria", "upper austria", "styria", "tyrol", "carinthia",
        "vorarlberg", "burgenland", "niederösterreich", "oberösterreich",
        "steiermark", "tirol", "kärnten"
    ]

    def __init__(self):
        self.headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }

    def _is_austria_location(self, location: str) -> bool:
        """Check if location is in Austria"""
        if not location:
            return False
        location_lower = location.lower()
        return any(loc in location_lower for loc in self.AUSTRIA_LOCATIONS)

    def search_jobs(self,
                    query: str,
                    location: str = "Austria",
                    min_salary: int = 65000,
                    limit: int = 50) -> List[Dict]:
        """
        Search for jobs using Serper Google Search

        Args:
            query: Job search query (e.g., "Sales Manager")
            location: Location filter
            min_salary: Minimum salary in EUR (default: 65000)
            limit: Maximum number of jobs to return
        """
        all_jobs = []
        seen_companies = set()

        # Search across multiple ATS platforms for better company extraction
        search_queries = [
            f'{query} {location} personio',  # Personio ATS
            f'{query} {location} karriere.at/firma',  # karriere.at company pages
            f'{query} Wien hiring',  # Vienna specific
            f'{query} Österreich stellenangebot',  # German job posting term
        ]

        for search_query in search_queries:
            data = {
                "q": search_query,
                "num": 30
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
                    jobs = self._parse_search_results(result, min_salary, query)
                    for job in jobs:
                        company_key = job["company_name"].lower().strip()
                        if company_key not in seen_companies:
                            seen_companies.add(company_key)
                            all_jobs.append(job)

                    if len(all_jobs) >= limit:
                        break
                else:
                    print(f"Serper API error for '{search_query}': {response.status_code}")

            except Exception as e:
                print(f"Serper API exception: {e}")

        return all_jobs[:limit]

    def _parse_search_results(self, result: Dict, min_salary: int, category: str) -> List[Dict]:
        """Parse search results from job sites"""
        jobs = []
        seen_companies = set()

        # First pass: prioritize high-quality ATS sources
        items = result.get("organic", [])
        # Sort by source quality (company portals first)
        items_sorted = sorted(items, key=lambda x: 0 if self._is_company_job_portal(x.get("link", "")) else 1)

        for item in items_sorted:
            title = item.get("title", "")
            link = item.get("link", "")
            snippet = item.get("snippet", "")

            # Skip generic portal pages
            if self._is_generic_portal_page(link):
                continue

            # Extract company name from title or URL
            company = self._extract_company_from_result(title, link, snippet)

            # Validate company name - skip if looks like job title or location
            if not company:
                continue
            company_lower = company.lower()
            invalid_names = [
                "karriere", "stepstone", "willhaben", "job", "jobs",
                "vollzeit", "teilzeit", "wien", "austria", "graz", "linz",
                "salzburg", "innsbruck", "home office", "remote",
                "personio", "linkedin", "indeed", "glassdoor", "xing",
                "work from home", "rocketreach", "salaryexpert", "hotelcareer",
                "efinancialcareers", "stellenangebote", "servicenow careers",
                "wearedevelopers", "heysuccess", "apply now", "graduate",
                "software engineer", "marketing manager", "sales manager",
                "developer", "engineer", "manager"  # Job titles mistaken as companies
            ]
            if any(inv in company_lower for inv in invalid_names):
                continue
            # Skip if company name is too short or looks like job descriptor
            if len(company) < 3 or company_lower in ["new", "top", "all", "mid"]:
                continue

            # Skip duplicates
            company_key = company_lower.strip()
            if company_key in seen_companies:
                continue

            # Skip blacklisted
            if self._is_blacklisted(company):
                continue

            # Skip recruiting agencies
            if self._is_recruiting_agency(company, title + " " + snippet):
                continue

            # Extract salary from snippet
            salary_info = self._extract_salary_from_text(snippet + " " + title)

            # Check salary threshold (if salary found)
            if salary_info["salary_num"] and salary_info["salary_num"] < min_salary:
                continue

            seen_companies.add(company_key)

            # Extract domain
            domain = self._extract_domain(company, link)

            jobs.append({
                "job_title": self._clean_job_title(title),
                "company_name": company,
                "company_name_clean": self._clean_company_name(company),
                "company_domain": domain,
                "location": "Austria",  # We're only searching Austria
                "salary_text": salary_info["salary_text"],
                "salary_num": salary_info["salary_num"],
                "job_url": link,
                "job_description": snippet,
                "posted_date": "",
                "source": self._get_source_from_url(link),
                "category": category,
                "is_direct_source": self._is_company_job_portal(link)
            })

        return jobs

    def _is_generic_portal_page(self, url: str) -> bool:
        """Check if URL is a generic portal page (not a specific job)"""
        generic_patterns = [
            r'karriere\.at/?$',
            r'karriere\.at/jobs/?$',
            r'karriere\.at/jobs/[a-z%-]+/?$',  # Category pages
            r'stepstone\.at/?$',
            r'stepstone\.at/jobs/?$',
            r'stepstone\.at/jobs/[a-z%-]+/?$',
            r'stepstone\.at/jobs/[a-z%-]+/in-',  # Location search pages
            r'willhaben\.at/jobs/?$',
            r'linkedin\.com/jobs/?$',
            r'jobs\.derstandard\.at',  # All DerStandard job search
            r'indeed\.com',
            r'indeed\.at',
            r'glassdoor\.',
            r'metajob\.',  # Job aggregator
            r'/search\?',
            r'/jobs\?q=',
            r'xing\.com/jobs',
            r'kununu\.',
            r'lohnanalyse\.',  # Salary analysis
            r'gehaltsvergleich\.',  # Salary comparison
            r'karriere\.at/gehalt',  # Salary pages
            r'gehalt\.de',
            r'payscale\.',
            r'reddit\.com',  # Reddit posts
            r'builtin\.com',  # BuiltIn job aggregator
            r'willhaben\.at/jobs/suche/',  # Willhaben search pages
            r'arbeitgeber\.stepstone',  # Stepstone employer pages
            r'personio\.com/(?:about|careers)',  # Personio's own career page
            r'finden\.at',  # Job aggregator
            r'stepstone\.de/jobs/',  # StepStone DE search pages
            r'linkedin\.com/posts/',  # LinkedIn posts (not job listings)
            r'linkedin\.com/in/',  # LinkedIn profiles
            r'jooble\.',  # Job aggregator
            r'rocketreach\.co',  # Company info site
            r'hotelcareer\.',  # Hotel job portal
            r'efinancialcareers\.',  # Finance job portal
            r'salaryexpert\.',  # Salary info
            r'wfhcareer|workfromhome|remoteco',  # Remote job aggregators
            r'servicenow\.com/careers',  # Generic career page
            r'wearedevelopers\.',  # Developer job portal
            r'heysuccess\.',  # Job portal
            r'applynow|apply-now',  # Generic apply pages
            r'venturecapital(?:careers|jobs)',  # VC job portal
        ]
        for pattern in generic_patterns:
            if re.search(pattern, url):
                return True
        return False

    def _is_company_job_portal(self, url: str) -> bool:
        """Check if URL is a direct company job portal (high quality)"""
        good_patterns = [
            r'\.jobs\.personio\.(?:com|de)',  # Personio ATS
            r'karriere\.at/firma/',  # Direct company page on karriere.at
            r'jobs\.lever\.co/',  # Lever ATS
            r'boards\.greenhouse\.io/',  # Greenhouse ATS
            r'jobs\.smartrecruiters\.com/',  # SmartRecruiters
            r'workable\.com/',  # Workable ATS
            r'/career[s]?/',  # Company career pages
            r'/job[s]?/',  # Company job pages
            r'/stelle[n]?/',  # German job pages
        ]
        for pattern in good_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False

    def _extract_company_from_result(self, title: str, url: str, snippet: str) -> Optional[str]:
        """Extract company name from search result"""
        # Skip generic job portal names
        generic_names = [
            "karriere.at", "stepstone", "willhaben", "jobs", "indeed",
            "glassdoor", "der standard", "derstandard", "xing", "linkedin",
            "kununu", "monster", "job", "stellenangebote"
        ]

        # Try karriere.at URL pattern: /firma/companyname/
        match = re.search(r'karriere\.at/firma/([^/]+)', url)
        if match:
            return match.group(1).replace('-', ' ').title()

        # Try stepstone URL pattern
        match = re.search(r'stepstone\.at/.*?/firma-([^/]+)', url)
        if match:
            return match.group(1).replace('-', ' ').title()

        # Try Personio URL pattern: company-name.jobs.personio.com
        match = re.search(r'([a-z0-9-]+)\.jobs\.personio\.(?:com|de)', url)
        if match:
            company = match.group(1).replace('-', ' ').title()
            if company.lower() not in generic_names:
                return company

        # Try company job portal: jobs.company.at or company.jobs.at
        match = re.search(r'(?:jobs\.)?([a-z0-9-]+)(?:\.jobs)?\.(?:at|com|de)/(?:job|career)', url)
        if match:
            company = match.group(1).replace('-', ' ').title()
            if company.lower() not in generic_names:
                return company

        # Try "at Company" pattern in title (common in Austrian job listings)
        match = re.search(r'(?:at|bei|@)\s+([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9\s&\.\-]+?)(?:\s*[-–|]|\s*\(|,|$)', title, re.IGNORECASE)
        if match:
            company = match.group(1).strip()
            if len(company) > 2 and company.lower() not in generic_names:
                return company

        # Try "| Company" or "- Company" pattern at end
        match = re.search(r'[-–|]\s*([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9\s&\.\-]+?)(?:\s*[-–|]|$)', title)
        if match:
            company = match.group(1).strip()
            if len(company) > 2 and company.lower() not in generic_names:
                return company

        # Try "Company Jobs" pattern in title
        match = re.search(r'^([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9\s&\.\-]+?)\s+(?:Jobs|Karriere|Career)', title)
        if match:
            company = match.group(1).strip()
            if len(company) > 2 and company.lower() not in generic_names:
                return company

        return None

    def _extract_salary_from_text(self, text: str) -> Dict:
        """Extract salary from text"""
        if not text:
            return {"salary_text": "", "salary_num": None}

        text_lower = text.lower().replace(".", "").replace(",", "")

        # Patterns for Austrian salary formats
        patterns = [
            (r'€\s*(\d{2,3})[\.\s]?(\d{3})', lambda m: int(m.group(1)) * 1000 + int(m.group(2))),
            (r'(\d{2,3})[\.\s]?(\d{3})\s*€', lambda m: int(m.group(1)) * 1000 + int(m.group(2))),
            (r'€\s*(\d{2,3})k', lambda m: int(m.group(1)) * 1000),
            (r'(\d{2,3})k\s*€', lambda m: int(m.group(1)) * 1000),
            (r'ab\s*€?\s*(\d{2,3})[\.\s]?(\d{3})', lambda m: int(m.group(1)) * 1000 + int(m.group(2))),
            (r'mindestgehalt[:\s]*€?\s*(\d{2,3})[\.\s]?(\d{3})', lambda m: int(m.group(1)) * 1000 + int(m.group(2))),
            (r'brutto[:\s]*€?\s*(\d{2,3})[\.\s]?(\d{3})', lambda m: int(m.group(1)) * 1000 + int(m.group(2))),
        ]

        for pattern, extractor in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    salary_num = extractor(match)
                    return {"salary_text": f"€{salary_num:,}", "salary_num": salary_num}
                except:
                    pass

        return {"salary_text": "", "salary_num": None}

    def _clean_job_title(self, title: str) -> str:
        """Clean job title"""
        # Remove site names
        title = re.sub(r'\s*[-–|]\s*(karriere\.at|stepstone|willhaben).*$', '', title, flags=re.IGNORECASE)
        # Remove gender markers
        title = re.sub(r'\s*\([mwfd/]+\)\s*', ' ', title, flags=re.IGNORECASE)
        return title.strip()

    def _get_source_from_url(self, url: str) -> str:
        """Get source name from URL"""
        if "karriere.at" in url:
            return "karriere.at"
        elif "stepstone.at" in url:
            return "stepstone.at"
        elif "willhaben.at" in url:
            return "willhaben.at"
        elif "linkedin.com" in url:
            return "LinkedIn"
        return "Google"

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

            # Skip jobs not in Austria
            job_location = job.get("location", "")
            if not self._is_austria_location(job_location):
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

    def search_with_apify(self,
                          queries: List[str],
                          location: str = "Austria",
                          max_items: int = 20,
                          timeout_minutes: int = 5) -> List[Dict]:
        """
        Search LinkedIn via Apify (takes longer but better data).
        Use for weekly batch runs, not real-time searches.
        """
        try:
            from apify_client import ApifyJobScraper
            apify = ApifyJobScraper()
            print(f"  Starting Apify LinkedIn scrape...")
            jobs = apify.scrape_and_wait(queries, location, max_items, timeout_minutes)
            return jobs
        except ImportError:
            print("  Apify client not available")
            return []
        except Exception as e:
            print(f"  Apify error: {e}")
            return []

    def search_all_sources(self,
                           queries: List[str],
                           location: str = "Austria",
                           min_salary: int = 65000,
                           use_apify: bool = False,
                           limit: int = 50) -> List[Dict]:
        """
        Search all available sources and combine results.

        Args:
            queries: Job search queries
            location: Location filter
            min_salary: Minimum salary
            use_apify: If True, also search LinkedIn via Apify (slower)
            limit: Maximum total results
        """
        all_jobs = []
        seen_companies = set()

        # Source 1: Google Search (Serper) - fast
        print("\n[Serper] Searching Google...")
        serper_jobs = self.search_multiple_categories(queries, location, min_salary, 10)
        for job in serper_jobs:
            company_key = job["company_name"].lower().strip()
            if company_key not in seen_companies:
                seen_companies.add(company_key)
                all_jobs.append(job)
        print(f"[Serper] Found {len(serper_jobs)} companies")

        # Source 2: LinkedIn (Apify) - slow but better data
        if use_apify and len(all_jobs) < limit:
            print("\n[Apify] Searching LinkedIn (this may take a few minutes)...")
            apify_jobs = self.search_with_apify(queries[:2], location, max_items=20)
            added = 0
            for job in apify_jobs:
                company_key = job["company_name"].lower().strip()
                if company_key not in seen_companies:
                    seen_companies.add(company_key)
                    all_jobs.append(job)
                    added += 1
            print(f"[Apify] Added {added} new companies")

        print(f"\n[Total] {len(all_jobs)} unique companies found")
        return all_jobs[:limit]


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
