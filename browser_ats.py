"""Playwright-based fetchers for sites that genuinely need a real browser.

Heavy and slow — uses headless Chromium. Only loaded if `USE_BROWSER=1` is
set in the environment (or `--browser` is passed on the CLI). Daily-digest
runs cost ~5-10 seconds per browser-fetched company, so we cap to the
~10 highest-value holdouts.

Strategy:

  1. Launch one Chromium process for the whole run.
  2. For each Workday tenant, navigate to the careers SPA, let it boot,
     intercept the `/wday/cxs/.../jobs` XHR response — Workday's own SPA
     fires it on init/search, so we piggyback on the auth tokens it already
     has from AWS Cognito.
  3. Normalize into the same job dict shape `ats.py` produces.

The Microsoft / Meta / Google / Tesla / Netflix / Shopify / Snap holdouts are
all behind anti-bot CDNs (Cloudflare turnstile, reCAPTCHA, Akamai). Even
with a real browser they reject Playwright's default fingerprint within a
few requests, so they're out of scope unless you wire `chromium-stealth`
or use the user's logged-in profile, which we don't do automatically.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

log = logging.getLogger("intern-alerter.browser")


WORKDAY_TENANTS = [
    # (display name, tenant, cluster, site)
    ("Cisco",       "cisco",       "1",  "External_Career_Site"),
    ("AMD",         "amd",         "1",  "AMDExternalCareerSite"),
    ("Atlassian",   "atlassian",   "5",  "External"),
    ("Snowflake",   "snowflake",   "1",  "Snowflake_Careers"),
    ("UiPath",      "uipath",      "1",  "UiPathCareers"),
    ("Confluent",   "confluent",   "1",  "confluent_careers"),
    ("Qualcomm",    "qualcomm",    "5",  "External"),
    ("ServiceNow",  "servicenow",  "1",  "ServiceNowCareers"),
    ("Oracle",      "oracle",      "5",  "OracleCorporation"),
    ("Nokia",       "nokia",       "3",  "nokia"),
    ("Vaisala",     "vaisala",     "3",  "vaisala"),
    ("Tesla",       "tesla",       "5",  "tesla"),
    ("Broadcom",    "broadcom",    "5",  "External_Career_Site"),
    ("Arm",         "arm",         "3",  "Apply_for_a_Job"),
]

WORKDAY_BY_NAME = {entry[0]: entry for entry in WORKDAY_TENANTS}


_WD_POSTED_PATTERNS = [
    (re.compile(r"posted\s+today", re.I), timedelta(days=0)),
    (re.compile(r"posted\s+yesterday", re.I), timedelta(days=1)),
    (re.compile(r"posted\s+(\d+)\s*\+?\s*days?\s+ago", re.I), None),
]


def _wd_parse_posted(text: str | None) -> datetime | None:
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


def _wd_normalize(jobs_payload: dict, tenant: str, cluster: str,
                   site: str) -> list[dict]:
    base = f"https://{tenant}.wd{cluster}.myworkdayjobs.com"
    out: list[dict] = []
    for job in jobs_payload.get("jobPostings", []) or []:
        ext_path = job.get("externalPath") or ""
        posting_url = (f"{base}/en-US/{site}{ext_path}" if ext_path
                       else f"{base}/{site}")
        out.append(
            {
                "id": f"wd-pw:{tenant}:{ext_path or job.get('title')}",
                "title": job.get("title") or "",
                "location": job.get("locationsText") or "",
                "url": posting_url,
                "department": "",
                "posted_at": _wd_parse_posted(job.get("postedOn")),
            }
        )
    return out


async def _fetch_workday_with_browser(
    browser_ctx: Any, tenant: str, cluster: str, site: str,
) -> list[dict]:
    """Load Workday SPA in a real browser, intercept its own jobs XHR."""
    page = await browser_ctx.new_page()
    base = f"https://{tenant}.wd{cluster}.myworkdayjobs.com"
    home = f"{base}/en-US/{site}"
    api_path = f"/wday/cxs/{tenant}/{site}/jobs"

    captured: list[dict] = []
    done = asyncio.Event()

    async def on_response(response):
        if api_path not in response.url:
            return
        if response.request.method != "POST":
            return
        if response.status != 200:
            return
        try:
            payload = await response.json()
        except Exception:
            return
        captured.append(payload)
        # Don't set done immediately — we want pages 2-4 too if they fire.

    page.on("response", lambda r: asyncio.create_task(on_response(r)))

    try:
        try:
            await page.goto(home, wait_until="domcontentloaded", timeout=35000)
        except Exception as exc:
            log.warning("Workday %s nav failed: %s", tenant, exc)
            return []
        # Some Workday tenants auto-search on load; many wait for the user
        # to click 'Search'. Try BOTH: wait, then explicitly click any
        # apply-filter / search button we find.
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        for selector in (
            "[data-automation-id='applyFilterButton']",
            "[data-automation-id='searchButton']",
            "button[aria-label*='Search' i]",
            "button:has-text('Search')",
        ):
            try:
                btn = page.locator(selector).first
                if await btn.count():
                    await btn.click(timeout=3000)
                    break
            except Exception:
                continue
        try:
            await page.wait_for_response(
                lambda r: api_path in r.url
                          and r.request.method == "POST"
                          and r.status == 200,
                timeout=20000,
            )
        except Exception:
            pass
        await page.wait_for_timeout(2000)
    finally:
        await page.close()

    out: list[dict] = []
    for payload in captured:
        out.extend(_wd_normalize(payload, tenant, cluster, site))
    # dedupe by id (Workday sometimes fires the same XHR twice on boot)
    seen = set()
    uniq: list[dict] = []
    for j in out:
        if j["id"] in seen:
            continue
        seen.add(j["id"])
        uniq.append(j)
    return uniq


# Public entrypoint --------------------------------------------------------

async def fetch_workday_browser(company: dict) -> list[dict]:
    """fetch_company-style wrapper. Caller passes the company dict; the
    'slug' is the display name (e.g. 'Cisco') matching WORKDAY_TENANTS."""
    from playwright.async_api import async_playwright  # lazy import

    name = company.get("slug") or company.get("name")
    entry = WORKDAY_BY_NAME.get(name)
    if not entry:
        log.warning("No Workday recipe for %r", name)
        return []
    _, tenant, cluster, site = entry

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="en-US",
            )
            jobs = await _fetch_workday_with_browser(ctx, tenant, cluster, site)
        finally:
            await browser.close()
    return jobs


async def fetch_all_workday_browser(companies: list[dict]) -> dict[str, list[dict]]:
    """Open ONE browser, fetch every requested Workday tenant in it serially.
    Returns {company_name: jobs}. Much cheaper than launching per-company."""
    from playwright.async_api import async_playwright  # lazy import

    results: dict[str, list[dict]] = {}
    targets = [c for c in companies if c.get("ats") == "workday_browser"]
    if not targets:
        return results

    log.info("Browser fetch: %d Workday-with-CSRF tenants…", len(targets))
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                locale="en-US",
            )
            for c in targets:
                entry = WORKDAY_BY_NAME.get(c.get("slug"))
                if not entry:
                    log.warning("Unknown Workday-browser slug: %r", c.get("slug"))
                    continue
                _, tenant, cluster, site = entry
                try:
                    jobs = await _fetch_workday_with_browser(ctx, tenant, cluster, site)
                    for j in jobs:
                        j["company"] = c["name"]
                        j["company_country"] = c.get("country", "")
                    results[c["name"]] = jobs
                    log.info("  %s -> %d jobs", c["name"], len(jobs))
                except Exception as exc:
                    log.warning("  %s failed: %s", c["name"], exc)
                    results[c["name"]] = []
        finally:
            await browser.close()
    return results
