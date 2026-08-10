"""Filter logic — retargeted for Subodh's search.

Acceptance rule (applied in `passes`):

    role is one of Subodh's tracks:
        quant / trading  OR  software / tech  OR  IB / finance  OR  consulting
    AND NOT HR / admin / recruiter / legal / sales / marketing / support / design
    AND located in a TARGET region
        (Sweden + Nordics, Netherlands, UK/London, Switzerland,
         major EU financial/tech hubs, or EU-remote)
    AND posted in the last N days
    AND looks like an INTERNSHIP / off-cycle / spring / summer-analyst role

Internships & student programmes ONLY. Full-time roles (junior, new-grad,
senior) are dropped. "Off-cycle", "spring week/insight", "summer analyst",
"working student" and "industrial placement" ARE accepted — the finance and
consulting cycles use those labels instead of the word "intern".

All matching is case-insensitive and word-boundary based, so "intern" does
NOT fire inside "internal"/"international", "lead" not inside "leaderboard".
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


# --- Early-career / insight / student-programme synonyms -----------------
# Banks, consultancies and big tech all brand their student-facing schemes
# differently. Catch every synonym so none slip through — these count both as
# "this is a student programme" (internship gate) and "this is a wanted track"
# (role gate), because an insight/off-cycle/spring/early-career scheme is
# inherently something Subodh wants regardless of the function named.
EARLY_CAREER_TOKENS = [
    # Insight events
    "insight", "insight programme", "insight program", "insight day",
    "insight week", "insight evening", "insight series", "insight event",
    # Spring / off-cycle / analyst cycles
    "spring week", "spring insight", "spring programme", "spring program",
    "off-cycle", "off cycle", "offcycle",
    "summer analyst", "summer associate", "summer intern",
    # Early-career / talent branding
    "early career", "early careers", "early talent", "emerging talent",
    "future talent", "next generation", "nextgen", "rising talent",
    # Student / campus / university branding
    "student programme", "student program", "student opportunities",
    "campus", "on-campus", "university programme", "university program",
    "undergraduate programme", "undergraduate program",
    # Discovery / explore / immersion style names
    "discovery programme", "discovery program", "discovery day",
    "explore programme", "explore program", "exploration programme",
    "immersion programme", "immersion program", "experience programme",
    # Graduate / trainee schemes (final-year entry — Subodh wants these too)
    "graduate programme", "graduate program", "graduate scheme", "grad scheme",
    "graduate analyst", "trainee programme", "trainee program",
    # Scholarships / fellowships / cohort names
    "scholarship programme", "scholarship program", "scholars programme",
    "fellowship", "academy", "bootcamp",
    # Diversity-led student events (NOT the vetoed HR "diversity" — these are
    # student pipelines) + year targeting
    "women in", "penultimate", "first-year", "first year", "sophomore",
    # Branded prop/quant early-career programmes & events (Jane Street, IMC,
    # SIG, G-Research, Optiver, etc.). "extern" is word-boundary matched so it
    # won't fire inside "external".
    "launchpad", "extern", "externship", "fttp", "in focus", "visit day",
    "talent community", "networking event", "estimathon", "hackathon",
    "trading challenge", "trading program", "trading programme",
    "trading academy", "quant challenge", "coding challenge", "open day",
    "discovery day", "discovery program", "discovery programme",
]

# --- "Is this an internship / student programme?" ------------------------
DEFAULT_INTERN_TOKENS = EARLY_CAREER_TOKENS + [
    # Core internship words
    "intern", "interns", "internship", "internships",
    "co-op", "coop",
    "working student", "werkstudent",
    "praktik", "praktikum", "praktikant", "praktikantin", "praktikplats",
    "stagiaire", "stagiaires", "stage", "stagiair", "stagiairs",
    "tirocinio", "tirocinante",
    "becario", "becaria", "practicas", "prácticas",
    "harjoittelija", "harjoittelu",
    "apprentice", "apprenticeship",
    # Finance / consulting cycle labels (these are how banks & MBB name their
    # student programmes — treat them as internships).
    "off-cycle", "off cycle", "offcycle",
    "spring week", "spring insight", "spring programme", "spring program",
    "insight programme", "insight program", "insight day", "insight week",
    "summer analyst", "summer internship", "summer intern",
    "industrial placement", "placement student", "student placement",
    "sandwich placement", "penultimate",
    "trainee", "traineeship",   # Nordic/EU firms use "trainee" for student roles
]

# Things that contain an internship keyword but aren't internships.
INTERN_FALSE_POSITIVES = [
    "stage manager", "stage director", "stagehand",
    "internship program manager", "internship programme manager",
    "graduate program manager", "graduate programme manager",
    "head of early career", "director of early career",
    "trainee manager", "trainee program manager",
]


# --- "Is this a role Subodh wants?" --------------------------------------
# Four tracks. A posting is WANTED if it matches any track and isn't vetoed.

# 1) Software / tech / data / ML — IC engineering.
TECH_TOKENS = [
    "engineer", "engineering", "developer", "software", "swe", "sde",
    "programmer", "fullstack", "full-stack", "full stack", "backend",
    "back-end", "back end", "frontend", "front-end", "front end",
    "mobile", "ios", "android", "platform", "infrastructure", "infra",
    "devops", "sre", "site reliability", "systems",
    "data", "ml", "machine learning", "mle", "ai ", "artificial intelligence",
    "deep learning", "research engineer", "research scientist", "scientist",
    "computer vision", "nlp", "llm", "robotics", "perception",
    "simulation", "computational", "hardware", "firmware", "fpga", "embedded",
    "compiler", "kernel", "security", "cyber", "appsec", "cloud",
    "kubernetes", "data engineer", "distributed", "performance engineer",
    "forward deployed engineer",
    # Product management (Subodh is open to APM/PM student roles)
    "product manager", "product management", "product owner",
    "associate product manager", "product management intern",
]

# 2) Quant / trading.
QUANT_TOKENS = [
    "quant", "quantitative", "quantitative research", "quantitative trader",
    "quantitative developer", "quant developer", "quant researcher",
    "quant trading", "quant research", "systematic", "algorithmic",
    "algo trading", "trader", "trading", "market maker", "market making",
    "market-making", "execution", "low latency", "low-latency",
]

# 3) Investment banking / finance / markets.
FINANCE_TOKENS = [
    "investment banking", "investment bank", "ibd", "m&a", "mergers",
    "corporate finance", "global markets", "sales & trading",
    "sales and trading", "equity research", "fixed income",
    "private equity", "asset management", "wealth management",
    "capital markets", "leveraged finance", "restructuring",
    "investment analyst", "financial engineering", "structured finance",
    "sustainable finance", "credit", "coverage", "advisory",
    "portfolio", "risk", "actuar",
]

# 4) Consulting / strategy.
CONSULTING_TOKENS = [
    "consultant", "consulting", "business analyst", "associate consultant",
    "strategy consultant", "management consult", "strategy&", "strategy &",
    "generalist consultant",
]

# 5) Programme labels that are inherently a wanted student/early-career
# scheme even when the title names no function ("Spring Week 2027",
# "Insight Day", "Early Careers Programme", "Graduate Scheme").
PROGRAMME_TOKENS = EARLY_CAREER_TOKENS

WANTED_TOKEN_GROUPS = [TECH_TOKENS, QUANT_TOKENS, FINANCE_TOKENS,
                       CONSULTING_TOKENS, PROGRAMME_TOKENS]


# --- "Is this something to veto?" ----------------------------------------
# NOTE: finance / consulting / business-analyst / BD are DELIBERATELY not
# vetoed here — they're wanted tracks. Only clearly off-target functions.
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
    # Legal / compliance-only
    "legal", "paralegal", "counsel", "attorney",
    "privacy counsel", "regulatory affairs", "ethics officer",
    # Accounting / procurement (back-office, not front-office finance)
    "accountant", "accounting", "tax analyst", "tax associate", "treasury ops",
    "auditor", "audit associate", "controller", "procurement", "purchasing",
    "billing", "collections", "accounts payable", "accounts receivable",
    # Pure sales / marketing / GTM / CS / support
    "sdr", "bdr", "account executive", "account manager",
    "partner manager", "channel manager", "customer success",
    "customer support", "customer service", "customer experience",
    "support specialist", "support engineer",
    "marketing", "growth marketer", "brand manager", "communications",
    "public relations", "content marketing", "social media",
    "community manager",
    # Non-tech ops / supply chain / logistics
    "supply chain", "logistics", "warehouse", "operations analyst",
    "operations manager", "biz ops",
    # Misc off-target
    "translator", "interpreter", "trainer", "teacher", "tutor",
    "writer", "editor", "journalist", "copywriter",
    "videographer", "photographer", "investor relations",
    "phlebotomist", "lab technician",
    # Sales-engineer / pre-sales / customer-facing "engineer"
    "solutions engineer", "solution engineer", "solutions architect",
    "solution architect", "pre-sales", "presales",
    "sales engineer", "customer engineer", "deployment strategist",
    # Field / on-site / maintenance "engineer"
    "field service engineer", "field engineer",
    "maintenance engineering", "reliability maintenance",
    # Support / services "engineer"
    "technical services engineer", "services engineer",
    # DevRel / advocacy
    "developer advocate", "developer relations", "devrel",
    "technical evangelist",
    # Design / UX
    "experience designer", "product designer", "ux designer",
    "ui designer", "ui/ux", "ux/ui", "visual designer", "brand designer",
    "graphic designer", "designer, ", "designer -", "designer:",
    # Program / engineering management
    "technical program manager", "program manager", " tpm ",
    "engineering manager", "manager, engineering",
    "head of engineering", "vp of engineering", "vp engineering",
    "director of engineering",
    # Physical / data-center / trade roles
    "data center technician", "cable install", "loss prevention",
    "physical security", "safety specialist", "manufacturing engineer",
    "operations technician", "sicherheitstechniker", "elektroniker",
]


# --- Senior / management labels (gate out full-time roles) ---------------
SENIOR_TOKENS = [
    "senior", "sr ", "sr.", "sr,",
    "staff", "principal", "distinguished",
    "lead", "leader", "tech lead", "engineering lead", "team lead",
    "manager", "head of", "director", "directress",
    "vp ", "vp,", "v.p.", "vice president",
    "chief", "cto", "cio", "ceo", "cpo", "cfo", "chro", "cso",
    "ii", "iii", "iv", "expert",
]


# --- Target locations ----------------------------------------------------
# Countries Subodh can work in with low/no friction (EU free movement +
# UK + Switzerland) plus the specific cities that host quant/finance/tech.
TARGET_COUNTRIES = [
    "Sweden", "Sverige",
    "Norway", "Norge",
    "Denmark", "Danmark",
    "Finland", "Suomi",
    "Iceland",
    "Netherlands", "Nederland", "The Netherlands", "Holland",
    "United Kingdom", "UK", "U.K.", "England", "Britain", "Great Britain",
    "Switzerland", "Schweiz", "Suisse", "Svizzera",
    "Ireland", "Éire",
    "Germany", "Deutschland",
    "France",
    "Belgium", "België", "Belgique",
    "Luxembourg",
    "Italy", "Italia",
    "Spain", "España",
    "Poland", "Polska",
    "Austria", "Österreich",
    "Portugal",
    "Estonia", "Lithuania", "Latvia",
]

TARGET_CITIES = [
    # Sweden
    "Stockholm", "Göteborg", "Gothenburg", "Malmö", "Malmo", "Lund",
    "Uppsala", "Solna", "Kista", "Sundbyberg",
    # Nordics
    "Oslo", "Bergen", "Trondheim",
    "Copenhagen", "København", "Kobenhavn", "Aarhus",
    "Helsinki", "Espoo", "Tampere",
    "Reykjavik", "Reykjavík",
    # Netherlands
    "Amsterdam", "Rotterdam", "The Hague", "Den Haag", "Eindhoven",
    "Utrecht", "Delft",
    # UK
    "London", "Cambridge", "Oxford", "Edinburgh", "Manchester",
    # Switzerland
    "Zurich", "Zürich", "Geneva", "Genève", "Zug", "Basel", "Lausanne",
    # Ireland
    "Dublin",
    # Germany
    "Frankfurt", "Munich", "München", "Berlin", "Hamburg", "Düsseldorf",
    "Stuttgart",
    # France / Benelux / other EU financial + tech hubs
    "Paris", "Brussels", "Bruxelles", "Luxembourg City",
    "Milan", "Milano", "Madrid", "Barcelona", "Warsaw", "Warszawa",
    "Vienna", "Wien", "Lisbon", "Lisboa",
    "Tallinn", "Vilnius", "Riga",
]

# Remote phrasings that mean "somewhere Subodh could work".
TARGET_REMOTE_TOKENS = [
    "Remote - EU", "Remote, EU", "Remote (EU)", "EU Remote", "EU-Remote",
    "Remote - Europe", "Remote, Europe", "Remote (Europe)", "Europe Remote",
    "Remote Europe", "EMEA Remote", "Remote - EMEA", "Remote EMEA",
    "Remote - Sweden", "Remote Sweden", "Remote, Sweden",
    "Remote - Netherlands", "Remote - UK", "Remote UK",
    "Nordics", "Nordic", "Scandinavia",
]

# Regions that are clearly NOT for Subodh. If one of these is named and no
# target country/city is, the posting is rejected. Also kills collisions
# (a "London, Ontario" or "Paris, TX" that names Canada / United States).
NON_TARGET_VETO_COUNTRIES = [
    "United States", "USA", "U.S.", "U.S.A.", "US-", "Canada", "Mexico",
    "India", "Bharat", "Pakistan", "Bangladesh", "Sri Lanka",
    "Singapore", "Malaysia", "Indonesia", "Philippines", "Thailand",
    "Vietnam", "Japan", "China", "Hong Kong", "Korea", "Taiwan",
    "Australia", "New Zealand",
    "Israel", "UAE", "United Arab Emirates", "Saudi Arabia", "Qatar",
    "Egypt", "Nigeria", "South Africa", "Kenya",
    "Brazil", "Argentina", "Chile", "Colombia",
    "Ontario", "Texas", "California", "New York",  # US/Canada state collisions
]


# --- helpers --------------------------------------------------------------
def _word_match(text: str, token: str) -> bool:
    """Case-insensitive whole-word(s) match. Handles multi-word tokens too."""
    if " " in token or "-" in token or "&" in token:
        return token.lower() in text.lower()
    return re.search(rf"(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])",
                     text, flags=re.IGNORECASE) is not None


def _any_word_match(text: str, tokens) -> bool:
    return any(_word_match(text, tok) for tok in tokens)


def _word_in(text: str, token: str) -> bool:
    if " " in token or "-" in token or "." in token:
        return token.lower() in text.lower()
    return re.search(rf"(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])",
                     text, flags=re.IGNORECASE) is not None


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


def is_wanted_role(title: str, dept: str = "") -> bool:
    """True if the title matches any of Subodh's four tracks."""
    blob = f"{title} || {dept}"
    return any(_any_word_match(blob, grp) for grp in WANTED_TOKEN_GROUPS)


# Kept for backward-compat with any caller expecting is_tech().
def is_tech(title: str, dept: str = "") -> bool:
    return is_wanted_role(title, dept)


def classify_track(title: str, dept: str = "") -> str:
    """Bucket a role into one of Subodh's tracks for the Excel tracker.
    Priority order resolves overlaps (a 'Quant Trader' is Quant, not Tech)."""
    blob = f"{title} || {dept}"
    if _any_word_match(blob, QUANT_TOKENS):
        return "Quant"
    if _any_word_match(blob, FINANCE_TOKENS):
        return "Finance/IB"
    if _any_word_match(blob, CONSULTING_TOKENS):
        return "Consulting"
    if _any_word_match(blob, TECH_TOKENS):
        return "Tech/SWE"
    return "Programme"


# --- City buckets used by the digest's per-city sections -----------------
STOCKHOLM_TOKENS = [
    "Stockholm", "Solna", "Kista", "Sundbyberg", "Sverige",
]
NORDIC_TOKENS = [
    "Göteborg", "Gothenburg", "Malmö", "Malmo", "Lund", "Uppsala",
    "Oslo", "Bergen", "Trondheim", "Norway", "Norge",
    "Copenhagen", "København", "Kobenhavn", "Aarhus", "Denmark", "Danmark",
    "Helsinki", "Espoo", "Tampere", "Finland", "Reykjavik", "Reykjavík",
    "Nordic", "Nordics", "Scandinavia", "Sweden",
]
AMSTERDAM_TOKENS = [
    "Amsterdam", "Rotterdam", "The Hague", "Den Haag", "Eindhoven",
    "Utrecht", "Delft", "Netherlands", "Nederland", "Holland",
]
LONDON_TOKENS = [
    "London", "Cambridge", "Oxford", "Edinburgh", "Manchester",
    "United Kingdom", "England",
]
ZURICH_TOKENS = [
    "Zurich", "Zürich", "Geneva", "Genève", "Zug", "Basel", "Lausanne",
    "Switzerland", "Schweiz", "Suisse",
]


def is_stockholm_location(location: str) -> bool:
    return bool(location) and _any_word_match(location, STOCKHOLM_TOKENS)


def is_nordic_location(location: str) -> bool:
    return bool(location) and _any_word_match(location, NORDIC_TOKENS)


def is_amsterdam_location(location: str) -> bool:
    return bool(location) and _any_word_match(location, AMSTERDAM_TOKENS)


def is_london_location(location: str) -> bool:
    return bool(location) and _any_word_match(location, LONDON_TOKENS)


def is_zurich_location(location: str) -> bool:
    return bool(location) and _any_word_match(location, ZURICH_TOKENS)


def is_target_location(location: str, *,
                       extra_tokens: list[str] | None = None) -> bool:
    """True if the location clearly points at one of Subodh's target regions.

    Two-step, mirroring the original India gate but inverted to a whitelist:
      (1) find a target hint — a target country, city, remote phrasing, or a
          user-supplied extra token;
      (2) if a clearly non-target region is *also* named and no target
          country is explicitly present, drop it (kills "London, Ontario",
          "Paris, TX", "Amsterdam, NY").
    """
    if not location:
        return False
    loc = location.strip()

    has_hint = False
    for token in TARGET_COUNTRIES + TARGET_CITIES + TARGET_REMOTE_TOKENS:
        if _word_in(loc, token):
            has_hint = True
            break
    if not has_hint and extra_tokens:
        low = loc.lower()
        for token in extra_tokens:
            if token and token.lower() in low:
                has_hint = True
                break

    if not has_hint:
        return False

    # An explicit target COUNTRY name beats any city-name collision.
    for country in TARGET_COUNTRIES:
        if _word_in(loc, country):
            return True

    # City-only hint: reject if a non-target region is named alongside it.
    for country in NON_TARGET_VETO_COUNTRIES:
        if _word_in(loc, country):
            return False
    return True


def posted_within(job: dict, days: int) -> bool:
    """True if posted within `days` days (or has no timestamp at all — we
    don't want to silently drop boards that omit dates)."""
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
    extra_location_tokens: list[str] | None = None,
    max_age_days: int = 3,
) -> bool:
    title = job.get("title", "")
    dept = job.get("department", "") or ""
    location = job.get("location", "")

    # Location gate — target regions only.
    if not is_target_location(location, extra_tokens=extra_location_tokens):
        return False

    # Freshness gate
    if not posted_within(job, max_age_days):
        return False

    # Trusted source: a curated early-career/events board (e.g. Jane Street's
    # hidden-events board) where every posting is inherently a student event.
    # Skip the role/internship gates — location + freshness already applied.
    if job.get("_trust"):
        return True

    # HR / admin / legal / sales / support veto first — wins over everything.
    if is_non_tech(title, dept):
        return False

    # Must match one of Subodh's four tracks.
    if not is_wanted_role(title, dept):
        return False

    # Internships / student programmes ONLY.
    return is_internship(title, intern_tokens=intern_tokens)


_ROLE_NOUN = r"engineer|developer|programmer|designer|scientist|analyst|researcher|architect|sde|swe|trader|consultant"

_JR_LEVEL_PATTERNS = [
    re.compile(rf"\b({_ROLE_NOUN})\s+(i{{1,2}})\b", re.I),
    re.compile(rf"\b({_ROLE_NOUN})\s*[,]?\s*(level\s*|l\s*)?(1|2)\b(?!\d)", re.I),
    re.compile(rf"\bL\s?(1|2)\b\s+({_ROLE_NOUN})", re.I),
]


def label_for(job: dict) -> str:
    """Short label to show in the digest (Internship / Off-cycle / Spring /
    Summer analyst / Grad / Junior / Regular)."""
    title = job.get("title", "")
    low = title.lower()
    # An explicit full-time marker wins over "campus"/"graduate" wording, so a
    # "Campus Quant Trader (Full-Time)" isn't mislabelled as an internship.
    if ("full-time" in low or "full time" in low) and "intern" not in low:
        return "Grad/FT"
    if any(k in low for k in ("off-cycle", "off cycle", "offcycle")):
        return "Off-cycle"
    if any(k in low for k in ("spring week", "spring insight", "spring programme",
                              "spring program", "insight")):
        return "Spring/Insight"
    if "summer analyst" in low:
        return "Summer analyst"
    if is_internship(title):
        return "Internship"
    if any(k in low for k in ("new grad", "new graduate", "graduate program",
                              "graduate programme", "grad program",
                              "early career", "early-career",
                              "university grad", "campus hire")):
        return "New grad"
    if _word_match(title, "graduate"):
        return "New grad"
    if any(_word_match(title, k) for k in
           ("junior", "jr", "entry-level", "entry level", "associate",
            "trainee", "traineeship")):
        return "Junior"
    for rx in _JR_LEVEL_PATTERNS:
        if rx.search(title):
            return "Junior"
    return "Regular"
