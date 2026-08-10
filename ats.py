"""Fetchers for the public job APIs of every wired ATS / careers site.

Each fetcher returns a list of normalized job dicts:

    {
        "id":         str,
        "title":      str,
        "location":   str,
        "url":        str,
        "department": str,
        "posted_at":  datetime | None,
    }

Live-verified ATS coverage:

  greenhouse        public JSON board
  lever             public JSON board
  ashby             public JSON board
  smartrecruiters   public JSON board
  workday           public undocumented POST endpoint (per-tenant cluster)
  amazon            amazon.jobs search.json (India country filter baked in)
  github            github.careers public JSON API
  microsoft         apply.careers.microsoft.com/api/pcsx/search
  workable          apply.workable.com/api/v3/accounts/{slug}/jobs (POST)
  supercell         supercell.com/en/careers/  __NEXT_DATA__ extract
  iqm               iqm.tech/careers/ HTML link extraction
  apple             jobs.apple.com/en-us/search?location=... per-country

Companies on Workday-with-auth (Cisco, AMD, Atlassian, Snowflake, UiPath,
Confluent, Arm, Qualcomm, ServiceNow, Oracle, Broadcom, Nokia, DJI, ASML,
Vaisala), on Google / Meta CSRF-protected APIs, or on client-side-rendered
TeamTailor / custom pages (ICEYE, Aiven, Klarna, Hoxhunt, Neko Health, …)
need a real headless browser session — they're listed with ats=None.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import aiohttp

log = logging.getLogger("arcy-alerter.ats")

_DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=25)
_HEADERS = {
    "User-Agent": "arcyinternalerter/1.0 personal job watcher",
    "Accept": "application/json",
}


async def _get_json(session: aiohttp.ClientSession, url: str) -> Any | None:
    try:
        async with session.get(url, headers=_HEADERS, timeout=_DEFAULT_TIMEOUT) as resp:
            if resp.status == 404:
                log.warning("404 %s (board slug probably wrong)", url)
                return None
            if resp.status >= 400:
                log.warning("HTTP %s %s", resp.status, url)
                return None
            return await resp.json(content_type=None)
    except asyncio.TimeoutError:
        log.warning("Timeout %s", url)
        return None
    except aiohttp.ClientError as exc:
        log.warning("Network error %s: %s", url, exc)
        return None
    except Exception as exc:
        log.warning("Unexpected error fetching %s: %s", url, exc)
        return None


async def _post_json(session: aiohttp.ClientSession, url: str,
                     body: dict) -> Any | None:
    try:
        async with session.post(
            url,
            json=body,
            headers={**_HEADERS, "Content-Type": "application/json"},
            timeout=_DEFAULT_TIMEOUT,
        ) as resp:
            if resp.status >= 400:
                log.warning("HTTP %s POST %s", resp.status, url)
                return None
            return await resp.json(content_type=None)
    except asyncio.TimeoutError:
        log.warning("Timeout POST %s", url)
        return None
    except aiohttp.ClientError as exc:
        log.warning("Network error POST %s: %s", url, exc)
        return None
    except Exception as exc:
        log.warning("Unexpected error POST %s: %s", url, exc)
        return None


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_epoch_ms(value: Any) -> datetime | None:
    try:
        ms = int(value)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


# --- Greenhouse ------------------------------------------------------------
async def fetch_greenhouse(session: aiohttp.ClientSession, slug: str) -> list[dict]:
    if slug.startswith("eu:"):
        base = "boards-api.eu.greenhouse.io"
        slug = slug[3:]
    else:
        base = "boards-api.greenhouse.io"
    url = f"https://{base}/v1/boards/{slug}/jobs?content=false"
    data = await _get_json(session, url)
    if not data or "jobs" not in data:
        return []
    out: list[dict] = []
    for job in data["jobs"]:
        loc = (job.get("location") or {}).get("name") or ""
        offices = ", ".join(
            o.get("name", "") for o in (job.get("offices") or []) if o.get("name")
        )
        if offices and offices not in loc:
            loc = f"{loc} | {offices}" if loc else offices
        dept = ", ".join(
            d.get("name", "") for d in (job.get("departments") or []) if d.get("name")
        )
        posted_at = _parse_iso(job.get("first_published")) or _parse_iso(job.get("updated_at"))
        out.append(
            {
                "id": f"gh:{slug}:{job.get('id')}",
                "title": job.get("title") or "",
                "location": loc,
                "url": job.get("absolute_url") or "",
                "department": dept,
                "posted_at": posted_at,
            }
        )
    return out


# --- Lever -----------------------------------------------------------------
async def fetch_lever(session: aiohttp.ClientSession, slug: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    data = await _get_json(session, url)
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    for job in data:
        cats = job.get("categories") or {}
        loc = cats.get("location") or ""
        all_locs = ", ".join(
            l for l in (cats.get("allLocations") or []) if l and l != loc
        )
        if all_locs:
            loc = f"{loc} | {all_locs}" if loc else all_locs
        out.append(
            {
                "id": f"lv:{slug}:{job.get('id')}",
                "title": job.get("text") or "",
                "location": loc,
                "url": job.get("hostedUrl") or job.get("applyUrl") or "",
                "department": cats.get("team") or cats.get("department") or "",
                "posted_at": _parse_epoch_ms(job.get("createdAt")),
            }
        )
    return out


# --- Ashby -----------------------------------------------------------------
async def fetch_ashby(session: aiohttp.ClientSession, slug: str) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=false"
    data = await _get_json(session, url)
    if not data or "jobs" not in data:
        return []
    out: list[dict] = []
    for job in data["jobs"]:
        loc = job.get("locationName") or job.get("location") or ""
        secondary = ", ".join(
            (l.get("locationName") if isinstance(l, dict) else l) or ""
            for l in (job.get("secondaryLocations") or [])
        ).strip(", ")
        if secondary:
            loc = f"{loc} | {secondary}" if loc else secondary
        out.append(
            {
                "id": f"ab:{slug}:{job.get('id')}",
                "title": job.get("title") or "",
                "location": loc,
                "url": job.get("jobUrl") or job.get("applyUrl") or "",
                "department": job.get("department")
                              or job.get("departmentName")
                              or job.get("team")
                              or "",
                "posted_at": _parse_iso(job.get("publishedAt")),
            }
        )
    return out


# --- SmartRecruiters -------------------------------------------------------
async def fetch_smartrecruiters(session: aiohttp.ClientSession, slug: str) -> list[dict]:
    url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings?limit=100"
    data = await _get_json(session, url)
    if not data or "content" not in data:
        return []
    out: list[dict] = []
    for job in data["content"]:
        loc_obj = job.get("location") or {}
        loc_parts = [
            loc_obj.get("city"),
            loc_obj.get("region"),
            loc_obj.get("country"),
        ]
        loc = ", ".join(p for p in loc_parts if p)
        out.append(
            {
                "id": f"sr:{slug}:{job.get('id')}",
                "title": job.get("name") or "",
                "location": loc,
                "url": f"https://jobs.smartrecruiters.com/{slug}/{job.get('id')}",
                "department": (job.get("department") or {}).get("label")
                              or (job.get("function") or {}).get("label")
                              or "",
                "posted_at": _parse_iso(job.get("releasedDate")),
            }
        )
    return out


# --- Workday ---------------------------------------------------------------
# Public undocumented endpoint. Slug format: "tenant/cluster/site", e.g.
# "nvidia/5/NVIDIAExternalCareerSite". Only works for tenants that don't
# require auth/CSRF (NVIDIA, Adobe, CrowdStrike, Salesforce confirmed).

_WD_POSTED_PATTERNS = [
    (re.compile(r"posted\s+today", re.I), timedelta(days=0)),
    (re.compile(r"posted\s+yesterday", re.I), timedelta(days=1)),
    (re.compile(r"posted\s+(\d+)\s*\+?\s*days?\s+ago", re.I), None),
]


def _wd_parse_posted(text: str | None) -> datetime | None:
    """Workday returns "Posted Today" / "Posted 3 Days Ago" — best effort."""
    if not text:
        return None
    now = datetime.now(timezone.utc)
    for rx, delta in _WD_POSTED_PATTERNS:
        m = rx.search(text)
        if m:
            if delta is not None:
                return now - delta
            try:
                days = int(m.group(1))
                return now - timedelta(days=days)
            except (ValueError, IndexError):
                return None
    return None


async def fetch_workday(session: aiohttp.ClientSession, slug: str) -> list[dict]:
    # Slug is "tenant/cluster/site" and may carry an optional 4th segment used
    # as a server-side searchText (e.g. "db/3/DBWebsite/intern") so big boards
    # are narrowed before paging — otherwise the newest-80 slice buries the
    # handful of intern roles among hundreds of unrelated postings.
    parts = slug.split("/")
    if len(parts) == 4:
        tenant, cluster, site, search_text = parts
    elif len(parts) == 3:
        tenant, cluster, site = parts
        search_text = ""
    else:
        log.warning("Workday slug must be tenant/cluster/site[/search], got %r", slug)
        return []
    base = f"https://{tenant}.wd{cluster}.myworkdayjobs.com"
    url = f"{base}/wday/cxs/{tenant}/{site}/jobs"

    out: list[dict] = []
    # A filtered search returns few rows, so page deeper (up to 140); an
    # unfiltered board still stops early via the <20 break below.
    for offset in range(0, 140, 20):
        body = {"appliedFacets": {}, "limit": 20, "offset": offset,
                "searchText": search_text}
        data = await _post_json(session, url, body)
        if not data:
            break
        postings = data.get("jobPostings") or []
        if not postings:
            break
        for job in postings:
            ext_path = job.get("externalPath") or ""
            posting_url = (f"{base}/en-US/{site}{ext_path}" if ext_path
                           else f"{base}/{site}")
            out.append(
                {
                    "id": f"wd:{tenant}:{ext_path or job.get('title')}",
                    "title": job.get("title") or "",
                    "location": job.get("locationsText") or "",
                    "url": posting_url,
                    "department": "",
                    "posted_at": _wd_parse_posted(job.get("postedOn")),
                }
            )
        if len(postings) < 20:
            break
    return out


# --- Amazon (amazon.jobs) --------------------------------------------------
# Public search.json. We filter to India on the server side so we only pull
# what we'd actually keep.

_AMZN_IN_CCS = ["IND"]


async def _fetch_amazon_ccs(session: aiohttp.ClientSession,
                            ccs: list[str]) -> list[dict]:
    out: list[dict] = []
    params = "&".join(f"normalized_country_code[]={cc}" for cc in ccs)
    # Paginate; Amazon caps at 100 per page.
    for offset in (0, 100, 200, 300, 400, 500):
        url = (f"https://www.amazon.jobs/en-gb/search.json?{params}"
               f"&offset={offset}&result_limit=100&sort=recent")
        data = await _get_json(session, url)
        if not data:
            break
        jobs = data.get("jobs") or []
        if not jobs:
            break
        for job in jobs:
            path = job.get("job_path") or ""
            url_full = f"https://www.amazon.jobs{path}" if path else ""
            # Posted date like "May 26, 2026"
            posted_at = None
            for fmt in ("%B %d, %Y", "%b %d, %Y"):
                try:
                    posted_at = datetime.strptime(
                        job.get("posted_date") or "", fmt
                    ).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue
            out.append(
                {
                    "id": f"amzn:{job.get('id')}",
                    "title": job.get("title") or "",
                    "location": job.get("normalized_location")
                                or f"{job.get('city','')}, {job.get('country_code','')}",
                    "url": url_full,
                    "department": (job.get("team") or {}).get("label") or "",
                    "posted_at": posted_at,
                }
            )
        if len(jobs) < 100:
            break
    return out


async def fetch_amazon(session: aiohttp.ClientSession, _slug: str) -> list[dict]:
    return await _fetch_amazon_ccs(session, _AMZN_IN_CCS)


# --- Microsoft (apply.careers.microsoft.com pcsx) -------------------------
# Public undocumented endpoint that the careers SPA hits. Returns positions
# but with null posting dates — so we rely on state.json dedupe rather than
# the freshness filter for MS roles.

async def fetch_microsoft(session: aiohttp.ClientSession, _slug: str) -> list[dict]:
    out: list[dict] = []
    seen_ids: set = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0",
        "Accept": "application/json",
        "Referer": "https://jobs.careers.microsoft.com/",
    }
    # Pull a few pages so we surface a meaningful sample. MS has ~10k roles
    # total; we cap to ~200 most-relevant per poll to keep digests sane.
    for start in (0, 20, 40, 60, 80, 100, 140, 180):
        url = ("https://apply.careers.microsoft.com/api/pcsx/search?"
               f"domain=microsoft.com&query=&location=&start={start}&num=20")
        try:
            async with session.get(url, headers=headers,
                                   timeout=_DEFAULT_TIMEOUT) as resp:
                if resp.status >= 400:
                    log.warning("Microsoft HTTP %s @ start=%s", resp.status, start)
                    break
                data = await resp.json(content_type=None)
        except Exception as exc:
            log.warning("Microsoft fetch failed: %s", exc)
            break
        positions = (data.get("data") or {}).get("positions") or []
        if not positions:
            break
        for p in positions:
            jid = p.get("displayJobId") or p.get("id")
            if not jid or jid in seen_ids:
                continue
            seen_ids.add(jid)
            locs = p.get("locations") or []
            location = " | ".join(locs) if isinstance(locs, list) else str(locs)
            title = p.get("name") or p.get("title") or ""
            out.append(
                {
                    "id": f"ms:{jid}",
                    "title": title,
                    "location": location,
                    "url": f"https://jobs.careers.microsoft.com/global/en/job/{jid}",
                    "department": p.get("category") or p.get("subCategory") or "",
                    "posted_at": None,  # MS API doesn't expose date; dedupe via state
                }
            )
    return out


# --- Workable (apply.workable.com) ----------------------------------------
# Works for any Workable-hosted careers page. Slug = the company subdomain
# path on apply.workable.com.

async def fetch_workable(session: aiohttp.ClientSession, slug: str) -> list[dict]:
    url = f"https://apply.workable.com/api/v3/accounts/{slug}/jobs"
    try:
        async with session.post(
            url,
            json={},  # MUST be empty body — adding params returns "Not allowed".
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Origin": "https://apply.workable.com",
                "Referer": f"https://apply.workable.com/{slug}/",
            },
            timeout=_DEFAULT_TIMEOUT,
        ) as resp:
            if resp.status >= 400:
                log.warning("Workable HTTP %s for %s", resp.status, slug)
                return []
            data = await resp.json(content_type=None)
    except Exception as exc:
        log.warning("Workable fetch failed for %s: %s", slug, exc)
        return []
    out: list[dict] = []
    for j in data.get("results", []):
        loc_obj = j.get("location") or {}
        loc_parts = [loc_obj.get("city"), loc_obj.get("region"),
                     loc_obj.get("country")]
        location = ", ".join(p for p in loc_parts if p)
        if j.get("remote"):
            location = f"{location} (Remote)" if location else "Remote"
        out.append(
            {
                "id": f"wk:{slug}:{j.get('id')}",
                "title": j.get("title") or "",
                "location": location,
                "url": (f"https://apply.workable.com/{slug}/j/"
                        f"{j.get('shortcode')}/"),
                "department": j.get("department") or "",
                "posted_at": _parse_iso(j.get("published")
                                        or j.get("created_at")),
            }
        )
    return out


# --- Supercell (Next.js __NEXT_DATA__) ------------------------------------
# Supercell's careers page is a Next.js SSG with all postings baked into
# __NEXT_DATA__. One HTML fetch -> 40+ jobs with location + department.

_SUPERCELL_NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>',
    flags=re.DOTALL,
)


async def fetch_supercell(session: aiohttp.ClientSession, _slug: str) -> list[dict]:
    try:
        async with session.get(
            "https://supercell.com/en/careers/",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"},
            timeout=_DEFAULT_TIMEOUT,
        ) as resp:
            if resp.status >= 400:
                return []
            html = await resp.text()
    except Exception as exc:
        log.warning("Supercell fetch failed: %s", exc)
        return []
    m = _SUPERCELL_NEXT_DATA.search(html)
    if not m:
        return []
    try:
        import json as _json
        data = _json.loads(m.group(1))
    except Exception:
        return []
    postings = (((data.get("props") or {}).get("pageProps") or {})
                .get("postings") or [])
    out: list[dict] = []
    for p in postings:
        jid = p.get("jobId") or p.get("id")
        slug_v = p.get("slug") or ""
        out.append(
            {
                "id": f"sc:{jid}",
                "title": p.get("title") or "",
                "location": p.get("location") or "",
                "url": f"https://supercell.com/en/careers/job/{slug_v}/",
                "department": p.get("department") or "",
                "posted_at": None,
            }
        )
    return out


# --- IQM Quantum Computers (extract TT links from their site) -------------
# iqm.tech/careers/ embeds <a href="https://iqm.teamtailor.com/jobs/..."> for
# each open role. We extract title + URL; location/date aren't on the index.

_IQM_LINK = re.compile(
    r'<a[^>]+href="(https://iqm\.teamtailor\.com/jobs/(\d+)-[^"]+)"[^>]*>'
    r'(.*?)</a>',
    flags=re.DOTALL | re.IGNORECASE,
)


async def fetch_iqm(session: aiohttp.ClientSession, _slug: str) -> list[dict]:
    try:
        async with session.get(
            "https://iqm.tech/careers/",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "text/html"},
            timeout=_DEFAULT_TIMEOUT,
        ) as resp:
            if resp.status >= 400:
                return []
            html = await resp.text()
    except Exception as exc:
        log.warning("IQM fetch failed: %s", exc)
        return []
    seen: set = set()
    out: list[dict] = []
    for url, jid, inner in _IQM_LINK.findall(html):
        if jid in seen:
            continue
        # Inner may contain nested spans/icons. Strip tags to get text.
        title = re.sub(r"<[^>]+>", " ", inner)
        title = re.sub(r"\s+", " ", title).strip()
        if not title:
            continue
        seen.add(jid)
        out.append(
            {
                "id": f"iqm:{jid}",
                "title": title,
                "location": "Espoo, Finland",  # IQM HQ
                "url": url,
                "department": "",
                "posted_at": None,
            }
        )
    return out


# --- Apple (server-rendered search HTML, per-country) ---------------------
# jobs.apple.com renders the search results into HTML server-side. We pull
# the India search page plus the en-in locale page and merge.

_APPLE_DETAIL = re.compile(
    r'href="(/(?:[a-z]{2}-[a-z]{2})/details/(\d+)/([^"?]+))(?:\?team=([^"]+))?"',
)

_APPLE_IN_LOCATIONS = [
    ("india-IND", "India"),
]

# The en-in locale root page is itself an India filter, and it surfaces
# postings the `location=` query sometimes misses. Fetched as well and
# merged (the caller dedupes on posting id).
_APPLE_LOCALE_SEARCHES = [
    ("en-in", "India"),
]


async def fetch_apple(session: aiohttp.ClientSession, _slug: str) -> list[dict]:
    out: list[dict] = []
    seen: set = set()
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/html"}
    searches = (
        [(f"https://jobs.apple.com/en-us/search?location={code}", name)
         for code, name in _APPLE_IN_LOCATIONS]
        + [(f"https://jobs.apple.com/{loc}/search", name)
           for loc, name in _APPLE_LOCALE_SEARCHES]
    )
    for url, loc_name in searches:
        try:
            async with session.get(url, headers=headers,
                                   timeout=_DEFAULT_TIMEOUT) as resp:
                if resp.status >= 400:
                    continue
                html = await resp.text()
        except Exception as exc:
            log.debug("Apple %s failed: %s", loc_name, exc)
            continue
        for full_path, jid, slug_part, team in _APPLE_DETAIL.findall(html):
            if jid in seen:
                continue
            if "/locationPicker" in full_path:
                continue
            seen.add(jid)
            # Title: best-effort from slug ("software-engineer-machine-learning"
            # -> "Software Engineer Machine Learning"). The HTML also has
            # readable titles but extracting them robustly is fragile; the
            # slug-derived title is good enough for the filter.
            title = " ".join(w.capitalize() for w in slug_part.split("-"))
            out.append(
                {
                    "id": f"apl:{jid}",
                    "title": title,
                    "location": loc_name,
                    "url": f"https://jobs.apple.com{full_path}",
                    "department": team or "",
                    "posted_at": None,
                }
            )
    return out


# --- Phenom People careers (GitHub, AMD, and many others) ------------------
# Pattern: https://{host}/api/jobs?page=N&limit=50  returns
#   {jobs: [{data: {title, city, country, slug, posting_created, ...}}]}
# Slug format: "host|prefix"  e.g. "github.careers|github" or
#              "careers.amd.com|amd".

async def _fetch_phenom(session: aiohttp.ClientSession, host: str,
                         prefix: str) -> list[dict]:
    out: list[dict] = []
    for page in (1, 2, 3, 4, 5):
        url = (f"https://{host}/api/jobs?stretchUnit=MILES&stretch=10"
               f"&page={page}&limit=50")
        data = await _get_json(session, url)
        if not data:
            break
        jobs = data.get("jobs") or []
        if not jobs:
            break
        for entry in jobs:
            j = entry.get("data") or entry
            cities = j.get("city") or j.get("location_name") or ""
            country = j.get("country") or ""
            location = ", ".join(filter(None, [cities, country]))
            posted = (_parse_iso(j.get("posting_updated"))
                      or _parse_iso(j.get("posting_created")))
            slug_v = j.get("slug") or j.get("id") or j.get("req_id")
            out.append(
                {
                    "id": f"phenom:{prefix}:{slug_v}",
                    "title": j.get("title") or "",
                    "location": location,
                    "url": f"https://{host}/careers-home/jobs/{slug_v}",
                    "department": j.get("department") or j.get("category") or "",
                    "posted_at": posted,
                }
            )
        if len(jobs) < 50:
            break
    return out


async def fetch_github(session: aiohttp.ClientSession, _slug: str) -> list[dict]:
    return await _fetch_phenom(session, "github.careers", "github")


async def fetch_amd(session: aiohttp.ClientSession, _slug: str) -> list[dict]:
    return await _fetch_phenom(session, "careers.amd.com", "amd")


async def fetch_phenom(session: aiohttp.ClientSession, slug: str) -> list[dict]:
    """Generic Phenom People fetcher. Slug format: 'host|prefix'
    e.g. 'jobs.sap.com|sap' or 'careers.vodafone.com|vodafone'."""
    if "|" in slug:
        host, _, prefix = slug.partition("|")
    else:
        host = slug
        prefix = slug.split(".")[0]
    return await _fetch_phenom(session, host, prefix)


# --- Recruitee (many EU scaleups) -----------------------------------------
# Clean public JSON API: GET https://{slug}.recruitee.com/api/offers/
# Slug = company subdomain, e.g. "personio" for personio.recruitee.com.

async def fetch_recruitee(session: aiohttp.ClientSession, slug: str) -> list[dict]:
    url = f"https://{slug}.recruitee.com/api/offers/?limit=100"
    data = await _get_json(session, url)
    if not data or "offers" not in data:
        return []
    out: list[dict] = []
    for job in data["offers"]:
        city    = job.get("city")    or job.get("location") or ""
        country = job.get("country") or ""
        location = ", ".join(p for p in [city, country] if p)
        if job.get("remote"):
            location = f"{location} (Remote)" if location else "Remote"
        tags = job.get("tags") or []
        if tags:
            first = tags[0]
            dept = first if isinstance(first, str) else first.get("name") or ""
        else:
            dept = ""
        posted  = job.get("published_at") or job.get("created_at")
        slug_v  = job.get("slug") or str(job.get("id") or "")
        out.append({
            "id":         f"rt:{slug}:{job.get('id')}",
            "title":      job.get("title") or "",
            "location":   location,
            "url":        f"https://{slug}.recruitee.com/o/{slug_v}",
            "department": dept,
            "posted_at":  _parse_iso(posted),
        })
    return out


# --- TeamTailor RSS/Atom (Finnish startups + many EU scaleups) -------------
# Each TT careers page exposes /jobs.rss (RSS 2.0) and /jobs.atom. We probe
# both. Slug = the host root, e.g. "iqm.teamtailor.com" or
# "careers.relexsolutions.com".

_TT_RSS_ITEM = re.compile(
    r"<item>(.+?)</item>", flags=re.DOTALL | re.IGNORECASE,
)
_TT_ATOM_ENTRY = re.compile(
    r"<entry>(.+?)</entry>", flags=re.DOTALL | re.IGNORECASE,
)
_TT_TAG = re.compile(r"<([a-z:]+)[^>]*>(.+?)</\1>", flags=re.DOTALL | re.IGNORECASE)


def _strip_cdata(s: str) -> str:
    return re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s, flags=re.DOTALL).strip()


def _parse_tt_item(block: str) -> dict:
    out = {}
    for m in _TT_TAG.finditer(block):
        tag = m.group(1).lower()
        val = _strip_cdata(m.group(2))
        # Strip nested HTML so location/title stay clean.
        if tag in ("title", "location", "link", "id", "pubdate", "published",
                   "updated", "description", "category"):
            out.setdefault(tag, val)
    # atom <link href="..."/> self-closing
    if "link" not in out:
        m = re.search(r'<link[^>]+href="([^"]+)"', block)
        if m:
            out["link"] = m.group(1)
    return out


async def fetch_teamtailor(session: aiohttp.ClientSession,
                            slug: str) -> list[dict]:
    """Slug = the careers host (e.g. 'iqm.teamtailor.com' or
    'careers.relexsolutions.com'). Tries .rss then .atom."""
    host = slug.strip().strip("/")
    for ext in ("jobs.rss", "jobs.atom"):
        url = f"https://{host}/{ext}"
        try:
            async with session.get(url, headers=_HEADERS,
                                   timeout=_DEFAULT_TIMEOUT) as resp:
                if resp.status >= 400:
                    continue
                xml = await resp.text()
        except Exception:
            continue
        items = _TT_RSS_ITEM.findall(xml) or _TT_ATOM_ENTRY.findall(xml)
        if not items:
            continue
        out: list[dict] = []
        for block in items:
            f = _parse_tt_item(block)
            title = f.get("title") or ""
            # Title sometimes is "Job Title - Department" — keep as-is.
            link = f.get("link") or ""
            jid = link.rstrip("/").rsplit("/", 1)[-1] or title
            # Location often appears in <description> like "Helsinki" or
            # "Munich, Germany" / inside <category> tags.
            location = f.get("location") or ""
            if not location:
                desc = f.get("description") or ""
                # TT description often contains "Location: X<br>"
                m = re.search(r"Location\s*:?\s*([A-Za-zÀ-ž\u00C0-\u017F\-\.,\s]+)",
                              desc)
                if m:
                    location = m.group(1).strip().rstrip(".,")
            posted_at = (_parse_iso(f.get("published"))
                         or _parse_iso(f.get("updated"))
                         or _parse_rfc822(f.get("pubdate")))
            out.append(
                {
                    "id": f"tt:{host}:{jid}",
                    "title": _clean_html(title),
                    "location": _clean_html(location),
                    "url": link,
                    "department": f.get("category") or "",
                    "posted_at": posted_at,
                }
            )
        return out
    return []


def _clean_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


_RFC822_FMTS = [
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S GMT",
    "%d %b %Y %H:%M:%S %z",
]


def _parse_rfc822(value: str | None) -> datetime | None:
    if not value:
        return None
    s = value.strip()
    for fmt in _RFC822_FMTS:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


# --- Snap (careers.snap.com/api/jobs — Workday-backed but aggregated) ------

async def fetch_snap(session: aiohttp.ClientSession, _slug: str) -> list[dict]:
    """Snap exposes their full board via a single anonymous endpoint that
    returns Elasticsearch hits."""
    url = "https://careers.snap.com/api/jobs?page=1&size=200"
    data = await _get_json(session, url)
    if not data:
        return []
    out: list[dict] = []
    for hit in data.get("body", []) or []:
        src = hit.get("_source", {})
        offices = src.get("offices") or []
        loc = " | ".join(o.get("name", "") for o in offices if o.get("name"))
        if not loc:
            loc = src.get("primary_location") or ""
        out.append(
            {
                "id": f"snap:{src.get('id')}",
                "title": src.get("title") or "",
                "location": loc,
                "url": src.get("absolute_url") or "",
                "department": src.get("departments") or "",
                "posted_at": None,
            }
        )
    return out


# --- Netflix (explore.jobs.netflix.net Eightfold-style) -------------------

async def fetch_netflix(session: aiohttp.ClientSession, _slug: str) -> list[dict]:
    out: list[dict] = []
    seen: set = set()
    for start in (0, 100, 200, 300, 400):
        url = ("https://explore.jobs.netflix.net/api/apply/v2/jobs"
               f"?domain=netflix.com&start={start}&num=100&sort_by=relevance")
        data = await _get_json(session, url)
        if not data:
            break
        positions = data.get("positions") or []
        if not positions:
            break
        for p in positions:
            pid = p.get("id") or p.get("display_job_id")
            if pid in seen:
                continue
            seen.add(pid)
            locs = p.get("locations") or [p.get("location")] if p.get("location") else []
            loc = " | ".join(l for l in locs if l)
            ts = p.get("t_create") or p.get("t_update")
            posted_at = (datetime.fromtimestamp(int(ts), tz=timezone.utc)
                         if isinstance(ts, (int, float)) else None)
            out.append(
                {
                    "id": f"nflx:{pid}",
                    "title": p.get("name") or "",
                    "location": loc,
                    "url": (f"https://explore.jobs.netflix.net/careers/job/"
                            f"{pid}/"),
                    "department": p.get("department") or "",
                    "posted_at": posted_at,
                }
            )
        if len(positions) < 100:
            break
    return out


# --- dispatch --------------------------------------------------------------

FETCHERS = {
    "greenhouse":      fetch_greenhouse,
    "lever":           fetch_lever,
    "ashby":           fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
    "workday":         fetch_workday,
    "amazon":          fetch_amazon,
    "github":          fetch_github,
    "microsoft":       fetch_microsoft,
    "workable":        fetch_workable,
    "supercell":       fetch_supercell,
    "iqm":             fetch_iqm,    # legacy HTML scrape (now redundant)
    "apple":           fetch_apple,
    "amd":             fetch_amd,
    "teamtailor":      fetch_teamtailor,
    "snap":            fetch_snap,
    "netflix":         fetch_netflix,
    "recruitee":       fetch_recruitee,
    "phenom":          fetch_phenom,
}


async def fetch_company(session: aiohttp.ClientSession, company: dict) -> list[dict]:
    ats = company.get("ats")
    slug = company.get("slug")
    name = company.get("name", slug)
    fetcher = FETCHERS.get(ats)
    if not fetcher or not slug:
        log.debug("Skipping %s: unsupported ATS %r", name, ats)
        return []
    jobs = await fetcher(session, slug)
    for j in jobs:
        j["company"] = name
        j["company_country"] = company.get("country", "")
    return jobs
