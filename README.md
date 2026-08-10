# arcyinternalerter

A personal internship radar. It scrapes company career boards for **quant, software, finance and consulting internships in Europe**, filters them down to the roles I'd actually apply to, and pushes matches to Telegram with an auto-updating Excel tracker.

It runs itself: a fast board digest every morning, a heavier LinkedIn/Google sweep once a week, both catching up automatically if the laptop was off.

---

## What gets alerted

A posting is sent only if **all four** hold:

| Gate | Rule |
|---|---|
| **Location** | A target region: Sweden + Nordics, Netherlands, UK, Switzerland, or the major EU financial/tech hubs (Dublin, Frankfurt, Paris, Amsterdam…), plus EU-remote. Collisions like "London, Ontario" are rejected. |
| **Track** | One of four: **quant/trading**, **software/tech/ML**, **investment banking/finance**, or **consulting**. |
| **Level** | Student programmes only: internships, off-cycle, spring weeks, insight days, summer analyst, campus/early-career and graduate schemes. Full-time senior roles are dropped. |
| **Freshness** | Posted within the last `MAX_AGE_DAYS` days. |

The role filter knows the branded early-career programmes too (Jane Street SEE/FTTP/INSIGHT, IMC Launchpad, SIG Discovery Day, spring insight, externships, and so on), not just the word "intern".

---

## Where the roles come from

- **Public ATS APIs** — Greenhouse, Lever, Ashby, SmartRecruiters and Workday boards, hit directly. This covers the prop shops (Jane Street, IMC, HRT, Optiver, Two Sigma, DRW, Citadel, G-Research, Five Rings…) and a large catalog of EU tech firms.
- **Bulge-bracket banks, scraped from their own Workday boards** — Deutsche Bank, Morgan Stanley, Barclays and Citi, filtered server-side to student roles so the handful of internships surface out of 700–2000 postings.
- **Jane Street's events board** — wired with a "trust" flag so every early-career event flows through, filtered only by region.
- **JobSpy fallback** (`--jobspy`) — LinkedIn/Google Jobs for firms with no public board (banks and MBB), each searching its own function (banks → "analyst", consulting → "consultant") in its own regions.

## The digest

One grouped Telegram message per run, split into city sections:

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

Empty sections are omitted; each role appears once. `state.json` dedupes so a posting is never sent twice.

## Excel tracker + application factory

- Every new role is appended to **`job_tracker.xlsx`** — Date, Company, Role, Location, Type, Track, Status (a dropdown: New → Interested → Applied → …), a clickable link, and Notes. Deduped by job id; your Status/Notes edits are never overwritten.
- Mark a row **Interested** and `python apply_factory.py` prepares a review-gated packet per role under `applications/`: the right CV variant, an apply checklist, and a cover-letter stub. It never submits anything — you review and apply yourself.

---

## Running it

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env    # then fill in the two Telegram values
python tracker.py --digest --dry-run
```

`--dry-run` prints matches to the console and sends nothing.

| Command | What it does |
|---|---|
| `python tracker.py --digest` | One digest, send, exit. The scheduled one. |
| `python tracker.py --digest --dry-run` | Same, print instead of send. |
| `python tracker.py --digest --jobspy` | Also sweep the banks/MBB via LinkedIn/Google (slow). |
| `python tracker.py --verify` | Ping every wired board, print alive/dead. |
| `python apply_factory.py` | Prepare application packets for rows marked "Interested". |

### Scheduling

```powershell
.\setup_scheduled_task.ps1
```

Registers two Windows tasks that call `run_digest.cmd` / `run_jobspy.cmd`:
a daily board digest at 08:00 and a weekly jobspy sweep on Mondays at 07:00. Both use `StartWhenAvailable`, so a run missed while the laptop was off fires as soon as it's next turned on.

## Config (`.env`)

| Key | Default | Meaning |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | from @BotFather |
| `TELEGRAM_CHAT_ID` | — | recipient's chat id, from `getUpdates` |
| `MAX_AGE_DAYS` | `2` | freshness window |
| `DIGEST_INTERVAL_HOURS` | `24` | only used with `--loop` |
| `EXTRA_LOCATIONS` | — | extra comma-separated location tokens to accept |
| `USE_JOBSPY` | off | same as `--jobspy` |

---

## Files

| File | Role |
|---|---|
| `tracker.py` | entry point: fetch → filter → dedupe → send → log |
| `filters.py` | region gate, four-track role filter, internship/early-career detection, city buckets |
| `companies.py` | the catalog (prop shops, EU tech, banks via Workday, jobspy finance/MBB) |
| `ats.py` | one fetcher per ATS (Greenhouse/Lever/Ashby/SmartRecruiters/Workday/…) |
| `jobspy_fetcher.py` | LinkedIn/Google Jobs fallback, per-firm search terms + regions |
| `notifier.py` | Telegram formatting, per-city sections, 4000-char splitting |
| `excel_tracker.py` | appends new roles to `job_tracker.xlsx` |
| `apply_factory.py` | builds review-gated application packets from "Interested" rows |
| `state.py` | seen-id store |

---

Forked from [Ijtihed/arcyinternalerter](https://github.com/Ijtihed/arcyinternalerter) and retargeted from its original India/tech scope to a European quant/SWE/finance/consulting search.
