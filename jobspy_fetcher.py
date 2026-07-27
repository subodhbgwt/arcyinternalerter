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
                region: str = "India") -> list[dict]:
    """Blocking — call via asyncio.to_thread. `region` is the search
    location, always India for this alerter."""
    try:
        from jobspy import scrape_jobs
    except ImportError:
        log.warning("python-jobspy not installed. Run: pip install python-jobspy")
        return []

    sites = ["linkedin"] if linkedin_id else ["google"]
    kwargs = {
        "site_name": sites,
        "search_term": "software engineer",
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
    else:
        where = region
        kwargs["google_search_term"] = (
            f'"{company_name}" software engineer jobs {where} '
            f"since {hours_old//24 or 1} days ago"
        )

    try:
        df = scrape_jobs(**kwargs)
    except Exception as exc:
        log.warning("JobSpy failed for %s (%s): %s", company_name, region, exc)
        return []

    if df is None or df.empty:
        return []

    out: list[dict] = []
    for _, row in df.iterrows():
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
        })
    return out


# Single search region — this alerter is India-only, so there is no second
# pass for any company.
REGIONS = ["India"]


async def fetch_jobspy(company: dict, *, hours_old: int = 48,
                      max_results: int = 25) -> list[dict]:
    slug = (company.get("slug") or "").strip()
    linkedin_id = None
    company_name = company.get("name", "")
    if "|" in slug:
        linkedin_id, _, _ = slug.partition("|")
    elif slug.isdigit():
        linkedin_id = slug

    regions = list(REGIONS)

    jobs: list[dict] = []
    seen: set[str] = set()
    for i, region in enumerate(regions):
        if i:
            # Throttle between passes so LinkedIn doesn't 429 us.
            await asyncio.sleep(8)
        batch = await asyncio.to_thread(
            _scrape_one, company_name, linkedin_id, hours_old,
            max_results, region,
        )
        for j in batch:
            if j["id"] in seen:
                continue
            seen.add(j["id"])
            jobs.append(j)

    for j in jobs:
        j["company"] = company_name
        j["company_country"] = company.get("country", "")
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
