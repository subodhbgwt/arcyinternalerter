# arcyinternalerter

Telegram alerter for **tech / SWE internships located anywhere in India**.

Same engine as `intern-alerter`: same ATS fetchers, same internship /
technical-role detection, same daily digest format, same state dedupe.
Three things are different:

1. **Geo gate is India, not the EU.** All 28 states + 8 union territories,
   ~250 cities from Bengaluru down to Tezpur, plus "Remote - India" /
   "Pan India" phrasings. No country exceptions for anyone.
2. **+120 Indian companies** on top of the inherited global catalog.
3. **Digest is grouped by Indian metro**, not by country.

Everything else is untouched, deliberately.

---

## What gets alerted

A posting is sent only if **all four** hold:

| Gate | Rule |
|---|---|
| Location | Anywhere in India (`filters.is_india_location`) |
| Function | Technical: SWE / ML / data / hardware / infra / security, plus product management |
| Not | HR, recruiting, admin, legal, finance, sales, marketing, support, solutions engineering, devrel, or any manager / director / lead title |
| Level | **Internship only.** Full-time roles, including junior and new-grad, are dropped |

Deliberately *not* treated as internships: **Graduate Engineer Trainee /
GET** and **Management Trainee**. Those are full-time entry roles in India,
and this alerter stays internship-only. "Industrial trainee", "student
trainee" and "summer trainee" *are* accepted.

### Location gate details

The gate needs a positive India hint (state, UT, city, `IND`, or a remote
phrasing), then rejects the posting if a *foreign* country is named and
"India" itself is not. That kills the three classic collisions:

- `Hyderabad, Sindh, Pakistan` -> rejected (Hyderabad also exists in Sindh)
- `Salem, OR, United States` -> rejected (Salem also exists in Tamil Nadu)
- `Lahore, Punjab, Pakistan` -> rejected (Punjab straddles the border)

`Indianapolis, Indiana` is rejected too, because matching is word-boundary
based: "India" never fires inside "Indiana".

The bare ISO-2 code `IN` is **not** accepted as a hint. It collides with the
English word "in" and with Indiana. `IND` is accepted.

---

## Digest layout

One grouped Telegram message per run, split into metro sections:

```
India tech / SWE internship digest - Mon 27 Jul 2026
7 new role(s) across 4 compan(ies), posted in the last 2 day(s).

==== BENGALURU (3) ====
--- Fi Money (2) ---
[Internship] AI Engg Intern
   Bangalore  ·  today  ·  apply
...
==== HYDERABAD (1) ====
==== DELHI NCR (2) ====
==== PUNE (1) ====
==== REST OF INDIA (0) ====
```

Sections, in fixed order: Bengaluru, Hyderabad, Delhi NCR, Mumbai, Pune,
Chennai, Rest of India. Empty ones are omitted. Bucketing is
first-match-wins, so a "Bengaluru / Pune" posting appears exactly once
(under Bengaluru). Anything outside the six metros (Kochi, Jaipur,
Bhubaneswar, Pan-India remote) lands in Rest of India.

---

## Companies

573 total, 531 wired to a working board.

| Group | Count | Notes |
|---|---|---|
| Inherited global catalog | 453 | Google, Microsoft, Amazon, NVIDIA, Stripe, Databricks, ... - their **India** postings now surface, since the geo gate changed |
| `INDIA` | 100 | The prestigious Indian tech list |
| `INDIA_CORE` | 20 | Conglomerates, banks, pharma, core engineering |

### The 100

IT services / ER&D (20), consumer internet (20), fintech (20), SaaS (20),
AI and analytics (11), space / defence / semis / EV (9).

TCS, Infosys, Wipro, HCLTech, Tech Mahindra, LTIMindtree, LTTS, Mphasis,
Persistent, Coforge, Hexaware, Cyient, KPIT, Tata Elxsi, Birlasoft, Sonata,
Happiest Minds, Zensar, Sasken, Newgen, Flipkart, Zomato, Swiggy, Meesho,
Myntra, Nykaa, BigBasket, Zepto, Blinkit, Urban Company, Udaan, Lenskart,
Delhivery, Ola, Ola Electric, Rapido, OYO, MakeMyTrip, ixigo, Info Edge,
Paytm, PhonePe, Razorpay, CRED, Zerodha, Groww, Pine Labs, Juspay, Cashfree,
slice, Navi, Fi Money, Jupiter, Zeta, M2P, Perfios, Policybazaar, Angel One,
NPCI, smallcase, Zoho, Freshworks, Dream11, BrowserStack, Chargebee, Hasura,
Druva, Icertis, Innovaccer, Darwinbox, Whatfix, MoEngage, CleverTap, Netcore,
Eightfold, Sprinklr, Amagi, Atlan, Zluri, Uniphore, Sarvam AI, Krutrim,
Fractal, Mu Sigma, Tiger Analytics, LatentView, Quantiphi, InMobi, Glance,
Observe.AI, Turing, Skyroot, Agnikul, Pixxel, Dhruva Space, Bellatrix,
ideaForge, Tonbo Imaging, Tata Electronics, Ather Energy.

Postman is Indian-founded and belongs in this tier, but it was already wired
in the inherited catalog, so its slot went to Dream11 rather than fetching
the same board twice.

`INDIA_CORE`: Reliance, Jio, L&T, Tata Motors, Mahindra, Bajaj Auto, Maruti
Suzuki, Adani, JSW, Godrej, Ultraviolette, Sun Pharma, Dr. Reddy's, Cipla,
Biocon, Serum Institute, HDFC Bank, ICICI Bank, Axis Bank, Kotak.

### How they are wired

**22 boards were live-probed on 2026-07-27** and returned real postings from
the real company. These run on every plain `--digest` pass, no flags:

| ATS | Companies |
|---|---|
| greenhouse | PhonePe, Groww, Druva, InMobi, Glance, Observe.AI, Turing |
| lever | Paytm, Meesho, CRED, Zeta, Fi Money |
| ashby | Sarvam AI, Atlan |
| smartrecruiters | Freshworks, Zomato, Swiggy, ixigo, Mphasis, Whatfix, Sprinklr |
| recruitee | Lenskart |

Four look-alike slugs were probed and **rejected** - they belong to unrelated
companies, and wiring them would have piped a foreign firm's jobs in under an
Indian name:

- `greenhouse:pine` -> a Toronto mortgage broker, not Pine Labs
- `ashby:navi` -> an SF startup, not Navi
- `greenhouse:slice` -> a North Macedonian company, not slice
- `ashby:tiger` -> an SF startup, not Tiger Analytics

The other 98 run on in-house portals, Workday, SAP SuccessFactors, Darwinbox
or Keka with no anonymous JSON endpoint, so they are wired to **jobspy**,
which reaches them through Google Jobs. That path is opt-in.

---

## Running it

```powershell
cd C:\Users\Ijtihed\Documents\GitHub\arcyinternalerter
pip install -r requirements.txt
Copy-Item .env.example .env    # then fill in the two values
python tracker.py --digest --dry-run
```

`--dry-run` prints matches to the console and sends nothing.

| Command | What it does |
|---|---|
| `python tracker.py --digest` | One digest, send, exit. This is the scheduled one. |
| `python tracker.py --digest --dry-run` | Same, print instead of send. |
| `python tracker.py --digest --loop` | Re-run every `DIGEST_INTERVAL_HOURS`. |
| `python tracker.py --digest --jobspy` | Also scrape the 134 jobspy companies. |
| `python tracker.py --verify` | Ping every wired board, print alive/dead. |
| `python tests/test_filters.py` | 71 offline filter assertions. |

### About `--jobspy`

It costs roughly 10s of scraping plus an 8s throttle **per company**, and
there are 134 of them, so a full jobspy pass takes ~30 minutes and can trip
LinkedIn rate limits. Keep it off the daily schedule; run it by hand when you
want the Infosys / Flipkart / Reliance tier swept.

### Scheduling

```powershell
.\setup_scheduled_task.ps1
```

Registers "arcyinternalerter daily digest" at 08:00, logging to
`logs\digest-YYYYMMDD.log`. No elevation needed.

---

## Config (`.env`)

| Key | Default | Meaning |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | - | from @BotFather |
| `TELEGRAM_CHAT_ID` | - | recipient's chat id, from `getUpdates` |
| `MAX_AGE_DAYS` | `2` | freshness window |
| `DIGEST_INTERVAL_HOURS` | `24` | only used with `--loop` |
| `INDIA_LOCATIONS` | - | extra comma-separated location tokens to accept |
| `INTERN_KEYWORDS` | - | extra comma-separated internship title tokens |
| `USE_JOBSPY` | off | same as `--jobspy` |
| `USE_BROWSER` | off | same as `--browser` (needs Playwright) |

`state.json` holds the ids already sent, so a posting is never repeated. It
is only written **after** a successful Telegram send, so an outage does not
silently swallow a digest.

---

## Files

| File | Role |
|---|---|
| `tracker.py` | entry point, fetch -> filter -> dedupe -> send |
| `companies.py` | the catalog, incl. `INDIA` and `INDIA_CORE` |
| `filters.py` | India geo gate, internship / technical detection, metro buckets |
| `ats.py` | one fetcher per ATS (Amazon and Apple query India server-side) |
| `jobspy_fetcher.py` | Google Jobs / LinkedIn fallback, region pinned to India |
| `notifier.py` | Telegram formatting, metro sections, 4000-char splitting |
| `state.py` | seen-id store |
