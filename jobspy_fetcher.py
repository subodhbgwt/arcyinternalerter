"""JobSpy-based fallback fetchers for companies that don't expose an
anonymous ATS API (Google, Meta, Tesla, ASML, Atlassian, Cisco, etc.).

JobSpy scrapes LinkedIn / Google Jobs / Indeed under the hood. It's slow
(2-15s per company) and rate-limit-prone, so this module is opt-in via
USE_JOBSPY=1 / --jobspy.

Slug format: 'linkedin_company_id|search_query'
  e.g.  '1441|Google' for Google's LinkedIn ID 1441
        '10667|Meta' for Meta's ID
"""
from __future__ import annotations

import asyncio
import logging
import warnings
from datetime import datetime, timezone

warnings.filterwarnings("ignore", category=DeprecationWarning)

log = logging.getLogger("arcy-alerter.jobspy")


def _epoch(dt) -> datetime | None:
    if dt is None:
        return None
    try:
        # pandas Timestamp or datetime
        if hasattr(dt, "to_pydatetime"):
            dt = dt.to_pydatetime()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _scrape_one(company_name: str, linkedin_id: str | None,
                hours_old: int, max_results: int,
                region: str = "Sweden",
                search_term: str = "software engineer",
                match_tokens: list[str] | None = None) -> list[dict]:
    """Blocking, call it via asyncio.to_thread. `region` is the search
    location; `search_term` lets finance/consulting firms search their own
    function (e.g. "analyst") instead of the tech default."""
    try:
        from jobspy import scrape_jobs
    except ImportError:
        log.warning("python-jobspy not installed. Run: pip install python-jobspy")
        return []

    # Google Jobs returned ~0 for every firm, so firms without a numeric
    # LinkedIn id now use a LinkedIn keyword search on "<firm> <term>" and
    # keep only rows whose company matches. Sweeps (company_name=None) search
    # the term on its own and keep every company.
    sites = ["linkedin"]
    term = search_term
    if not linkedin_id and company_name:
        term = f"{company_name} {search_term}"
    kwargs = {
        "site_name": sites,
        "search_term": term,
        "location": region,
        "results_wanted": max_results,
        "hours_old": hours_old,
        "linkedin_fetch_description": False,
        "verbose": 0,
    }
    if linkedin_id:
        try:
            kwargs["linkedin_company_ids"] = [int(linkedin_id)]
        except ValueError:
            pass

    try:
        df = scrape_jobs(**kwargs)
    except Exception as exc:
        log.warning("JobSpy failed for %s (%s): %s", company_name, region, exc)
        return []

    if df is None or df.empty:
        return []

    out: list[dict] = []
    for _, row in df.iterrows():
        row_company = str(row.get("company") or "").strip()
        if company_name and not linkedin_id and match_tokens:
            if not any(t.lower() in row_company.lower() for t in match_tokens):
                continue
        title = str(row.get("title") or "")
        location = str(row.get("location") or "")
        url = str(row.get("job_url") or row.get("job_url_direct") or "")
        posted = _epoch(row.get("date_posted"))
        jid = (str(row.get("id") or row.get("job_url") or "")
               or f"{title}|{location}")
        out.append({
            "id": f"jobspy:{company_name}:{jid}",
            "title": title,
            "location": location,
            "url": url,
            "department": "",
            "posted_at": posted,
            "company": row_company,
        })
    return out


# Default search region is Sweden (keeps the ~130-company generic sweep fast
# and Stockholm-relevant). Finance/consulting firms override with their own
# "jobspy_regions" list (e.g. banks -> UK, UBS -> Switzerland).
REGIONS = ["Sweden"]


async def fetch_jobspy(company: dict, *, hours_old: int = 48,
                      max_results: int = 25) -> list[dict]:
    slug = (company.get("slug") or "").strip()
    linkedin_id = None
    company_name = company.get("name", "")
    if "|" in slug:
        linkedin_id, _, _ = slug.partition("|")
    elif slug.isdigit():
        linkedin_id = slug

    sweep = bool(company.get("sweep"))
    match_tokens = company.get("jobspy_match") or [company_name.split()[0]]
    regions = company.get("jobspy_regions") or list(REGIONS)
    searches = company.get("jobspy_search") or ["software engineer"]
    if isinstance(searches, str):
        searches = [searches]

    jobs: list[dict] = []
    seen: set[str] = set()
    first = True
    for region in regions:
        for term in searches:
            if not first:
                # Throttle between passes so LinkedIn doesn't 429 us.
                await asyncio.sleep(8)
            first = False
            batch = await asyncio.to_thread(
                _scrape_one, None if sweep else company_name, linkedin_id,
                hours_old, max_results, region, term, match_tokens,
            )
            for j in batch:
                if j["id"] in seen:
                    continue
                seen.add(j["id"])
                jobs.append(j)

    for j in jobs:
        if not (sweep and j.get("company")):
            j["company"] = company_name
        j["company_country"] = company.get("country", "")
        j["_max_age_days"] = max(1, hours_old // 24)
    return jobs


# Company → LinkedIn company ID for the auth-walled holdouts we'd want via
# JobSpy. IDs verified from each company's public linkedin.com/company URL.
LINKEDIN_IDS = {
    "Google":           "1441",
    "Meta":             "10667",
    "Tesla":            "15564",
    "ASML":             "4287",
    "Atlassian":        "21629",
    "Cisco":            "1063",
    "ServiceNow":       "14375",
    "Oracle":           "1028",
    "Coinbase":         "6622162",
    "Klarna":           "11497",
    "Bolt":             "8966211",
    "Revolut":          "4476554",
    "Canva":            "3081311",
    "Uber":             "1815218",
    "Citadel":          "11116",
    "Citadel Securities":"3128648",
    "Two Sigma":        "21089",
    "Optiver":          "21063",
    "G-Research":       "10090",
    "Hudson River Trading":"15193",
    "DRW":              "9265",
    "Susquehanna International Group":"8780",
    "Riot Games":       "11164",
    "Epic Games":       "10906",
    "Intel":            "1053",
    "Samsung Electronics":"1186",
    "ByteDance":        "10810658",
    "Plaid":            "3013575",
    "Magic":            "73923174",
    "Black Forest Labs":"99918823",
    # Gaming
    "Electronic Arts":  "1271",
    "Ubisoft":          "2142",
    "CD Projekt":       "181462",
    # Enterprise
    "SAP":              "1115",
    "IBM":              "1009",
    "Siemens":          "1043",
    "Ericsson":         "5765",
    "Logitech":         "3539",
    # Finance / banks
    "Goldman Sachs":    "1038",
    "Bloomberg":        "7697",
    "Morgan Stanley":   "7044",
    "JPMorgan Chase":   "1067",
    "PayPal":           "10962",
}
