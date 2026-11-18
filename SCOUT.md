# Weekly scout: events, MBB and spring weeks

The daily digest only sees job boards with an API. MBB, the Swedish banks'
student pages, networking events and UK spring weeks live on pages without
one, so a scheduled Claude task reads them once or twice a week and adds what's
new with `scout_add.py`.

## Who it's for

Subodh, KTH (BSc CS 2024–27, then MSc Applied & Computational Mathematics
2027–29, final graduation Jun 2029). Based in Stockholm. He's
targeting MBB and strategy consulting first, then quant, data science / ML and
tech. Networking events count as much as applications. Classic IB, M&A and
PE are skipped: in Sweden they recruit almost only from SSE. Markets, quant,
risk and XVA roles at banks are still in.

Keep: events, case nights, dinners, insight days, weekends, mentorship and
talent programmes (BCG Emeralds, Bain Buddy, McKinsey weekends and so on),
internships, off-cycle roles, spring weeks and insight weeks. Stockholm events
first, then the rest of the Nordics, then London / EU spring weeks.

Skip: anything only for SSE students (unless it also says KTH or "all
universities"), graduate schemes, full-time roles, events that have already
happened, and anything with a deadline that has passed.

## Sources

Consulting (check every run):
- McKinsey Sweden upcoming events: https://www.mckinsey.com/se/careers/upcoming-events
- McKinsey Sweden internships: https://www.mckinsey.com/se/careers/internship-opportunities
- BCG Sweden (events, Emeralds, +You): https://careers.bcg.com/locations/sweden
- BCG Platinion events: https://www.bcgplatinion.com/careers/events
- Bain recruiting events (filter Stockholm / Nordics): https://www.bain.com/careers/work-with-us/recruiting-events/
- Bain on your campus (KTH): https://careers.bain.com/bainonyourcampus/SchoolDetails
- Also search the web for: Kearney, Roland Berger, Oliver Wyman, EY-Parthenon,
  Strategy& (PwC), Arthur D. Little, Implement, Simon-Kucher, Accenture
  Strategy "Stockholm student event" / "case evening" / "internship".

Student associations that post firm events:
- SASSE events (SSE, check whether KTH students can join): https://www.sasse.se/events/
- KTH / THS: search "THS Armada events", "KTH case night", "KTH Business
  Society" and the Datasektionen calendar for firm events.

Quant and markets (Sweden):
- SEB CIB (XVA, fixed income quant, markets), Nordea Markets, Handelsbanken
  Capital Markets, Swedbank: student and internship pages.
- Lynx Asset Management, Wincent, Brummer & Partners, Nasdaq, AP1/AP2/AP3/AP4/AP7,
  Kidbrooke: internships, events, hackathons.
- Search "quant internship Stockholm 2027", "kvantitativ praktik".

Quant (Europe): events and insight days that the boards miss, such as Optiver,
IMC, Jane Street, Citadel, G-Research, SIG, Flow Traders, Maven and Squarepoint
(Amsterdam / London / Zurich). Also trading challenges, estimathons and quant
hackathons open to KTH students.

Data science / ML:
- Spotify, King, Klarna, Ericsson Research, Peltarion-type AI labs, SEB/Nordea
  data science: student events and summer internships.
- Hackathons and AI events in Stockholm (KTH AI Society, THS, Stockholm AI)
  with firm sponsors.

Spring weeks / insight (UK and EU):
- https://app.the-trackr.com/uk-finance/spring-weeks
- https://www.fe.training/free-resources/investment-banking/investment-banking-spring-weeks-open-applications/
- Quant list: https://github.com/northwesternfintech/2027QuantInternships
- Goldman Sachs, J.P. Morgan, Morgan Stanley, BofA, Citi, Barclays, UBS,
  Deutsche Bank early-careers pages. At banks, prefer markets, quant,
  engineering and technology spring weeks over IBD-only ones.

## Programme watchlist (flag the day they open)

These are the ones he asked to be told about. When one of them opens, add it
as a find with type "Programme" (or "Internship") and start the note with
"OPENED:" so it stands out in the Telegram message.

- EY Sweden: Consulting Summer Internship, Talent Training, Aster (with
  EY-Parthenon). Expected December 2026.
- Ericsson summer internship 2027, Business & Operations track (1 Dec 2026 –
  24 Jan 2027). Also Ericsson SPP associate consultant intern (opens ~Sep).
- BCG Emeralds, BCG +You and any BCG Sweden student programme or event.
- McKinsey Sweden BA internship (second deadline around 5 Feb 2027), McKinsey
  student weekends and programmes.
- Bain Buddy / Bain Nordics student events and the next AC intern cycle.
- If Insurance analyst summer internship (Jan–Feb 2027).
- Swedbank Robur: he heard (Nov 2026) that Robur may take in 10–12 students
  soon (student programme, internships or part-time). Check every run:
  https://jobs.swedbank.com (Teamtailor) and https://www.swedbank.com/work-with-us/students-and-graduates.html. Last year the Robur Summer Internship (8 weeks, Jun–Jul) closed 16 Jan 2026, so expect the 2027 round Dec–Jan. Job list
  (search "Robur", "student", "praktik", "sommarjobb", "trainee") and
  LinkedIn "Swedbank Robur student". Flag anything new as OPENED.
- From the INDEK internship catalogue (next cycles mostly open Aug–Oct 2027):
  Arkwright, Applied Value, OPX Partners, Roland Berger, Ericsson SPP,
  Kearney, Oliver Wyman, Strategy&, Accenture Strategy, Visma (Sweden 2028
  cycle). Flag any new student event from these firms too.

## Procedure

1. Read `scout_seen.json` (links already sent) so you don't redo work.
2. Check every source above. Read the firm's own page wherever you can, and
   don't trust a third-party date unless the firm's page confirms it.
3. For each find, record company, title, type (Event / Spring week / Insight /
   Internship), location, event date (`when`), application deadline, the link
   from the firm's own page, and a short note on eligibility.
4. Write the list to `scout_finds.json` in this folder, then run
   `python scout_add.py scout_finds.json`. That adds new rows to
   `job_tracker.xlsx` and sends one Telegram message. Links already in
   `scout_seen.json` are skipped.
5. Finish with a short summary: what's new, and anything with a deadline in
   the next 7 days at the top.

Never sign up or apply for anything yourself. Finding things is the whole job.
