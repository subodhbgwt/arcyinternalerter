"""Poll every wired ATS for INDIA tech/SWE internships and ping Telegram.

Two delivery modes:

    --digest          (recommended)  - One grouped Telegram message per run,
                                       covering everything posted in the last
                                       MAX_AGE_DAYS days (default 3) that
                                       we haven't already sent. Wire this to
                                       Windows Task Scheduler to run once
                                       per day and you get a daily digest.

    --once / --loop   (legacy)       - Per-posting alerts, one Telegram
                                       message per new role.

Usage:
    python tracker.py --digest                 # one daily digest, exit
    python tracker.py --digest --loop          # send a digest every DIGEST_INTERVAL_HOURS
    python tracker.py --digest --dry-run       # preview, no Telegram
    python tracker.py --verify                 # ping every slug, report alive/dead
    python tracker.py --once                   # legacy per-posting mode
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import logging
import os
import sys
from pathlib import Path

import aiohttp
from dotenv import load_dotenv

from ats import fetch_company
from companies import all_companies, supported_companies
from filters import passes, label_for, is_internship
from notifier import send_digest, send_job, send_text
from state import SeenStore

# Browser fetcher is optional — only imported if USE_BROWSER=1 / --browser.
fetch_all_workday_browser = None  # type: ignore[assignment]

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("arcy-alerter")


def _clean(v: str) -> str:
    s = (v or "").strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1]
    return s.strip()


def _csv(v: str) -> list[str]:
    return [x.strip() for x in (v or "").split(",") if x.strip()]


TELEGRAM_BOT_TOKEN = _clean(os.environ.get("TELEGRAM_BOT_TOKEN", ""))
TELEGRAM_CHAT_ID = _clean(os.environ.get("TELEGRAM_CHAT_ID", ""))
POLL_INTERVAL = int(_clean(os.environ.get("POLL_INTERVAL_SECONDS", "")) or "900")
DIGEST_INTERVAL_HOURS = float(
    _clean(os.environ.get("DIGEST_INTERVAL_HOURS", "")) or "24"
)
MAX_AGE_DAYS = int(_clean(os.environ.get("MAX_AGE_DAYS", "")) or "2")
STATE_FILE = ROOT / (_clean(os.environ.get("STATE_FILE", "")) or "state.json")
TRACKER_FILE = ROOT / (_clean(os.environ.get("TRACKER_FILE", "")) or "job_tracker.xlsx")
EXTRA_LOC = _csv(_clean(os.environ.get("EXTRA_LOCATIONS", "")
                        or os.environ.get("INDIA_LOCATIONS", "")))
INTERN_EXTRA = _csv(_clean(os.environ.get("INTERN_KEYWORDS", "")))
USE_BROWSER = _clean(os.environ.get("USE_BROWSER", "")) in ("1", "true", "True", "yes")
USE_JOBSPY = _clean(os.environ.get("USE_JOBSPY", "")) in ("1", "true", "True", "yes")


async def _fetch_all(session: aiohttp.ClientSession,
                     use_browser: bool = False,
                     use_jobspy: bool = False) -> list[dict]:
    # Plain HTTP fetchers — high concurrency.
    plain_companies = [c for c in supported_companies()
                       if c.get("ats") not in ("workday_browser", "jobspy")]
    sem = asyncio.Semaphore(8)

    async def one(company: dict) -> list[dict]:
        async with sem:
            try:
                jobs = await fetch_company(session, company)
                if company.get("trust"):
                    for j in jobs:
                        j["_trust"] = True
                return jobs
            except Exception as exc:
                log.warning("Fetch failed for %s: %s", company.get("name"), exc)
                return []

    coros = [one(c) for c in plain_companies]
    results = await asyncio.gather(*coros)
    out: list[dict] = []
    for r in results:
        out.extend(r)

    # Browser-based Workday tenants (slow). Only fetched when opted in.
    browser_companies = [c for c in supported_companies()
                         if c.get("ats") == "workday_browser"]
    if browser_companies and use_browser:
        try:
            from browser_ats import fetch_all_workday_browser as _go
            browser_results = await _go(browser_companies)
            for jobs in browser_results.values():
                out.extend(jobs)
        except ImportError:
            log.warning("USE_BROWSER=1 but playwright not installed; skipping")
        except Exception:
            log.exception("Browser fetch failed; continuing with plain fetchers")
    elif browser_companies and not use_browser:
        log.info("Skipping %d browser-only boards (set USE_BROWSER=1 to enable)",
                 len(browser_companies))

    # JobSpy-based fallback for auth-walled big-tech holdouts. Slow + rate-
    # limited (LinkedIn). Opt-in via USE_JOBSPY=1 / --jobspy.
    jobspy_companies = [c for c in supported_companies()
                        if c.get("ats") == "jobspy"]
    if jobspy_companies and use_jobspy:
        try:
            from jobspy_fetcher import fetch_jobspy
            log.info("JobSpy fetch: %d companies via LinkedIn/Google Jobs…",
                     len(jobspy_companies))
            for c in jobspy_companies:
                try:
                    jobs = await fetch_jobspy(c, hours_old=MAX_AGE_DAYS * 24)
                    out.extend(jobs)
                    log.info("  %s -> %d jobs", c["name"], len(jobs))
                except Exception as exc:
                    log.warning("  %s failed: %s", c["name"], exc)
                # throttle to avoid LinkedIn 429s
                await asyncio.sleep(8)
        except ImportError:
            log.warning("USE_JOBSPY=1 but python-jobspy not installed; "
                        "run: pip install python-jobspy")
    elif jobspy_companies and not use_jobspy:
        log.info("Skipping %d JobSpy boards (set USE_JOBSPY=1 to enable)",
                 len(jobspy_companies))

    return out


# --- verify ---------------------------------------------------------------
async def cmd_verify(use_browser: bool = False) -> int:
    print(f"Verifying {len(supported_companies())} wired boards "
          f"(of {len(all_companies())} total companies)\n")
    async with aiohttp.ClientSession() as session:
        for company in supported_companies():
            if company["ats"] == "workday_browser" and not use_browser:
                print(f"  ..  workday_browser  {company['slug']:<22} "
                      f"{company['name']}  (skipped — set USE_BROWSER=1 or pass --browser)")
                continue
            if company["ats"] == "workday_browser":
                from browser_ats import fetch_workday_browser
                jobs = await fetch_workday_browser(company)
            else:
                jobs = await fetch_company(session, company)
            status = "OK " if jobs else "??"
            print(f"  {status}  {company['ats']:<16} {company['slug']:<30} "
                  f"{company['name']}  -> {len(jobs)} jobs")
    print("\nNot wired (no public JSON API, or slug TBD):")
    for c in all_companies():
        if not c.get("ats") or not c.get("slug"):
            print(f"        --             --                             {c['name']}")
    return 0


# --- shared filtering -----------------------------------------------------
def _filter_jobs(jobs: list[dict]) -> list[dict]:
    out: list[dict] = []
    for job in jobs:
        if not passes(
            job,
            intern_tokens=INTERN_EXTRA or None,
            extra_location_tokens=EXTRA_LOC or None,
            max_age_days=MAX_AGE_DAYS,
        ):
            continue
        job["_label"] = label_for(job)
        out.append(job)
    return out


# --- digest mode (default + recommended) ---------------------------------
async def cmd_digest(*, dry_run: bool, use_browser: bool,
                     use_jobspy: bool = False) -> int:
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID) and not dry_run:
        sys.exit("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing in .env "
                 "(or pass --dry-run)")

    store = SeenStore(STATE_FILE)
    log.info(
        "Digest run: %d wired companies, %d ids in state, looking back %d day(s)%s.",
        len(supported_companies()), len(store), MAX_AGE_DAYS,
        " (browser mode ON)" if use_browser else "",
    )

    async with aiohttp.ClientSession() as session:
        all_jobs = await _fetch_all(session, use_browser=use_browser,
                                    use_jobspy=use_jobspy)
        log.info("Fetched %d total postings", len(all_jobs))

        matches = _filter_jobs(all_jobs)
        log.info("After track + region + %dd freshness filter: %d roles",
                 MAX_AGE_DAYS, len(matches))

        # Dedupe against state — we keep this so a posting that was in
        # yesterday's digest doesn't repeat in today's. The 3-day window only
        # acts as a safety net for missed runs.
        new_jobs: list[dict] = []
        for j in matches:
            if store.contains(j["id"]):
                continue
            new_jobs.append(j)

        # Console preview (always print so dry-run is informative).
        interns = sum(1 for j in new_jobs if is_internship(j["title"]))
        log.info("New today: %d internships", interns)
        for j in new_jobs:
            line = (f"  [{j.get('_label','?'):>10}]  {j['company']:<14}  "
                    f"|  {j['title']:<55}  |  {j['location']}")
            print(line.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8"))

        if dry_run:
            return 0

        if not new_jobs:
            today = datetime.now(timezone.utc).strftime("%a %d %b %Y")
            await send_text(
                session,
                bot_token=TELEGRAM_BOT_TOKEN,
                chat_id=TELEGRAM_CHAT_ID,
                text=f"No new matching internships found today ({today}).",
            )
            log.info("Nothing new — sent empty digest notification.")
            return 0

        # Append to the running Excel tracker (before send, so a Telegram
        # outage doesn't lose the log; the sheet dedupes by job id).
        try:
            from excel_tracker import append_jobs
            append_jobs(new_jobs, TRACKER_FILE)
        except Exception:
            log.exception("Excel tracker update failed (continuing).")

        sent = await send_digest(
            session,
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=TELEGRAM_CHAT_ID,
            jobs=new_jobs,
            max_age_days=MAX_AGE_DAYS,
        )
        log.info("Sent %d Telegram message(s) for %d roles.", sent, len(new_jobs))

        # Only mark as seen AFTER a successful send, so a transient Telegram
        # outage doesn't make us silently skip a digest.
        if sent > 0:
            for j in new_jobs:
                store.add(j["id"])
            store.save()

    return 0


async def cmd_digest_loop(*, use_browser: bool, use_jobspy: bool = False) -> int:
    interval = max(1.0, DIGEST_INTERVAL_HOURS) * 3600
    log.info("Digest loop: every %.1f hours.", DIGEST_INTERVAL_HOURS)
    while True:
        try:
            await cmd_digest(dry_run=False, use_browser=use_browser,
                             use_jobspy=use_jobspy)
        except Exception:
            log.exception("Digest run failed; will retry next interval.")
        await asyncio.sleep(interval)


# --- legacy per-posting mode --------------------------------------------
async def cmd_run_legacy(*, dry_run: bool, no_filter: bool,
                          use_browser: bool, use_jobspy: bool = False) -> int:
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID) and not dry_run:
        sys.exit("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing in .env "
                 "(or pass --dry-run)")

    store = SeenStore(STATE_FILE)
    log.info("Legacy run: %d wired companies, %d ids in state",
             len(supported_companies()), len(store))

    async with aiohttp.ClientSession() as session:
        all_jobs = await _fetch_all(session, use_browser=use_browser,
                                    use_jobspy=use_jobspy)
        matches = all_jobs if no_filter else _filter_jobs(all_jobs)
        log.info("Filter pass: %d roles", len(matches))

        new_count = 0
        for job in matches:
            jid = job["id"]
            if store.contains(jid):
                continue
            store.add(jid)
            new_count += 1
            print(f"NEW  {job['company']}  |  {job['title']}  |  "
                  f"{job['location']}  |  {job['url']}")
            if not dry_run:
                await send_job(session, bot_token=TELEGRAM_BOT_TOKEN,
                               chat_id=TELEGRAM_CHAT_ID, job=job)
        store.save()
        log.info("New this run: %d", new_count)
    return 0


async def cmd_loop_legacy(*, use_browser: bool, use_jobspy: bool = False) -> int:
    log.info("Legacy loop: every %d seconds.", POLL_INTERVAL)
    while True:
        try:
            await cmd_run_legacy(dry_run=False, no_filter=False,
                                 use_browser=use_browser,
                                 use_jobspy=use_jobspy)
        except Exception:
            log.exception("Run failed; will retry next interval")
        await asyncio.sleep(POLL_INTERVAL)


def main() -> None:
    parser = argparse.ArgumentParser(description="India tech/SWE internship Telegram alerter.")
    parser.add_argument("--digest", action="store_true",
                        help="Send a grouped daily digest of new India tech/SWE roles "
                             "from the last MAX_AGE_DAYS days. RECOMMENDED.")
    parser.add_argument("--loop", action="store_true",
                        help="With --digest: re-run every DIGEST_INTERVAL_HOURS. "
                             "Without --digest: legacy per-posting polling every "
                             "POLL_INTERVAL_SECONDS.")
    parser.add_argument("--once", action="store_true",
                        help="(legacy) one per-posting polling pass.")
    parser.add_argument("--verify", action="store_true",
                        help="Hit every wired board, print which work.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run + filter, but DON'T send Telegram. Print to stdout.")
    parser.add_argument("--no-filter", action="store_true",
                        help="(legacy) skip every filter — dumps everything.")
    parser.add_argument("--browser", action="store_true",
                        help="Also fetch the auth-gated Workday tenants "
                             "(Cisco, Atlassian, ServiceNow, …) using a "
                             "real headless Chromium via Playwright. "
                             "Adds ~3-10s per tenant.")
    parser.add_argument("--jobspy", action="store_true",
                        help="Also fetch Google/Meta/Tesla/ASML/etc via "
                             "JobSpy (LinkedIn + Google Jobs scraping). "
                             "Adds ~10s per company; rate-limit prone.")
    args = parser.parse_args()

    use_browser = args.browser or USE_BROWSER
    use_jobspy = args.jobspy or USE_JOBSPY

    if args.verify:
        sys.exit(asyncio.run(cmd_verify(use_browser=use_browser)))

    if args.digest:
        if args.loop:
            sys.exit(asyncio.run(cmd_digest_loop(
                use_browser=use_browser, use_jobspy=use_jobspy)))
        sys.exit(asyncio.run(cmd_digest(dry_run=args.dry_run,
                                        use_browser=use_browser,
                                        use_jobspy=use_jobspy)))

    if args.loop:
        sys.exit(asyncio.run(cmd_loop_legacy(
            use_browser=use_browser, use_jobspy=use_jobspy)))
    sys.exit(asyncio.run(cmd_run_legacy(dry_run=args.dry_run,
                                        no_filter=args.no_filter,
                                        use_browser=use_browser,
                                        use_jobspy=use_jobspy)))


if __name__ == "__main__":
    main()
