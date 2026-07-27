"""Filter logic.

Acceptance rule (applied in `passes`):

    job is technical / product-management / SWE / engineering
    AND NOT HR / admin / recruiter / legal / finance / office
    AND located in India (any state / union territory)
    AND posted in the last N days
    AND looks like an INTERNSHIP

Internships ONLY. Full-time roles (junior, new-grad, or otherwise) are no
longer sent. Product-management internships ARE accepted (product manager /
product management / product owner) — see PRODUCT_TOKENS in TECH_TOKENS.

All matching is case-insensitive and uses word boundaries so "intern" does
NOT match inside "internal" / "international", "lead" does NOT match inside
"leader-board", etc.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


# --- "Is this an internship?" --------------------------------------------
# Indian postings are English but use a few local labels of their own
# ("industrial trainee", "articleship", "summer intern", "GET" style
# programmes), on top of the multi-language tokens inherited from the
# EU alerter — harmless to keep, they simply never fire here.
DEFAULT_INTERN_TOKENS = [
    # Only actual *internship* words — new-grad / junior signals are
    # handled separately in label_for() so they're labelled correctly.
    "intern", "interns", "internship", "internships",
    "co-op", "coop",
    "working student", "werkstudent",
    "praktikum", "praktikant", "praktikantin",
    "stagiaire", "stagiaires",
    "stage",
    "stagiair", "stagiairs",
    "tirocinio", "tirocinante",
    "becario", "becaria", "practicas", "prácticas",
    "harjoittelija", "harjoittelu",
    "apprentice", "apprenticeship",
    # India-specific internship labels. Deliberately NOT included:
    # "graduate engineer trainee" / "GET" / "management trainee" — those are
    # full-time entry roles in India, and this alerter stays internship-only.
    "industrial trainee", "student trainee", "summer trainee",
]

# Things that contain an internship keyword but aren't internships.
INTERN_FALSE_POSITIVES = [
    "stage manager", "stage director", "stagehand",
    "internship program manager",
    "graduate program manager",
    "head of early career",
    "director of early career",
]


# --- "Is this a technical role we want?" ---------------------------------
# IC-engineering + product management. Designers / Solutions / Sales / TPM /
# Program-mgmt / Support / DevRel / Field roles are still vetoed below.
# (Product MANAGEMENT is now wanted — see the "Product management" block.)
TECH_TOKENS = [
    # Software / general engineering
    "engineer", "engineering", "developer", "software", "swe", "sde",
    "programmer", "fullstack", "full-stack", "full stack", "backend",
    "back-end", "back end", "frontend", "front-end", "front end",
    "mobile", "ios", "android", "platform", "infrastructure", "infra",
    "devops", "sre", "site reliability", "systems",
    # Data / ML / AI / Research
    "data", "ml", "machine learning", "mle", "ai ", "artificial intelligence",
    "deep learning", "research", "researcher", "scientist",
    "applied scientist", "research scientist", "research engineer",
    "computer vision", "nlp", "llm", "robotics", "perception", "autonomy",
    # Simulation / physics / graphics
    "simulation", "simulations", "simulator", "physics", "computational",
    # Hardware / firmware / quant / chips
    "hardware", "firmware", "asic", "fpga", "embedded", "chip",
    "silicon", "rtl", "verification engineer", "physical design",
    "compiler", "kernel",
    # Security
    "security", "cyber", "appsec", "secops", "vulnerability", "penetration",
    "red team", "blue team",
    # Cloud / data engineering
    "cloud", "kubernetes", "platform engineer", "data engineer",
    "performance engineer", "distributed",
    # Game / graphics
    "gameplay", "graphics", "rendering", "engine programmer",
    "game programmer", "game developer", "shader",
    # Quant
    "quant", "quantitative",
    # Forward deployed engineer (Palantir-style) — actually IC engineering.
    "forward deployed engineer",
    # Product management (user wants these across ALL boards, incl. prestige
    # big-tech). Multi-word tokens => substring match, so "Product Management
    # Intern", "Associate Product Manager", "Product Owner" all match.
    # NOTE: bare "product" is intentionally NOT listed (too broad — would
    # catch "product marketing", "production", etc.).
    "product manager", "product management", "product owner",
    "associate product manager", "product management intern",
]


# --- "Is this HR / admin / not-our-thing?" -------------------------------
NON_TECH_VETO_TOKENS = [
    # Recruiting / HR / People
    "recruiter", "recruiting", "talent acquisition", "talent partner",
    "talent sourcer", "sourcer", "people operations", "people ops",
    "people partner", "hr ", "human resources", "hrbp", "hr business partner",
    "chro", "compensation analyst", "benefits", "payroll",
    "diversity", "dei ", "learning & development", "l&d",
    # Admin / office
    "executive assistant", "office manager", "office coordinator",
    "receptionist", "administrative", "admin assistant", "facilities",
    "workplace experience", "workplace coordinator", "office services",
    # Legal / compliance / risk
    "legal", "paralegal", "compliance", "counsel", "attorney",
    "privacy counsel", "regulatory affairs", "ethics",
    # Finance / accounting / procurement
    "finance", "accountant", "accounting", "tax ", "treasury", "audit",
    "auditor", "fp&a", "controller", "procurement", "purchasing",
    "billing", "collections", "ap analyst", "ar analyst",
    "financial analyst",
    # Sales / marketing / GTM / customer success / partnerships
    "sales", "sdr", "bdr", "account executive", "account manager",
    "business development", "partnerships", "partner manager",
    "channel manager", "customer success", "customer support",
    "customer experience", "support engineer trainee", "support specialist",
    "marketing", "growth marketer", "brand", "communications", "pr ",
    "public relations", "content marketing", "social media",
    "community manager",
    # Operations / supply chain / strategy (non-tech ops)
    "supply chain", "logistics", "warehouse", "operations analyst",
    "operations manager", "strategy & operations", "biz ops",
    "business operations", "strategic finance",
    # Misc
    "translator", "interpreter", "trainer", "teacher", "tutor",
    "writer", "editor", "journalist", "copywriter",
    "videographer", "photographer",
    "real estate", "investor relations",
    "phlebotomist", "technician, lab", "lab technician",
    # --- Sales-engineer / pre-sales / customer-facing "engineer" ---
    "solutions engineer", "solution engineer", "solutions architect",
    "solution architect", "account solution", "pre-sales", "presales",
    "sales engineer", "customer engineer",
    "deployment strategist",
    # --- Field / on-site / maintenance "engineer" ---
    "field service engineer", "field engineer",
    "maintenance engineering technician", "maintenance engineering manager",
    "reliability maintenance engineering",
    # --- Support / services "engineer" ---
    "technical services engineer", "services engineer",
    "support engineer",
    # --- DevRel / community / advocacy ---
    "developer advocate", "developer relations", "devrel",
    "technical evangelist",
    # --- Design / UX ---
    "experience designer", "product designer", "ux designer",
    "ui designer", "ui/ux", "ux/ui", "visual designer", "brand designer",
    "graphic designer", "designer, ", "designer -", "designer:",
    # --- Analyst (not engineer) ---
    "data analyst", "business analyst", "intelligence analyst",
    "competitor intelligence", "information security analyst",
    "security analyst", "threat analyst",
    # --- Program management (product MANAGEMENT now allowed via TECH_TOKENS) ---
    "technical program manager", "program manager", " tpm ",
    "platform owner",
    # --- Engineering management ---
    "engineering manager", "manager, engineering",
    "manager, site reliability", "manager, software",
    "manager, machine learning", "manager, data",
    "manager, security", "manager, infrastructure", "manager, platform",
    "head of engineering", "vp of engineering", "vp engineering",
    "director of engineering",
    # --- Physical / data-center / ops roles that aren't SWE ---
    "data center deployment", "data center technician", "cable install",
    "loss prevention", "physical security", "safety specialist",
    "workplace incident", "incident management",
    "manufacturing engineer", "data management specialist",
    "operations technician", "deployment specialist",
    "investigator",
    # --- German-language field/trade roles (Bosch etc.) ---
    "sicherheitstechniker", "elektroniker",
    # --- Customer-facing / consulting ---
    "professional services", "business consulting",
]


# --- Senior / management labels (used to gate full-time roles) -----------
SENIOR_TOKENS = [
    "senior", "sr ", "sr.", "sr,",
    "staff", "principal", "distinguished",
    "lead", "leader",
    "tech lead", "engineering lead", "team lead",
    "architect",
    "manager", "head of", "director", "directress",
    "vp ", "vp,", "v.p.", "vice president",
    "chief", "cto", "cio", "ceo", "cpo", "cfo", "chro", "cso",
    "ii", "iii", "iv",
    "expert", "advisor",
]


# --- India location ------------------------------------------------------
# Every state and union territory. Word-boundary matched, so "Goa" will not
# fire inside "Goandhra" and "India" will not fire inside "Indiana".
INDIA_STATES = [
    "India", "Bharat",
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Orissa", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Tamilnadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "Uttaranchal",
    "West Bengal",
    # Union territories
    "Andaman and Nicobar", "Chandigarh", "Dadra and Nagar Haveli",
    "Daman and Diu", "Delhi", "Jammu and Kashmir", "Ladakh",
    "Lakshadweep", "Puducherry", "Pondicherry",
    # Note: "Punjab" also exists in Pakistan — NON_INDIA_VETO_COUNTRIES
    # below kills "Lahore, Punjab, Pakistan".
]

INDIA_CITIES = [
    # --- Bengaluru ---
    "Bengaluru", "Bangalore", "Whitefield", "Electronic City",
    "Koramangala", "Marathahalli", "Bellandur", "Indiranagar",
    "HSR Layout", "Hebbal", "Yelahanka", "Jayanagar", "Bommanahalli",
    "Devanahalli", "Sarjapur", "Manyata", "Outer Ring Road",
    # --- Hyderabad ---
    "Hyderabad", "Secunderabad", "Gachibowli", "HITEC City", "Hitech City",
    "Madhapur", "Kondapur", "Kukatpally", "Nanakramguda", "Shamshabad",
    # --- Delhi NCR ---
    "New Delhi", "Gurgaon", "Gurugram", "Noida", "Greater Noida",
    "Ghaziabad", "Faridabad", "NCR", "Cyber City", "Cyber Hub",
    "Sohna Road", "Dwarka", "Okhla", "Manesar",
    # --- Mumbai ---
    "Mumbai", "Bombay", "Navi Mumbai", "Thane", "Powai", "Andheri",
    "Goregaon", "Bandra", "Malad", "Vikhroli", "Lower Parel",
    "Worli", "Airoli", "Vashi", "Kalyan", "Dombivli", "Mira Road",
    # --- Pune ---
    "Pune", "Hinjewadi", "Hinjawadi", "Pimpri", "Chinchwad", "Kharadi",
    "Magarpatta", "Baner", "Viman Nagar", "Wakad", "Hadapsar", "Talegaon",
    # --- Chennai ---
    "Chennai", "Madras", "Sholinganallur", "Guindy", "Taramani",
    "Siruseri", "Perungudi", "Ambattur", "Tambaram", "Chengalpattu",
    # --- Kolkata ---
    "Kolkata", "Calcutta", "Howrah", "Rajarhat", "New Town", "Sector V",
    "Durgapur", "Asansol", "Siliguri", "Kharagpur",
    # --- West / Gujarat ---
    "Ahmedabad", "Gandhinagar", "GIFT City", "Surat", "Vadodara",
    "Baroda", "Rajkot", "Bhavnagar", "Jamnagar", "Anand", "Bharuch",
    # --- Rajasthan ---
    "Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner",
    # --- Uttar Pradesh / Uttarakhand ---
    "Lucknow", "Kanpur", "Varanasi", "Banaras", "Prayagraj", "Allahabad",
    "Agra", "Meerut", "Bareilly", "Aligarh", "Moradabad", "Gorakhpur",
    "Jhansi", "Mathura", "Dehradun", "Haridwar", "Rishikesh", "Roorkee",
    # --- Punjab / Haryana / HP / J&K ---
    "Mohali", "Panchkula", "Ludhiana", "Amritsar", "Jalandhar", "Patiala",
    "Zirakpur", "Shimla", "Dharamshala", "Srinagar", "Jammu", "Karnal",
    "Hisar", "Ambala", "Sonipat", "Rohtak", "Panipat",
    # --- Madhya Pradesh / Chhattisgarh ---
    "Indore", "Bhopal", "Jabalpur", "Gwalior", "Ujjain", "Sagar",
    "Raipur", "Bhilai", "Bilaspur", "Durg",
    # --- Odisha / Jharkhand / Bihar ---
    "Bhubaneswar", "Cuttack", "Rourkela", "Sambalpur", "Puri",
    "Ranchi", "Jamshedpur", "Dhanbad", "Bokaro",
    "Patna", "Gaya", "Muzaffarpur", "Bhagalpur",
    # --- North-east ---
    "Guwahati", "Dibrugarh", "Silchar", "Jorhat", "Tezpur",
    "Shillong", "Imphal", "Agartala", "Aizawl", "Kohima", "Itanagar",
    "Gangtok",
    # --- Kerala ---
    "Kochi", "Cochin", "Ernakulam", "Infopark", "Technopark",
    "Thiruvananthapuram", "Trivandrum", "Kozhikode", "Calicut",
    "Thrissur", "Kannur", "Kollam", "Alappuzha", "Kottayam", "Palakkad",
    # --- Tamil Nadu (non-Chennai) ---
    "Coimbatore", "Madurai", "Tiruchirappalli", "Trichy", "Salem",
    "Tirunelveli", "Hosur", "Vellore", "Erode", "Tirupur", "Thoothukudi",
    # --- Andhra / Telangana (non-Hyderabad) ---
    "Visakhapatnam", "Vizag", "Vijayawada", "Guntur", "Tirupati",
    "Amaravati", "Nellore", "Kakinada", "Rajahmundry", "Warangal",
    "Karimnagar", "Nizamabad",
    # --- Karnataka (non-Bengaluru) ---
    "Mysore", "Mysuru", "Mangalore", "Mangaluru", "Hubli", "Hubballi",
    "Belgaum", "Belagavi", "Davangere", "Shimoga", "Udupi", "Manipal",
    # --- Maharashtra (non-Mumbai/Pune) ---
    "Nagpur", "Nashik", "Nasik", "Aurangabad", "Chhatrapati Sambhajinagar",
    "Kolhapur", "Solapur", "Amravati", "Satara", "Ratnagiri",
    # --- Goa ---
    "Panaji", "Panjim", "Margao", "Verna", "Porvorim",
]

# Umbrella / remote phrasings that mean "somewhere in India".
INDIA_REMOTE_TOKENS = [
    "Remote - India", "Remote, India", "India Remote", "Remote (India)",
    "Remote-India", "India - Remote", "Pan India", "Pan-India",
    "All India", "Anywhere in India", "Remote India",
    "APAC - India", "IN Remote",
]

# Countries whose city names collide with Indian ones ("Hyderabad, Sindh",
# "Salem, OR", "Lahore, Punjab"). If one of these is named and the string
# never says "India", the posting is rejected.
NON_INDIA_VETO_COUNTRIES = [
    "Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Bhutan", "Myanmar",
    "United States", "USA", "U.S.", "U.S.A.", "Canada", "Mexico",
    "United Kingdom", "Great Britain", "Ireland", "Germany", "France",
    "Netherlands", "Spain", "Italy", "Poland", "Portugal", "Sweden",
    "Switzerland", "Australia", "New Zealand", "Singapore", "Malaysia",
    "Indonesia", "Philippines", "Thailand", "Vietnam", "Japan", "China",
    "Korea", "Israel", "UAE", "United Arab Emirates", "Saudi Arabia",
    "Qatar", "Egypt", "Nigeria", "South Africa", "Brazil", "Argentina",
]


# --- helpers --------------------------------------------------------------
def _word_match(text: str, token: str) -> bool:
    """Case-insensitive whole-word(s) match. Handles multi-word tokens too."""
    if " " in token or "-" in token:
        return token.lower() in text.lower()
    return re.search(rf"(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])",
                     text, flags=re.IGNORECASE) is not None


def _any_word_match(text: str, tokens) -> bool:
    return any(_word_match(text, tok) for tok in tokens)


# --- predicates -----------------------------------------------------------
def is_internship(title: str, *, intern_tokens: list[str] | None = None) -> bool:
    tokens = intern_tokens or DEFAULT_INTERN_TOKENS
    low = title.lower()
    if any(fp in low for fp in INTERN_FALSE_POSITIVES):
        return False
    return _any_word_match(title, tokens)


def is_senior(title: str) -> bool:
    return _any_word_match(title, SENIOR_TOKENS)


def is_non_tech(title: str, dept: str = "") -> bool:
    blob = f"{title} || {dept}"
    return _any_word_match(blob, NON_TECH_VETO_TOKENS)


def is_tech(title: str, dept: str = "") -> bool:
    blob = f"{title} || {dept}"
    return _any_word_match(blob, TECH_TOKENS)


def _word_in(text: str, token: str) -> bool:
    return re.search(rf"(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])",
                     text, flags=re.IGNORECASE) is not None


# Metro buckets used by the digest's per-city sections.
BENGALURU_TOKENS = [
    "Bengaluru", "Bangalore", "Whitefield", "Electronic City",
    "Koramangala", "Marathahalli", "Bellandur", "Indiranagar",
    "HSR Layout", "Hebbal", "Yelahanka", "Jayanagar", "Bommanahalli",
    "Devanahalli", "Sarjapur", "Manyata",
]

HYDERABAD_TOKENS = [
    "Hyderabad", "Secunderabad", "Gachibowli", "HITEC City", "Hitech City",
    "Madhapur", "Kondapur", "Kukatpally", "Nanakramguda", "Shamshabad",
]

NCR_TOKENS = [
    "New Delhi", "Delhi", "Gurgaon", "Gurugram", "Noida", "Greater Noida",
    "Ghaziabad", "Faridabad", "NCR", "Cyber City", "Cyber Hub",
    "Sohna Road", "Dwarka", "Okhla", "Manesar",
]

MUMBAI_TOKENS = [
    "Mumbai", "Bombay", "Navi Mumbai", "Thane", "Powai", "Andheri",
    "Goregaon", "Bandra", "Malad", "Vikhroli", "Lower Parel", "Worli",
    "Airoli", "Vashi",
]

PUNE_TOKENS = [
    "Pune", "Hinjewadi", "Hinjawadi", "Pimpri", "Chinchwad", "Kharadi",
    "Magarpatta", "Baner", "Viman Nagar", "Wakad", "Hadapsar",
]

CHENNAI_TOKENS = [
    "Chennai", "Madras", "Sholinganallur", "Guindy", "Taramani",
    "Siruseri", "Perungudi", "Ambattur", "Tambaram",
]


def is_bengaluru_location(location: str) -> bool:
    return bool(location) and _any_word_match(location, BENGALURU_TOKENS)


def is_hyderabad_location(location: str) -> bool:
    return bool(location) and _any_word_match(location, HYDERABAD_TOKENS)


def is_ncr_location(location: str) -> bool:
    return bool(location) and _any_word_match(location, NCR_TOKENS)


def is_mumbai_location(location: str) -> bool:
    return bool(location) and _any_word_match(location, MUMBAI_TOKENS)


def is_pune_location(location: str) -> bool:
    return bool(location) and _any_word_match(location, PUNE_TOKENS)


def is_chennai_location(location: str) -> bool:
    return bool(location) and _any_word_match(location, CHENNAI_TOKENS)


def is_india_location(location: str, *,
                      extra_tokens: list[str] | None = None) -> bool:
    """True if the location string clearly points anywhere inside India.

    Two-step: (1) find an India hint — a state, UT, city, remote phrasing,
    the ISO-3 code IND, or a user-supplied extra token; (2) if the hint came
    from a name that also exists abroad, drop the posting when a foreign
    country is named and "India" itself is not.

    The bare ISO-2 code "IN" is deliberately NOT accepted: it collides with
    the English word "in" and with Indiana.
    """
    if not location:
        return False
    loc = location.strip()

    has_hint = False
    for token in INDIA_STATES + INDIA_CITIES + INDIA_REMOTE_TOKENS:
        if _word_in(loc, token):
            has_hint = True
            break
    if not has_hint and re.search(r"(?<![A-Za-z0-9])IND(?![A-Za-z0-9])", loc):
        has_hint = True
    if not has_hint and extra_tokens:
        low = loc.lower()
        for token in extra_tokens:
            if token and token.lower() in low:
                has_hint = True
                break

    if not has_hint:
        return False

    # An explicit "India" / "Bharat" beats any collision.
    if _word_in(loc, "India") or _word_in(loc, "Bharat"):
        return True

    # City-only hint: reject if some other country is named alongside it
    # ("Hyderabad, Sindh, Pakistan", "Salem, OR, United States").
    for country in NON_INDIA_VETO_COUNTRIES:
        if _word_in(loc, country):
            return False
    return True


def posted_within(job: dict, days: int) -> bool:
    """True if the job was posted within `days` days of now (or has no
    timestamp at all — we don't want to silently drop boards that omit dates)."""
    posted_at: datetime | None = job.get("posted_at")
    if posted_at is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return posted_at >= cutoff


# --- final acceptance gate ------------------------------------------------
def passes(
    job: dict,
    *,
    intern_tokens: list[str] | None = None,
    india_extra_tokens: list[str] | None = None,
    max_age_days: int = 3,
) -> bool:
    title = job.get("title", "")
    dept = job.get("department", "") or ""
    location = job.get("location", "")

    # Location gate. India only — no exceptions for any company.
    if not is_india_location(location, extra_tokens=india_extra_tokens):
        return False

    # Freshness gate
    if not posted_within(job, max_age_days):
        return False

    # HR / admin / legal / finance veto first — wins over everything.
    if is_non_tech(title, dept):
        return False

    # Must look technical-ish (engineering / data / ... / product management).
    if not is_tech(title, dept):
        return False

    # Internships ONLY. Full-time roles (junior, new-grad, or senior) are
    # dropped regardless of company. Any seniority of internship is fine.
    return is_internship(title, intern_tokens=intern_tokens)


_ROLE_NOUN = r"engineer|developer|programmer|designer|scientist|analyst|researcher|architect|sde|swe"

_JR_LEVEL_PATTERNS = [
    # "<role> I" / "<role> II"  (Roman I and II only — III/IV are mid+)
    re.compile(rf"\b({_ROLE_NOUN})\s+(i{{1,2}})\b", re.I),
    # "<role> 1" / "<role> 2" / "<role> L1" / "<role>, level 2"
    re.compile(rf"\b({_ROLE_NOUN})\s*[,]?\s*(level\s*|l\s*)?(1|2)\b(?!\d)", re.I),
    # "L1 <role>" / "L2 <role>"
    re.compile(rf"\bL\s?(1|2)\b\s+({_ROLE_NOUN})", re.I),
]


def label_for(job: dict) -> str:
    """Short label to show in the digest (Intern / Grad / Junior / Regular)."""
    title = job.get("title", "")
    low = title.lower()
    if is_internship(title):
        return "Internship"
    # New-grad / early-career / graduate-style language
    if any(k in low for k in ("new grad", "new graduate", "graduate program",
                              "graduate programme", "grad program",
                              "early career", "early-career",
                              "university grad", "campus hire")):
        return "New grad"
    # Standalone "graduate" word (e.g. "Graduate Software Engineer")
    if _word_match(title, "graduate"):
        return "New grad"
    # Junior-flavored tokens
    if any(_word_match(title, k) for k in
           ("junior", "jr", "entry-level", "entry level", "associate",
            "trainee", "traineeship")):
        return "Junior"
    # Level indicators: SDE 1 / Engineer I / L1 / L2 etc.
    for rx in _JR_LEVEL_PATTERNS:
        if rx.search(title):
            return "Junior"
    return "Regular"
