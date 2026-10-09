# arcyinternalerter

My internship radar. It checks company career boards for quant, software, finance and consulting internships in Europe, keeps the ones I'd actually apply to, sends them to me on Telegram and logs them in an Excel sheet.

It runs on its own: a quick check of the boards every morning, and a slower LinkedIn and Google sweep once a week. If the laptop was off, both catch up the next time it's on.

Forked from [Ijtihed/arcyinternalerter](https://github.com/Ijtihed/arcyinternalerter), which was built for India and tech roles. I changed the targeting, the sources and the filters for a European search.

## What gets through

A posting is only sent if it passes all four checks:

| Check | Rule |
|---|---|
| Location | Sweden and the Nordics, the Netherlands, the UK, Switzerland, or one of the big EU finance and tech cities (Dublin, Frankfurt, Paris and so on), plus remote within the EU. Lookalikes such as "London, Ontario" are filtered out. |
| Track | Quant/trading, software/tech/ML, investment banking/finance, or consulting. |
| Level | Student roles only: internships, off-cycle, spring weeks, insight days, summer analyst, early-careers and graduate schemes. Senior full-time roles are dropped. |
| Age | Posted within the last `MAX_AGE_DAYS` days. |

It also recognises the branded student programmes that don't say "intern" in the title, like Jane Street SEE, FTTP and INSIGHT, IMC Launchpad, SIG Discovery Day, BCG's Visiting Associate role and externships.

## Where the roles come from

- Public ATS APIs: Greenhouse, Lever, Ashby, SmartRecruiters and Workday. That covers the prop shops (Jane Street, IMC, HRT, Optiver, Two Sigma, DRW, Citadel, G-Research, Five Rings and others) plus a long list of European tech companies.
- The banks' own Workday boards: Deutsche Bank, Morgan Stanley, Barclays and Citi. The search is narrowed to student roles on their side, so the few internships aren't buried among 700 to 2000 postings.
- Jane Street's events board, marked as trusted, so every student event comes through and only the location filter applies.
- JobSpy (`--jobspy`) for firms without a public board, mainly banks and the consulting firms. It searches LinkedIn and Google Jobs with a search term and set of regions per firm, such as "analyst" for banks and "consultant" for consulting.

## The Telegram message

One message per run, grouped by city:

```
🎯 Internship digest — Wed 05 Aug 2026
7 new role(s) across 5 compan(ies), posted in the last 2 day(s).

════ 🏙 STOCKHOLM ════
════ ❄️ NORDICS ════
════ 🌷 AMSTERDAM / NL ════
════ 🎡 LONDON / UK ════
════ ⛰ ZURICH / CH ════
════ 🇪🇺 REST OF EUROPE ════
```

Empty sections are left out and each role only shows up once. `state.json` keeps track of what has already been sent.

## Excel tracker and application packets

New roles are added to `job_tracker.xlsx` with the date, company, role, location, type, track, a link, notes and a status dropdown (New, Interested, Applied and so on). Rows are matched on job id, so anything you've typed in Status or Notes is never overwritten.

When you mark a row as Interested, `python apply_factory.py` makes a folder for it under `applications/` with the right CV, a checklist and a cover letter draft. It doesn't apply to anything. That part is still up to you.

## Running it

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env    # add your Telegram bot token and chat id
python tracker.py --digest --dry-run
```

`--dry-run` prints the matches instead of sending them.

| Command | What it does |
|---|---|
| `python tracker.py --digest` | Check the boards, send one message, exit. This is the scheduled one. |
| `python tracker.py --digest --dry-run` | Same, but prints instead of sending. |
| `python tracker.py --digest --jobspy` | Also searches LinkedIn and Google for the banks and consulting firms. Slow. |
| `python tracker.py --verify` | Checks every board and says whether it's reachable. |
| `python apply_factory.py` | Makes application folders for rows marked Interested. |

### Scheduling

```powershell
.\setup_scheduled_task.ps1
```

This sets up two Windows tasks: the board check every day at 08:00 (`run_digest.cmd`) and the JobSpy sweep on Mondays at 07:00 (`run_jobspy.cmd`). Both use `StartWhenAvailable`, so a run that was missed while the laptop was off happens as soon as it's turned on again.

## Settings (`.env`)

| Key | Default | Meaning |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | none | from @BotFather |
| `TELEGRAM_CHAT_ID` | none | your chat id, from `getUpdates` |
| `MAX_AGE_DAYS` | `2` | how old a posting can be |
| `DIGEST_INTERVAL_HOURS` | `24` | only used with `--loop` |
| `EXTRA_LOCATIONS` | none | extra comma-separated places to accept |
| `USE_JOBSPY` | off | same as `--jobspy` |

## Files

| File | What it does |
|---|---|
| `tracker.py` | entry point: fetch, filter, skip what's been sent, send, log |
| `filters.py` | location, track and student-role checks, plus the city grouping |
| `companies.py` | the list of companies and where to find their jobs |
| `ats.py` | one fetcher per job board system |
| `jobspy_fetcher.py` | the LinkedIn and Google Jobs search |
| `notifier.py` | formats the Telegram message and splits it at 4000 characters |
| `excel_tracker.py` | adds new roles to `job_tracker.xlsx` |
| `apply_factory.py` | builds the application folders |
| `state.py` | remembers which postings have been sent |
