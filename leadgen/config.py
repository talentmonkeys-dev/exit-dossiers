"""
TalentMonkeys Lead Generation - Configuration

IMPORTANT: Set your API keys as environment variables or in a .env file:
    export SERPER_API_KEY=your_key
    export APOLLO_API_KEY=your_key
    export GOOGLE_CLIENT_ID=your_client_id
    export GOOGLE_CLIENT_SECRET=your_client_secret
"""
import os
from datetime import date

# API Keys (from environment variables)
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY", "")

# Google OAuth (from environment variables)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Email Settings
APPROVAL_EMAIL = "Flavio@talentmonkeys.com"
SENDER_NAME = "Flavio Arteaga"
COMPANY_NAME = "talentmonkeys GmbH"
COMPANY_WEBSITE = "talentmonkeys.com"

# Google Sheet
SHEET_NAME = "TalentMonkeys Leads"

# Job Categories with rotation
CATEGORIES = [
    {
        "name": "IT",
        "queries": [
            "Software Developer Austria",
            "IT Manager Wien",
            "DevOps Engineer Österreich",
            "Data Engineer Austria",
            "Cloud Architect Wien",
            "Backend Developer Austria",
            "Frontend Developer Wien",
            "Full Stack Developer Österreich"
        ]
    },
    {
        "name": "Sales",
        "queries": [
            "Sales Manager Austria",
            "Account Manager Wien",
            "Business Development Manager Österreich",
            "Key Account Manager Austria",
            "Sales Director Wien",
            "Vertriebsleiter Österreich"
        ]
    },
    {
        "name": "Marketing",
        "queries": [
            "Marketing Manager Austria",
            "Digital Marketing Manager Wien",
            "Brand Manager Österreich",
            "Content Marketing Manager Austria",
            "Marketing Director Wien",
            "Head of Marketing Österreich"
        ]
    },
    {
        "name": "Finance",
        "queries": [
            "Finance Manager Austria",
            "Controller Wien",
            "CFO Österreich",
            "Financial Controller Austria",
            "Head of Finance Wien",
            "Accounting Manager Österreich"
        ]
    },
    {
        "name": "HR",
        "queries": [
            "HR Manager Austria",
            "People & Culture Manager Wien",
            "Talent Acquisition Manager Österreich",
            "HR Director Austria",
            "Head of People Wien"
        ]
    },
    {
        "name": "Engineering",
        "queries": [
            "Engineering Manager Austria",
            "Technical Lead Wien",
            "Project Engineer Österreich",
            "Mechanical Engineer Austria",
            "Electrical Engineer Wien"
        ]
    },
    {
        "name": "Operations",
        "queries": [
            "Operations Manager Austria",
            "Supply Chain Manager Wien",
            "Logistics Manager Österreich",
            "COO Austria",
            "Head of Operations Wien"
        ]
    }
]

# Blacklist - Companies to exclude
BLACKLIST = [
    "PSA", "Drees & Sommer", "LKW Walter", "Cyan Security", "Schmachtl",
    "Netconomy", "Lisec", "Babak Bacon", "Binderholz", "Post", "Lat Nitrogen",
    "Still", "ATSP", "KUKA", "Kotanyi", "Eam", "Rohndo Ganahl", "Informatics",
    "Rail Power Systems", "Doka", "Hobex", "Budimex", "ComeOn Group", "Toolsense",
    "Mubea", "XXXL", "Ortner", "Axians", "ARAG", "Planradar", "Haberkorn",
    "Xit Cross", "Würth Elektronik", "Filzwieser", "Tractive", "Bühler",
    "Salesianer", "Lasselsberger", "TaxPro", "Automation X", "Light for the world",
    "Ebcont", "Waterdrop", "Hoerbiger", "Verbund", "Plasmics", "Patchbox", "Feri",
    "Navax", "Uniqa", "Workist", "RBI", "Hahn Software", "Bawag", "Finmatics",
    "Meister", "KIK", "With Solid", "Tink", "UCS", "Mister Specks", "Bitpanda",
    "Speedinvest", "CTRL.QS", "Joris Ide", "Gebr. Heinemann", "Ubimet", "Gekko",
    "Steffl", "Waldquelle", "enspired", "Swat.io", "Consileon", "Glacier",
    "Treetop Medical", "Sclable", "Journi", "Jentis", "Generali", "Otago",
    "Anyline", "Celum", "Frequentis", "Herold", "IBM iX CH DE", "Imi",
    "Voestalpine", "Tourradar", "Mysugr", "Evolve Consulting", "Bet@Home",
    "Alpenland", "Nexxar", "NextMunich", "BWT", "ZKW", "Deepopinion", "Oatly",
    "Eversports", "HalloSonne", "Dynatrace", "Ikarus", "Storyblok", "IKEA", "Mjam"
]

# Recruiting agency keywords
RECRUITING_KEYWORDS = [
    "recruiting", "staffing", "personalberatung", "headhunter",
    "hr consulting", "personaldienstleister", "zeitarbeit",
    "personalvermittlung", "executive search", "talent acquisition agency",
    "randstad", "hays", "michael page", "robert half", "adecco", "manpower"
]

# Reference customers for email
REFERENCE_CUSTOMERS = [
    "Drees & Sommer", "Cyan Security", "Schmachtl", "Netconomy", "Lisec",
    "Binderholz", "Post", "Still", "KUKA", "Kotanyi", "Rail Power Systems",
    "Doka", "Hobex", "ComeOn Group", "Toolsense", "Mubea", "XXXL", "Ortner",
    "Axians", "ARAG", "Planradar", "Haberkorn", "Würth Elektronik", "Tractive",
    "Bühler", "Salesianer", "Lasselsberger", "Ebcont"
]

# HR Titles to search for
HR_TITLES = [
    "HR Business Partner",
    "Head of HR",
    "HR Director",
    "HR Manager",
    "People & Culture Manager",
    "Talent Acquisition Manager",
    "HR Lead",
    "Personalleiter",
    "Leiter Personal",
    "Chief People Officer",
    "VP HR",
    "VP People",
    "Head of People",
    "People Operations Manager"
]

# Limits
MAX_LEADS_PER_DAY = 50
MIN_EMPLOYEES = 50
CONTACT_COOLDOWN_DAYS = 30

# Business hours (Vienna timezone)
BUSINESS_HOURS_START = 8
BUSINESS_HOURS_END = 18


def get_todays_category():
    """Get today's category based on rotation"""
    start_date = date(2025, 1, 1)
    days_since_start = (date.today() - start_date).days
    category_index = days_since_start % len(CATEGORIES)
    return CATEGORIES[category_index], CATEGORIES[(category_index + 1) % len(CATEGORIES)]
