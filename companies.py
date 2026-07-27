"""Companies to watch, with their public ATS slug if they have one.

Each entry is:
    {"name": "...",
     "ats":   "greenhouse|lever|ashby|smartrecruiters|workday|amazon|github|None",
     "slug":  "...",
     "country": "..."}

Slugs were live-verified at build time by hitting each company's public ATS
endpoint and confirming a non-empty `jobs` array.

Slug formats per ATS:
    greenhouse        boards.greenhouse.io/<slug>             -> "<slug>"
    lever             jobs.lever.co/<slug>                    -> "<slug>"
    ashby             jobs.ashbyhq.com/<slug>                 -> "<slug>"
    smartrecruiters   jobs.smartrecruiters.com/<Slug>         -> "<Slug>"   (case-sensitive)
    workday           {tenant}.wd{N}.myworkdayjobs.com/.../<site>
                                                              -> "<tenant>/<N>/<site>"
    amazon            (slug ignored; always EU country filter)
    github            (slug ignored)

Supported ATS keys:
    greenhouse, lever, ashby, smartrecruiters, workday, workday_browser,
    amazon, github, microsoft, workable, supercell, iqm, apple, amd,
    teamtailor, snap, netflix, jobspy, recruitee, phenom

Companies with `ats=None` either:
  - need CSRF / Bearer auth (Google, Meta — CSRF-protected JSON APIs),
  - run on SAP SuccessFactors (Roche, Novartis, ABB, Nestlé, Bosch, Kone…),
  - run on Workday tenants that gate behind login or unknown slugs
    (Cisco, AMD, Atlassian, Snowflake, Oracle, Broadcom, Samsung, Nokia,
    DJI, ASML, Vaisala, UBS, Swiss Re, Zurich Insurance, Swisscom…),
  - use iCIMS (Ubisoft),
  - use TeamTailor / Workable / custom client-side pages without a
    usable JSON endpoint (ICEYE, Aiven, RELEX, Varjo, Klarna, Bolt,
    Celonis, Revolut, Proton, CD Projekt, Rockstar, many gaming studios).

For those, the tracker just skips them. To add scraping later, write a
fetcher in ats.py and reference it here.

Run `python tracker.py --verify` after first install to confirm every wired
slug still returns jobs.
"""

# --- Global top-80 prestige list ------------------------------------------
GLOBAL = [
    {"name": "OpenAI",            "ats": "ashby",           "slug": "openai"},
    {"name": "NVIDIA",            "ats": "workday",         "slug": "nvidia/5/NVIDIAExternalCareerSite"},
    {"name": "Google",            "ats": "jobspy",          "slug": "1441"},
    {"name": "Apple",             "ats": "apple",           "slug": "apple"},   # server-rendered HTML, EU country filter
    {"name": "Microsoft",         "ats": "microsoft",       "slug": "microsoft"},  # apply.careers.microsoft.com/api/pcsx
    {"name": "Meta",              "ats": "jobspy",          "slug": "10667"},
    {"name": "SpaceX",            "ats": "greenhouse",      "slug": "spacex"},
    {"name": "Anthropic",         "ats": "greenhouse",      "slug": "anthropic"},
    {"name": "Amazon",            "ats": "amazon",          "slug": "amazon"},  # amazon.jobs EU search
    {"name": "Stripe",            "ats": "greenhouse",      "slug": "stripe"},
    {"name": "Databricks",        "ats": "greenhouse",      "slug": "databricks"},
    {"name": "Tesla",             "ats": "jobspy",          "slug": "15564"},
    {"name": "ByteDance",         "ats": "jobspy",          "slug": "10810658"},
    {"name": "TSMC",              "ats": None,              "slug": None},
    {"name": "ASML",              "ats": "jobspy",          "slug": "4287"},
    {"name": "Palantir",          "ats": "lever",           "slug": "palantir"},
    {"name": "Netflix",           "ats": "netflix",         "slug": "netflix"},
    {"name": "Samsung Electronics","ats": "jobspy",         "slug": "1186"},
    {"name": "Tencent",           "ats": None,              "slug": None},
    {"name": "Alibaba",           "ats": None,              "slug": None},
    {"name": "Huawei",            "ats": None,              "slug": None},
    {"name": "Uber",              "ats": "jobspy",          "slug": "1815218"},
    {"name": "Airbnb",            "ats": "greenhouse",      "slug": "airbnb"},
    {"name": "Cloudflare",        "ats": "greenhouse",      "slug": "cloudflare"},
    {"name": "Snowflake",         "ats": "ashby",           "slug": "snowflake"},
    {"name": "Anduril",           "ats": "greenhouse",      "slug": "andurilindustries"},
    {"name": "xAI",               "ats": "greenhouse",      "slug": "xai"},
    {"name": "Waymo",             "ats": "greenhouse",      "slug": "waymo"},
    {"name": "CoreWeave",         "ats": "greenhouse",      "slug": "coreweave"},
    {"name": "Figma",             "ats": "greenhouse",      "slug": "figma"},
    {"name": "Canva",             "ats": "smartrecruiters", "slug": "Canva"},
    {"name": "Perplexity",        "ats": "ashby",           "slug": "perplexity"},
    {"name": "Mistral AI",        "ats": "lever",           "slug": "mistral"},
    {"name": "Hugging Face",      "ats": "workable",        "slug": "huggingface"},
    {"name": "Cursor (Anysphere)","ats": "ashby",           "slug": "cursor"},
    {"name": "Scale AI",          "ats": "greenhouse",      "slug": "scaleai"},
    {"name": "ElevenLabs",        "ats": "ashby",           "slug": "elevenlabs"},
    {"name": "Neuralink",         "ats": None,              "slug": None},      # custom
    {"name": "Figure AI",         "ats": "greenhouse",      "slug": "figure"},
    {"name": "Midjourney",        "ats": None,              "slug": None},      # custom
    {"name": "Runway",            "ats": "ashby",           "slug": "runway"},
    {"name": "Vercel",            "ats": "greenhouse",      "slug": "vercel"},
    {"name": "GitHub",            "ats": "github",          "slug": "github"},
    {"name": "DJI",               "ats": None,              "slug": None},
    {"name": "Salesforce",        "ats": "workday",         "slug": "salesforce/12/External_Career_Site"},
    {"name": "Adobe",             "ats": "workday",         "slug": "adobe/5/external_experienced"},
    # Workday tenants that gate the search API behind AWS Cognito. Only
    # polled when USE_BROWSER=1 / --browser (Playwright loads the SPA so it
    # bootstraps auth, then we intercept its own XHR response).
    {"name": "Oracle",            "ats": "jobspy",          "slug": "1028"},
    {"name": "ServiceNow",        "ats": "jobspy",          "slug": "14375"},
    {"name": "AMD",               "ats": "amd",             "slug": "amd"},
    {"name": "Arm",               "ats": "jobspy",          "slug": "1666",             "country": "UK"},
    {"name": "Broadcom",          "ats": "jobspy",          "slug": "10612"},
    {"name": "Qualcomm",          "ats": "jobspy",          "slug": "1602"},
    {"name": "Intel",             "ats": "jobspy",          "slug": "1053"},
    {"name": "Cisco",             "ats": "jobspy",          "slug": "1063"},
    {"name": "Shopify",           "ats": None,              "slug": None},      # fully custom portal
    {"name": "Spotify",           "ats": "lever",           "slug": "spotify"},
    {"name": "Coinbase",          "ats": "jobspy",          "slug": "6622162"},
    {"name": "Revolut",           "ats": None,              "slug": None},      # custom ATS
    {"name": "Wise",              "ats": "smartrecruiters", "slug": "Wise"},
    {"name": "Adyen",             "ats": "greenhouse",      "slug": "adyen"},
    {"name": "Roblox",            "ats": "greenhouse",      "slug": "roblox"},
    {"name": "Epic Games",        "ats": "workday",         "slug": "epicgames/5/Epic_Games"},
    {"name": "Valve",             "ats": None,              "slug": None},      # custom
    {"name": "Riot Games",        "ats": "greenhouse",      "slug": "riotgamesinc"},
    {"name": "Discord",           "ats": "greenhouse",      "slug": "discord"},
    {"name": "Reddit",            "ats": "greenhouse",      "slug": "reddit"},
    {"name": "Snap",              "ats": "snap",            "slug": "snap"},
    {"name": "Duolingo",          "ats": "greenhouse",      "slug": "duolingo"},
    {"name": "Atlassian",         "ats": "jobspy",          "slug": "21629"},
    {"name": "GitLab",            "ats": "greenhouse",      "slug": "gitlab"},
    {"name": "Datadog",           "ats": "greenhouse",      "slug": "datadog"},
    {"name": "CrowdStrike",       "ats": "workday",         "slug": "crowdstrike/5/crowdstrikecareers"},
    {"name": "Wiz",               "ats": "greenhouse",      "slug": "wizinc"},
    # --- Quant / HFT (global prestige tier) ---
    {"name": "Citadel",               "ats": "jobspy",      "slug": "11116"},
    {"name": "Citadel Securities",    "ats": "jobspy",      "slug": "3128648"},
    {"name": "Two Sigma",             "ats": "jobspy",      "slug": "21089"},
    {"name": "DE Shaw",               "ats": None,          "slug": None},
    {"name": "Optiver",               "ats": "greenhouse",  "slug": "optiver"},
    {"name": "SIG",                   "ats": "jobspy",      "slug": "8780"},
    {"name": "G-Research",            "ats": "jobspy",      "slug": "10090",   "country": "UK"},
    {"name": "DRW",                   "ats": "jobspy",      "slug": "9265"},
    {"name": "Hudson River Trading",  "ats": "greenhouse",  "slug": "wehrtyou"},        # internal codename slug, verified
    {"name": "Old Mission Capital",   "ats": "greenhouse",  "slug": "oldmissioncapital"},
    {"name": "Five Rings",            "ats": "greenhouse",  "slug": "fiveringsllc"},
    {"name": "Radix Trading",         "ats": "greenhouse",  "slug": "radixexperienced"},
    {"name": "Virtu Financial",       "ats": "greenhouse",  "slug": "virtu"},
    # --- Gaming (globally iconic) ---
    {"name": "Mojang Studios",        "ats": "greenhouse",  "slug": "mojangab"},         # Minecraft studio
    {"name": "Bungie",                "ats": "greenhouse",  "slug": "bungie"},
    {"name": "Electronic Arts",       "ats": "jobspy",      "slug": "1271"},
    {"name": "CD Projekt Red",        "ats": "smartrecruiters","slug": "CDPROJEKTRED",  "country": "PL"},
    {"name": "Ubisoft",               "ats": "smartrecruiters","slug": "ubisoft2",      "country": "FR"},
    {"name": "Rockstar Games",        "ats": "greenhouse",  "slug": "rockstargames"},
    {"name": "Nintendo",              "ats": "greenhouse",  "slug": "nintendo"},
    {"name": "Square Enix",           "ats": "workable",    "slug": "square-enix"},
    {"name": "Bandai Namco",          "ats": "greenhouse",  "slug": "bandainamco"},
    {"name": "SEGA",                  "ats": "workday",     "slug": "sega/3/SEGA_Careers"},
    {"name": "Capcom",                "ats": None,          "slug": None},               # Jobvite — not supported
    {"name": "Activision Blizzard",   "ats": None,          "slug": None},              # now Microsoft
    {"name": "IO Interactive",        "ats": "teamtailor",  "slug": "io-interactive.teamtailor.com", "country": "DK"},
    {"name": "Paradox Interactive",   "ats": "teamtailor",  "slug": "career.paradoxplaza.com","country": "SE"},
    # --- Enterprise software (iconic globally) ---
    {"name": "SAP",                   "ats": "jobspy",      "slug": "1115",     "country": "DE"},
    {"name": "IBM",                   "ats": "jobspy",      "slug": "1009"},
    {"name": "Siemens",               "ats": "jobspy",      "slug": "1043",     "country": "DE"},
    {"name": "Bosch",                 "ats": "smartrecruiters","slug": "BoschGroup",   "country": "DE"},
    {"name": "Ericsson",              "ats": "jobspy",      "slug": "5765",     "country": "SE"},
    {"name": "HP",                    "ats": "workday",     "slug": "hp/5/ExternalCareerSite"},
    {"name": "Dell Technologies",     "ats": "workday",     "slug": "dell/1/External"},
    # --- Defense / aerospace (prestigious SWE roles) ---
    {"name": "Shield AI",             "ats": "lever",       "slug": "shieldai"},
    {"name": "Hermeus",               "ats": None,          "slug": None},               # closed board
    {"name": "Relativity Space",      "ats": "greenhouse",  "slug": "relativity"},
    {"name": "Joby Aviation",         "ats": None,          "slug": None},               # closed board
    {"name": "L3Harris",              "ats": None,          "slug": None},               # SAP SF
    {"name": "Northrop Grumman",      "ats": "workday",     "slug": "ngc/1/Northrop_Grumman_External_Site"},
    {"name": "BAE Systems",           "ats": None,          "slug": None,       "country": "UK"},  # IBM Kenexa
    # --- More frontier AI ---
    {"name": "DeepMind",              "ats": "greenhouse",  "slug": "deepmind"},
    {"name": "Cognition AI",          "ats": "ashby",       "slug": "cognition"},        # Devin
    {"name": "Magic",                 "ats": "jobspy",      "slug": "73923174"},
    {"name": "Poolside",              "ats": "ashby",       "slug": "poolside"},
    {"name": "Together AI",           "ats": "greenhouse",  "slug": "togetherai"},
    {"name": "Reflection AI",         "ats": "ashby",       "slug": "reflectionai"},
    {"name": "Imbue",                 "ats": "ashby",       "slug": "imbue"},
    {"name": "Black Forest Labs",     "ats": "jobspy",      "slug": "99918823", "country": "DE"},  # FLUX models
    {"name": "Isomorphic Labs",       "ats": "greenhouse",  "slug": "isomorphiclabs", "country": "UK"},  # DeepMind spinout
    {"name": "MongoDB",           "ats": "greenhouse",      "slug": "mongodb"},
    {"name": "Confluent",         "ats": "jobspy",          "slug": "11250374"},
    {"name": "Elastic",           "ats": "greenhouse",      "slug": "elastic"},
    {"name": "Notion",            "ats": "ashby",           "slug": "notion"},
    {"name": "Linear",            "ats": "ashby",           "slug": "linear"},
    {"name": "Ramp",              "ats": "ashby",           "slug": "ramp"},
    {"name": "Rippling",          "ats": None,              "slug": None},      # custom / Workday
    # --- prestigerank.com cross-check: prestigious gaps, slugs live-verified ---
    {"name": "Box",               "ats": "greenhouse",      "slug": "boxinc"},               # 294 jobs
    {"name": "Nuro",              "ats": "greenhouse",      "slug": "nuro"},                 # 792 jobs
    {"name": "Toast",             "ats": "greenhouse",      "slug": "toast"},                # 548 jobs
    {"name": "JetBrains",         "ats": "greenhouse",      "slug": "jetbrains"},            # 312 jobs
    {"name": "Klaviyo",           "ats": "greenhouse",      "slug": "klaviyo"},              # 169 jobs
    {"name": "Postman",           "ats": "greenhouse",      "slug": "postman"},              # 122 jobs
    {"name": "Temporal",          "ats": "greenhouse",      "slug": "temporaltechnologies"}, # 53 jobs
    {"name": "Thinking Machines Lab","ats": "greenhouse",   "slug": "thinkingmachines"},     # 32 jobs, Mira Murati lab
    {"name": "Character.AI",      "ats": "ashby",           "slug": "character"},            # 15 jobs
    {"name": "PlanetScale",       "ats": "greenhouse",      "slug": "planetscale"},          # 12 jobs
    {"name": "Netlify",           "ats": "greenhouse",      "slug": "netlify"},              # 2 jobs
    # Prestigious but no public ATS board (Workday/proprietary/stealth) -> unwired,
    # wire via jobspy LinkedIn-id later: LinkedIn, Blue Origin, Renaissance Technologies,
    # Cruise, Verily, Red Hat, VMware, Zoom, BlackRock, Capital One, Lockheed Martin,
    # Splunk, Micron, Marvell, Texas Instruments, Deel, Booking.com, Pixar, SSI.
]

# --- EU-biased add-ons from your follow-up --------------------------------
GLOBAL_EU_BIASED = [
    {"name": "Helsing",           "ats": "greenhouse",      "slug": "helsing",          "country": "DE"},
    {"name": "Celonis",           "ats": "greenhouse",      "slug": "celonis",           "country": "DE"},
    {"name": "Miro",              "ats": "greenhouse",      "slug": "realtimeboardglobal","country": "NL"},
    {"name": "Klarna",            "ats": "jobspy",          "slug": "11497",            "country": "SE"},
    {"name": "Bolt",              "ats": "greenhouse",      "slug": "boltv2",            "country": "EE"},
    {"name": "UiPath",            "ats": "jobspy",          "slug": "1623856",          "country": "RO"},
    {"name": "Lovable",           "ats": "ashby",           "slug": "lovable",          "country": "SE"},
    {"name": "Neko Health",       "ats": "ashby",           "slug": "neko-health",       "country": "SE"},
    {"name": "Synthesia",         "ats": "ashby",           "slug": "synthesia",        "country": "UK"},
    {"name": "Darktrace",         "ats": "workday",         "slug": "darktrace/3/DarktaceExternal","country": "UK"},  # note Darktrace's own typo
]

# --- Finland top list -----------------------------------------------------
# Most Finnish scaleups run on TeamTailor (auth-walled API) or their own ATS,
# so they're listed but not wired. Add an HTML scraper later if you really
# want IQM / RELEX / Varjo etc. piped through.
FINLAND = [
    {"name": "Supercell",            "ats": "supercell",       "slug": "supercell",        "country": "FI"},
    {"name": "Wolt",                 "ats": "greenhouse",      "slug": "wolt",             "country": "FI"},
    {"name": "Oura",                 "ats": "greenhouse",      "slug": "oura",             "country": "FI"},
    {"name": "Nokia",                "ats": "workday_browser", "slug": "Nokia",            "country": "FI"},
    {"name": "ICEYE",                "ats": "workable",        "slug": "iceye",             "country": "FI"},
    {"name": "IQM Quantum Computers","ats": "teamtailor",      "slug": "iqm.teamtailor.com","country": "FI"},
    {"name": "Aiven",                "ats": "greenhouse",      "slug": "eu:aiven36",        "country": "FI"},
    {"name": "RELEX Solutions",      "ats": None,              "slug": None,                "country": "FI"},  # JS-rendered careers.relexsolutions.com
    {"name": "Varjo",                "ats": "workable",        "slug": "varjo-1",           "country": "FI"},
    {"name": "Smartly.io",           "ats": "greenhouse",      "slug": "smartlyio",        "country": "FI"},
    {"name": "Silo AI / AMD Silo AI","ats": None,              "slug": None,                "country": "FI"},  # AMD Workday
    {"name": "Remedy Entertainment", "ats": None,              "slug": None,                "country": "FI"},  # custom
    {"name": "Rovio",                "ats": "lever",           "slug": "rovio-2",           "country": "FI"},
    {"name": "Bluefors",             "ats": "teamtailor",      "slug": "bluefors.teamtailor.com","country": "FI"},
    {"name": "Hoxhunt",              "ats": "ashby",           "slug": "hoxhunt",          "country": "FI"},
    {"name": "Swappie",              "ats": "teamtailor",      "slug": "careers.swappie.com","country": "FI"},
    {"name": "Metacore",             "ats": "greenhouse",      "slug": "metacore",          "country": "FI"},
    {"name": "Distance Technologies","ats": None,              "slug": None,                "country": "FI"},
    {"name": "ReOrbit",              "ats": "teamtailor",      "slug": "reorbit.teamtailor.com","country": "FI"},
    {"name": "Vaisala",              "ats": "workday_browser", "slug": "Vaisala",          "country": "FI"},
    # --- More Finnish tech / gaming ---
    {"name": "WithSecure",           "ats": None,              "slug": None,               "country": "FI"},  # F-Secure rebrand, cybersec
    {"name": "Gofore",               "ats": "lever",           "slug": "gofore",           "country": "FI"},  # Nasdaq Helsinki IT consultancy
    {"name": "Qt Group",             "ats": "greenhouse",      "slug": "theqtcompany",     "country": "FI"},
    {"name": "Fingersoft",           "ats": "teamtailor",      "slug": "careers.fingersoft.com","country": "FI"},
    {"name": "Small Giant Games",    "ats": "greenhouse",      "slug": "sggcareers",       "country": "FI"},  # Empires & Puzzles
    {"name": "Tietoevry",            "ats": "workday",         "slug": "tieto/3/Tieto_Careers_External_Site","country": "FI"},  # post-split entity
    {"name": "Kone",                 "ats": "workday",         "slug": "kone/3/Careers",   "country": "FI"},
    {"name": "Konecranes",           "ats": "smartrecruiters", "slug": "Konecranes",       "country": "FI"},  # industrial automation/IoT
    {"name": "Wärtsilä",             "ats": None,              "slug": None,               "country": "FI"},  # marine & energy tech
    {"name": "Vincit",               "ats": "teamtailor",      "slug": "vincitoyj.teamtailor.com",  "country": "FI"},
    {"name": "Reaktor",              "ats": "ashby",           "slug": "Reaktor",          "country": "FI"},
    {"name": "Futurice",             "ats": "greenhouse",      "slug": "futurice",         "country": "FI"},  # moved from Ashby
    {"name": "Solita",               "ats": "greenhouse",      "slug": "solita",           "country": "FI"},
    {"name": "SSH Communications",   "ats": None,              "slug": None,               "country": "FI"},
    # --- Gaming (new) ---
    {"name": "Housemarque",          "ats": "greenhouse",      "slug": "housemarque",      "country": "FI"},  # Sony PlayStation studio (Returnal)
    {"name": "Unity Technologies",   "ats": "greenhouse",      "slug": "unity3d",          "country": "FI"},  # game engine, 40+ Helsinki roles
    {"name": "Ubisoft Helsinki",     "ats": "smartrecruiters", "slug": "Ubisoft2",         "country": "FI"},  # AAA publisher Helsinki studio
    {"name": "Next Games",           "ats": "lever",           "slug": "nextgames",        "country": "FI"},  # Netflix-owned mobile game studio
    # --- SaaS / data (new) ---
    {"name": "Supermetrics",         "ats": "greenhouse",      "slug": "supermetricsoy",   "country": "FI"},  # marketing analytics SaaS, 140+ engineers
    {"name": "M-Files",              "ats": "workable",        "slug": "m-files",          "country": "FI"},  # document intelligence SaaS, Tampere
    {"name": "Mapbox",               "ats": "ashby",           "slug": "mapbox",           "country": "FI"},  # location tech, Helsinki engineering office
    {"name": "Sema4.ai",             "ats": "ashby",           "slug": "sema4.ai",         "country": "FI"},  # AI agent platform (formerly Robocorp)
    {"name": "Frends Technology",    "ats": "teamtailor",      "slug": "careers.frends.com","country": "FI"},  # integration platform SaaS, Gartner MQ
    # --- Cloud / infra / DevOps ---
    {"name": "UpCloud",              "ats": "teamtailor",      "slug": "upcloud.teamtailor.com","country": "FI"},  # Finnish cloud provider
    {"name": "Eficode",              "ats": "teamtailor",      "slug": "eficode.teamtailor.com","country": "FI"},  # DevOps/Atlassian consultancy
    # --- Fintech / payments ---
    {"name": "Enfuce",               "ats": "teamtailor",      "slug": "enfuceoy.teamtailor.com","country": "FI"},  # card issuing / payment processing
    # --- Consultancies ---
    {"name": "Siili Solutions",      "ats": "teamtailor",      "slug": "siili.teamtailor.com","country": "FI"},  # Nasdaq Helsinki IT consultancy
    {"name": "Innofactor",           "ats": "teamtailor",      "slug": "ura.innofactor.fi","country": "FI"},   # Microsoft cloud partner
    {"name": "Columbia Road",        "ats": "workable",        "slug": "columbia-road",    "country": "FI"},  # digital growth consultancy
    # --- Health / deep tech ---
    {"name": "Nightingale Health",   "ats": "teamtailor",      "slug": "nightingalehealth.teamtailor.com","country": "FI"},  # blood biomarker AI
]


# --- Switzerland tech & enterprise ----------------------------------------
# Enterprise giants use SAP SuccessFactors (not yet wired). Scaleups mostly
# on Greenhouse / Lever and are fully wired.
SWITZERLAND = [
    # Global enterprises headquartered in Switzerland
    {"name": "ABB",                  "ats": None,         "slug": None,                             "country": "CH"},  # Phenom People (complex tenant)
    {"name": "Roche",                "ats": "workday",    "slug": "roche/3/roche-ext",              "country": "CH"},
    {"name": "Novartis",             "ats": "workday",    "slug": "novartis/3/Novartis_Careers",    "country": "CH"},
    {"name": "Nestlé",               "ats": None,         "slug": None,                             "country": "CH"},  # Workday (verify tenant)
    {"name": "UBS",                  "ats": None,         "slug": None,                             "country": "CH"},  # proprietary TalentGate
    {"name": "Swiss Re",             "ats": None,         "slug": None,                             "country": "CH"},  # Workday
    {"name": "Zurich Insurance",     "ats": None,         "slug": None,                             "country": "CH"},  # Oracle Taleo
    {"name": "Swisscom",             "ats": "workday",    "slug": "swisscom/103/SwisscomExternalCareers","country": "CH"},
    {"name": "Logitech",             "ats": "workday",    "slug": "logitech/5/Logitech",            "country": "CH"},
    {"name": "Julius Baer",          "ats": "workday",    "slug": "juliusbaer/3/External",          "country": "CH"},
    {"name": "Hitachi Energy",       "ats": "workday",    "slug": "gtsgbu/3/Careers",          "country": "CH"},
    {"name": "Landis+Gyr",           "ats": None,         "slug": None,                        "country": "CH"},  # smart metering
    # Tech scaleups / AI
    {"name": "Scandit",              "ats": "greenhouse", "slug": "scandit",                   "country": "CH"},  # barcode + AR AI
    {"name": "Nexthink",             "ats": "smartrecruiters","slug": "nexthink",              "country": "CH"},  # DEX platform, Lausanne
    {"name": "GetYourGuide",         "ats": "greenhouse", "slug": "getyourguide",              "country": "CH"},  # travel, Zurich/Berlin
    {"name": "Beekeeper",            "ats": "greenhouse", "slug": "beekeeper",                 "country": "CH"},  # frontline workforce SaaS
    {"name": "Frontify",             "ats": "lever",      "slug": "frontify",                  "country": "CH"},  # brand mgmt, Basel — moved from Greenhouse
    {"name": "Yokoy",                "ats": "lever",      "slug": "yokoy",                     "country": "CH"},  # AI expense mgmt, Zurich — moved from Greenhouse
    {"name": "Sophia Genetics",      "ats": "workable",   "slug": "sophia-genetics",           "country": "CH"},  # AI genomics, Lausanne
    {"name": "Proton",               "ats": "greenhouse", "slug": "proton",                    "country": "CH"},  # ProtonMail / VPN, Geneva
    {"name": "Temenos",              "ats": "workday",    "slug": "temenos/103/Temenoscareers","country": "CH"},
    {"name": "u-blox",               "ats": None,         "slug": None,                        "country": "CH"},  # IoT / positioning chips
    {"name": "Sensirion",            "ats": "greenhouse", "slug": "sensirion",                 "country": "CH"},  # flow & env sensors, ETH-adjacent
    {"name": "Endress+Hauser",       "ats": None,         "slug": None,                        "country": "CH"},  # industrial IoT / measurement
    {"name": "Daedalean",            "ats": None,         "slug": None,                        "country": "CH"},  # avionics AI — board gone
    {"name": "Pricehubble",          "ats": "workable",   "slug": "pricehubble",               "country": "CH"},  # real-estate analytics — moved from Greenhouse
    {"name": "Unique Finance",       "ats": "ashby",      "slug": "unique",                    "country": "CH"},  # Swiss AI fintech
    # --- ETH / EPFL spin-offs & deep tech ---
    {"name": "ANYbotics",            "ats": "lever",      "slug": "anybotics",                 "country": "CH"},  # ETH spin-off, autonomous inspection robots
    {"name": "Gravis Robotics",      "ats": "lever",      "slug": "gravisrobotics",            "country": "CH"},  # ETH RSL spin-off, autonomous construction machinery
    {"name": "Zurich Instruments",   "ats": "lever",      "slug": "zurichinstruments",         "country": "CH"},  # quantum computing control systems, ETH-adjacent
    {"name": "Adaptyv Bio",          "ats": "ashby",      "slug": "adaptyv",                   "country": "CH"},  # EPFL spin-off, AI protein engineering + lab automation
    {"name": "Lakera AI",            "ats": "ashby",      "slug": "lakera.ai",                 "country": "CH"},  # LLM security / AI red-teaming, ETH-adjacent
    {"name": "LatticeFlow AI",       "ats": "greenhouse", "slug": "latticeflow",               "country": "CH"},  # ETH spin-off, trustworthy AI (slug unconfirmed)
    # --- Frontier AI (Zurich office) ---
    {"name": "Mistral AI",           "ats": "lever",      "slug": "mistral",                   "country": "CH"},  # frontier LLM, significant Zurich eng hub
    # --- Fintech / crypto ---
    {"name": "Avaloq",               "ats": "smartrecruiters", "slug": "Avaloq1",             "country": "CH"},  # core banking software, NEC subsidiary
    {"name": "Crealogix",            "ats": "smartrecruiters", "slug": "CREALOGIX",           "country": "CH"},  # digital banking SaaS
    {"name": "SwissBorg",            "ats": "lever",      "slug": "swissborg",                 "country": "CH"},  # crypto wealth management, Lausanne
    # --- AI / SaaS ---
    {"name": "Smallpdf",             "ats": "ashby",      "slug": "smallpdf",                  "country": "CH"},  # PDF SaaS, Zurich
    {"name": "DFINITY Foundation",   "ats": "greenhouse", "slug": "dfinity",                   "country": "CH"},  # ICP blockchain, 250 engineers, Zurich
    # --- Cybersecurity ---
    {"name": "xorlab",               "ats": "workable",   "slug": "xorlab",                    "country": "CH"},  # email security AI, ETH spin-off
    # --- Engineering consultancy ---
    {"name": "Zühlke Engineering",   "ats": "workday",    "slug": "zuehlke/3/Zuhlke-Careers", "country": "CH"},  # prestigious tech consultancy, Zurich
    # --- PropTech / fintech ---
    {"name": "MoneyPark",            "ats": "workable",   "slug": "moneypark",                 "country": "CH"},  # fintech mortgage advisory, Zurich
]


# --- Top EU scaleups actively hiring ----------------------------------------
# Companies that didn't fit global-prestige or country-specific buckets.
# Many verified on Greenhouse / Lever / Ashby; some still unwired (None).
EU_SCALEUPS = [
    # --- UK fintech / insurtech ---
    {"name": "Monese",               "ats": "lever",       "slug": "monese",            "country": "UK"},
    {"name": "Paysend",              "ats": "greenhouse",  "slug": "paysend",           "country": "UK"},
    {"name": "Modulr",               "ats": "greenhouse",  "slug": "modulr",            "country": "UK"},
    {"name": "ClearScore",           "ats": "greenhouse",  "slug": "clearscore",        "country": "UK"},
    {"name": "Cleo",                 "ats": "greenhouse",  "slug": "cleo",              "country": "UK"},
    {"name": "Tide",                 "ats": "greenhouse",  "slug": "tide",              "country": "UK"},
    {"name": "Pleo",                 "ats": "ashby",       "slug": "pleo",              "country": "DK"},
    {"name": "Lunar",                "ats": "greenhouse",  "slug": "lunar",             "country": "DK"},
    # --- French tech champions ---
    {"name": "Doctolib",             "ats": "greenhouse",  "slug": "doctolib",          "country": "FR"},
    {"name": "ContentSquare",        "ats": "lever",       "slug": "contentsquare",     "country": "FR"},
    {"name": "Mirakl",               "ats": "greenhouse",  "slug": "mirakl",            "country": "FR"},
    {"name": "Pennylane",            "ats": "ashby",       "slug": "pennylane",         "country": "FR"},
    {"name": "Spendesk",             "ats": "teamtailor",  "slug": "career.spendesk.com","country": "FR"},
    {"name": "Back Market",          "ats": "ashby",       "slug": "backmarket",        "country": "FR"},
    {"name": "Alan",                 "ats": "ashby",       "slug": "alan",              "country": "FR"},
    {"name": "Sorare",               "ats": "ashby",       "slug": "Sorare",            "country": "FR"},
    {"name": "Ledger",               "ats": "ashby",       "slug": "ledger",            "country": "FR"},
    {"name": "Shift Technology",     "ats": "greenhouse",  "slug": "shifttechnology",   "country": "FR"},
    {"name": "Ankorstore",           "ats": "ashby",       "slug": "ankorstore",        "country": "FR"},
    {"name": "Swile",                "ats": "lever",       "slug": "swile",             "country": "FR"},
    {"name": "Payfit",               "ats": "teamtailor",  "slug": "careers.payfit.com","country": "FR"},
    {"name": "Vestiaire Collective", "ats": "lever",       "slug": "vestiairecollective","country": "FR"},
    {"name": "Brevo",                "ats": "lever",       "slug": "brevo",             "country": "FR"},  # formerly Sendinblue
    {"name": "Deezer",               "ats": "smartrecruiters","slug": "deezer",          "country": "FR"},
    # --- DACH (DE / AT / CH) ---
    {"name": "Personio",             "ats": None,          "slug": None,               "country": "DE"},  # uses own product
    {"name": "Contentful",           "ats": "greenhouse",  "slug": "contentful",       "country": "DE"},
    {"name": "Taxfix",               "ats": "ashby",       "slug": "taxfix.com",       "country": "DE"},
    {"name": "Clark",                "ats": "greenhouse",  "slug": "clark",            "country": "DE"},
    {"name": "Mambu",                "ats": "lever",       "slug": "mambu",            "country": "DE"},
    {"name": "Cognigy",              "ats": "workable",    "slug": "cognigy",          "country": "DE"},
    {"name": "Parloa",               "ats": "greenhouse",  "slug": "parloa",           "country": "DE"},
    {"name": "Moss",                 "ats": "ashby",       "slug": "moss",             "country": "DE"},
    {"name": "Flink",                "ats": "smartrecruiters", "slug": "Flink3",       "country": "DE"},
    # HelloFresh already in EXTRAS
    {"name": "SumUp",                "ats": "greenhouse",  "slug": "sumup",            "country": "DE"},
    {"name": "Checkout.com",         "ats": "ashby",       "slug": "checkout.com",     "country": "UK"},
    # --- Benelux ---
    {"name": "Mollie",               "ats": "ashby",       "slug": "mollie",           "country": "NL"},
    {"name": "Picnic",               "ats": "greenhouse",  "slug": "picnicevents",     "country": "NL"},
    {"name": "Coolblue",             "ats": None,          "slug": None,               "country": "NL"},
    # --- Nordics ---
    {"name": "Kahoot!",              "ats": "workable",    "slug": "kahoot",           "country": "NO"},
    {"name": "Visma",                "ats": None,          "slug": None,               "country": "NO"},
    {"name": "Einride",              "ats": "lever",       "slug": "einride",          "country": "SE"},
    {"name": "Epidemic Sound",       "ats": "ashby",       "slug": "epidemic-sound",   "country": "SE"},
    # Spotify already in GLOBAL
    # --- Southern / Eastern EU ---
    {"name": "Delivery Hero",        "ats": "smartrecruiters", "slug": "DeliveryHero", "country": "DE"},
    {"name": "AUTO1 Group",          "ats": "greenhouse",  "slug": "auto1group",       "country": "DE"},
    {"name": "Scalable Capital",     "ats": "smartrecruiters", "slug": "ScalableGmbH", "country": "DE"},
    {"name": "Thought Machine",      "ats": "ashby",       "slug": "thought-machine",  "country": "UK"},
    {"name": "Starling Bank",        "ats": "workable",    "slug": "starling-bank",    "country": "UK"},
    {"name": "OakNorth",             "ats": "lever",       "slug": "oaknorth.ai",      "country": "UK"},
    {"name": "Zego",                 "ats": "workable",    "slug": "zego",             "country": "UK"},
    {"name": "Curve",                "ats": "greenhouse",  "slug": "curve",            "country": "UK"},
    {"name": "Soldo",                "ats": "greenhouse",  "slug": "soldo",            "country": "UK"},
    {"name": "ClearBank",            "ats": "greenhouse",  "slug": "clearbank",        "country": "UK"},
    {"name": "Yapily",               "ats": "greenhouse",  "slug": "yapily",           "country": "UK"},
    {"name": "Griffin",              "ats": "greenhouse",  "slug": "griffin",          "country": "UK"},
    {"name": "Uncapped",             "ats": "greenhouse",  "slug": "uncapped",         "country": "UK"},
]


# --- High-value extras (AI labs, fintech, robotics, EU scaleups) ----------
# Live-verified working as of build time.
EXTRAS = [
    # AI frontier labs
    {"name": "Cohere",            "ats": "ashby",           "slug": "cohere"},
    {"name": "Stability AI",      "ats": "greenhouse",      "slug": "stabilityai"},
    {"name": "Modal Labs",        "ats": "ashby",           "slug": "modal"},
    {"name": "Decagon",           "ats": "ashby",           "slug": "decagon"},
    {"name": "Sierra",            "ats": "ashby",           "slug": "sierra"},
    {"name": "Harvey",            "ats": "ashby",           "slug": "harvey"},
    {"name": "Glean",             "ats": "greenhouse",      "slug": "gleanwork"},
    {"name": "LangChain",         "ats": "ashby",           "slug": "langchain"},
    {"name": "Inflection AI",     "ats": "greenhouse",      "slug": "inflectionai"},
    {"name": "Liquid AI",         "ats": "ashby",           "slug": "liquid"},
    {"name": "Suno",              "ats": "ashby",           "slug": "suno"},
    {"name": "Speak",             "ats": "ashby",           "slug": "speak"},
    # AI / dev infra
    {"name": "Replit",            "ats": "ashby",           "slug": "replit"},
    {"name": "Vanta",             "ats": "ashby",           "slug": "vanta"},
    {"name": "PostHog",           "ats": "ashby",           "slug": "posthog"},
    {"name": "Browserbase",       "ats": "ashby",           "slug": "browserbase"},
    {"name": "Sourcegraph",       "ats": "greenhouse",      "slug": "sourcegraph91"},
    {"name": "Watershed",         "ats": "ashby",           "slug": "watershed"},
    {"name": "Resend",            "ats": "ashby",           "slug": "resend"},
    {"name": "Webflow",           "ats": "greenhouse",      "slug": "webflow"},
    # Robotics / autonomy / defense
    {"name": "Wayve",             "ats": "greenhouse",      "slug": "wayve",            "country": "UK"},
    {"name": "Skydio",            "ats": "ashby",           "slug": "skydio"},
    {"name": "Saronic",           "ats": "ashby",           "slug": "saronic"},
    {"name": "Boom Supersonic",   "ats": "ashby",           "slug": "boom"},
    # European fintech / scaleups
    {"name": "N26",               "ats": "greenhouse",      "slug": "n26",              "country": "DE"},
    {"name": "Trade Republic",    "ats": "greenhouse",      "slug": "traderepublic",    "country": "DE"},
    {"name": "GoCardless",        "ats": "greenhouse",      "slug": "gocardless",       "country": "UK"},
    {"name": "Monzo",             "ats": "greenhouse",      "slug": "monzo",            "country": "UK"},
    # Big SaaS / fintech with EU offices
    {"name": "Twilio",            "ats": "greenhouse",      "slug": "twilio"},
    {"name": "Asana",             "ats": "greenhouse",      "slug": "asana"},
    {"name": "Dropbox",           "ats": "greenhouse",      "slug": "dropbox"},
    {"name": "Pinterest",         "ats": "greenhouse",      "slug": "pinterest"},
    {"name": "Block",             "ats": "greenhouse",      "slug": "block"},
    {"name": "Robinhood",         "ats": "greenhouse",      "slug": "robinhood"},
    {"name": "Affirm",            "ats": "greenhouse",      "slug": "affirm"},
    {"name": "Chime",             "ats": "greenhouse",      "slug": "chime"},
    # --- Quant / HFT (London-heavy, top SWE prestige) ---
    {"name": "Jane Street",       "ats": "greenhouse",      "slug": "janestreet"},
    {"name": "Jump Trading",      "ats": "greenhouse",      "slug": "jumptrading"},
    {"name": "IMC Trading",       "ats": "greenhouse",      "slug": "imc",              "country": "NL"},
    {"name": "Flow Traders",      "ats": "greenhouse",      "slug": "flowtraders",      "country": "NL"},
    {"name": "Akuna Capital",     "ats": "greenhouse",      "slug": "akunacapital"},
    # --- Big consumer / fintech / devtools ---
    {"name": "DoorDash",          "ats": "greenhouse",      "slug": "doordashusa"},
    {"name": "Brex",              "ats": "greenhouse",      "slug": "brex"},
    {"name": "Docker",            "ats": "ashby",           "slug": "docker"},
    {"name": "Supabase",          "ats": "ashby",           "slug": "supabase"},
    {"name": "Amplitude",         "ats": "greenhouse",      "slug": "amplitude"},
    {"name": "1Password",         "ats": "ashby",           "slug": "1password"},
    {"name": "Metabase",          "ats": "lever",           "slug": "metabase"},
    {"name": "Cresta",            "ats": "greenhouse",      "slug": "cresta"},
    # --- EU AI (sovereign / French / German) ---
    {"name": "DeepL",             "ats": "ashby",           "slug": "deepl",            "country": "DE"},
    {"name": "Aleph Alpha",       "ats": "ashby",           "slug": "alephalpha",       "country": "DE"},
    {"name": "Photoroom",         "ats": "ashby",           "slug": "photoroom",        "country": "FR"},
    {"name": "Speechmatics",      "ats": "greenhouse",      "slug": "speechmatics",     "country": "UK"},
    # --- Frontier AI / data infra ---
    {"name": "Pika",              "ats": "ashby",           "slug": "pika"},
    {"name": "Physical Intelligence","ats": "ashby",        "slug": "physicalintelligence"},
    {"name": "ClickHouse",        "ats": "greenhouse",      "slug": "clickhouse"},
    {"name": "MotherDuck",        "ats": "ashby",           "slug": "motherduck"},
    {"name": "Turbopuffer",       "ats": "ashby",           "slug": "turbopuffer"},
    {"name": "Materialize",       "ats": "ashby",           "slug": "materialize"},
    {"name": "Pinecone",          "ats": "ashby",           "slug": "pinecone"},
    {"name": "Vapi",              "ats": "ashby",           "slug": "vapi"},
    # --- High-paying SaaS / security / enterprise ---
    {"name": "HubSpot",           "ats": "greenhouse",      "slug": "hubspotjobs"},
    {"name": "Zendesk",           "ats": "workday",         "slug": "zendesk/1/zendesk"},
    {"name": "SentinelOne",       "ats": "greenhouse",      "slug": "sentinellabs"},
    {"name": "Palo Alto Networks","ats": "smartrecruiters", "slug": "PaloAltoNetworks2"},
    {"name": "Fortinet",          "ats": None,              "slug": None},               # custom career site
    {"name": "HashiCorp",         "ats": None,               "slug": None},             # IBM acquisition, no public board
    {"name": "New Relic",         "ats": "greenhouse",      "slug": "newrelic"},
    {"name": "Veeva Systems",     "ats": "lever",           "slug": "veeva"},
    # --- High-paying fintech / banks (engineering) ---
    {"name": "Goldman Sachs",     "ats": "jobspy",          "slug": "1038"},
    {"name": "Bloomberg",         "ats": "jobspy",          "slug": "7697"},
    {"name": "Morgan Stanley",    "ats": "workday",         "slug": "ms/5/External"},
    {"name": "JPMorgan Chase",    "ats": "jobspy",          "slug": "1067"},
    {"name": "PayPal",            "ats": "jobspy",          "slug": "10962"},
    {"name": "Workday",           "ats": "workday",         "slug": "workday/5/Workday"},      # company uses own product
    # --- Dev tools / data high-pays ---
    {"name": "dbt Labs",          "ats": "greenhouse",      "slug": "dbtlabsinc"},
    {"name": "Retool",            "ats": "greenhouse",      "slug": "retool"},
    {"name": "Benchling",         "ats": "ashby",           "slug": "benchling"},
    {"name": "Weights & Biases",  "ats": "lever",           "slug": "wandb"},
    {"name": "Airtable",          "ats": "greenhouse",      "slug": "airtable"},
    {"name": "Gusto",             "ats": "greenhouse",      "slug": "gusto"},
    {"name": "Carta",             "ats": "greenhouse",      "slug": "carta"},
    {"name": "Mercury",           "ats": "greenhouse",      "slug": "mercury"},
    {"name": "Ironclad",          "ats": "ashby",           "slug": "ironcladhq"},
    {"name": "Dataiku",           "ats": "greenhouse",      "slug": "dataiku",         "country": "FR"},
    {"name": "Hex",               "ats": "greenhouse",      "slug": "hex"},
    {"name": "Pigment",           "ats": "lever",           "slug": "pigment",         "country": "FR"},
    {"name": "Criteo",            "ats": "smartrecruiters", "slug": "Criteo2",         "country": "FR"},
    # --- Big recognizable ---
    {"name": "Okta",              "ats": "greenhouse",      "slug": "okta"},
    {"name": "Zscaler",           "ats": "greenhouse",      "slug": "zscaler"},
    {"name": "Pure Storage",      "ats": "greenhouse",      "slug": "purestorage"},
    {"name": "Roku",              "ats": "greenhouse",      "slug": "roku"},
    {"name": "HelloFresh",        "ats": "greenhouse",      "slug": "hellofresh", "country": "DE"},
    {"name": "Lyft",              "ats": "greenhouse",      "slug": "lyft"},
    {"name": "Instacart",         "ats": "greenhouse",      "slug": "instacart"},
    {"name": "Ripple",            "ats": "greenhouse",      "slug": "ripple"},
    {"name": "Lucid Motors",      "ats": "greenhouse",      "slug": "lucidmotors"},
    {"name": "Twitch",            "ats": "greenhouse",      "slug": "twitch"},
    {"name": "Fastly",            "ats": "greenhouse",      "slug": "fastly"},
    {"name": "PagerDuty",         "ats": "greenhouse",      "slug": "pagerduty"},
    {"name": "Take-Two Interactive","ats": "greenhouse",    "slug": "taketwo"},
    {"name": "Crusoe",            "ats": "ashby",           "slug": "crusoe"},
    {"name": "Vannevar Labs",     "ats": "greenhouse",      "slug": "vannevarlabs"},

    # --- Aerospace / Defense / Space ---
    {"name": "Rocket Lab",        "ats": "greenhouse",      "slug": "rocketlab"},
    {"name": "Aurora",            "ats": "greenhouse",      "slug": "aurorainnovation"},
    {"name": "Astranis",          "ats": "greenhouse",      "slug": "astranis"},
    # Energy / Fusion
    {"name": "Helion",            "ats": "ashby",           "slug": "helion"},
    # AI hardware / chips
    {"name": "Cerebras",          "ats": "greenhouse",      "slug": "cerebrassystems"},         # 89
    {"name": "SambaNova",         "ats": "greenhouse",      "slug": "sambanovasystems"},        # 24
    {"name": "Tenstorrent",       "ats": "greenhouse",      "slug": "tenstorrent"},             # 118 (Jim Keller)
    {"name": "Etched",            "ats": "ashby",           "slug": "etched"},                  # 98 (transformer ASIC)
    {"name": "Lambda Labs",       "ats": "ashby",           "slug": "lambda"},                  # 34 (GPU cloud)
    {"name": "RunPod",            "ats": "ashby",           "slug": "runpod"},                  # 19 (GPU cloud)
    # Biotech
    {"name": "Ginkgo Bioworks",   "ats": "greenhouse",      "slug": "ginkgobioworks"},          # 11
    # Dev tools / Infra
    {"name": "Render",            "ats": "ashby",           "slug": "render"},                  # 22 (PaaS)
    {"name": "Railway",           "ats": "ashby",           "slug": "railway"},                 # 9 (PaaS)
    {"name": "Neon",              "ats": "ashby",           "slug": "neon"},                    # 7 (serverless Postgres)
    {"name": "CircleCI",          "ats": "greenhouse",      "slug": "circleci"},                # 11
    {"name": "Sentry",            "ats": "ashby",           "slug": "sentry"},                  # 40
    {"name": "Grafana Labs",      "ats": "greenhouse",      "slug": "grafanalabs"},             # 128
    # Fintech / payments
    {"name": "Plaid",             "ats": "ashby",           "slug": "plaid"},                   # 85
    {"name": "SoFi",              "ats": "greenhouse",      "slug": "sofi"},                    # 153
    {"name": "Marqeta",           "ats": "greenhouse",      "slug": "marqeta"},                 # 38
    {"name": "Rho",               "ats": "ashby",           "slug": "rho"},                     # 25
    {"name": "Carvana",           "ats": "greenhouse",      "slug": "carvana"},                 # 2205
    # Crypto / prediction markets
    {"name": "Polymarket",        "ats": "ashby",           "slug": "polymarket"},              # 44 (hot)
    {"name": "Kalshi",            "ats": "ashby",           "slug": "kalshi"},                  # 28
    {"name": "Fireblocks",        "ats": "greenhouse",      "slug": "fireblocks"},              # 52
    # Gaming / consumer
    {"name": "AppLovin",          "ats": "greenhouse",      "slug": "applovin"},                # 26
    {"name": "FanDuel",           "ats": "greenhouse",      "slug": "fanduel"},                 # 130
    {"name": "Wayfair",           "ats": "smartrecruiters", "slug": "Wayfair"},                 # 1
    # AI coding / hot 2026
    {"name": "Continue",          "ats": "ashby",           "slug": "continue"},                # 3
    {"name": "Mercor",            "ats": "ashby",           "slug": "mercor"},                  # 58 (Thiel Fellow)
    {"name": "Anrok",             "ats": "ashby",           "slug": "anrok"},                   # 21
    {"name": "Newfront",          "ats": "ashby",           "slug": "newfront"},                # 20
    # --- More frontier AI / data infra ---
    # Mistral AI already in GLOBAL
    {"name": "Nous Research",     "ats": "ashby",           "slug": "nousresearch"},
    {"name": "Writer",            "ats": "greenhouse",      "slug": "writer"},
    {"name": "Contextual AI",     "ats": "ashby",           "slug": "contextual"},
    {"name": "Exa",               "ats": "ashby",           "slug": "exa"},
    {"name": "Luma AI",           "ats": "lever",           "slug": "LumaAi"},             # Dream Machine video gen
    # CoreWeave already in GLOBAL
    {"name": "Groq",              "ats": None,               "slug": None},             # Gem ATS, not supported
    {"name": "SandboxAQ",         "ats": "greenhouse",      "slug": "sandboxaq"},          # quantum + AI, spun out of Google
    {"name": "IonQ",              "ats": "greenhouse",      "slug": "ionq"},               # public quantum computing
    {"name": "PsiQuantum",        "ats": "greenhouse",      "slug": "psiquantum"},
    # --- More gaming / consumer ---
    {"name": "Niantic",           "ats": "greenhouse",      "slug": "niantic"},            # Pokemon GO
    {"name": "Zynga",             "ats": "greenhouse",      "slug": "zyngacareers"},
    {"name": "Gearbox Software",      "ats": "greenhouse",  "slug": "gearbox"},
    {"name": "Frontier Developments", "ats": "workable",   "slug": "frontierdevelopments","country": "UK"},
    {"name": "Fatshark",              "ats": "teamtailor", "slug": "fatshark.teamtailor.com","country": "SE"},
    {"name": "Hazelight",             "ats": "teamtailor", "slug": "hazelight.teamtailor.com","country": "SE"},
    {"name": "Resolution Games",      "ats": "teamtailor", "slug": "resolutiongames.teamtailor.com","country": "SE"},
    # --- More infrastructure / cloud ---
    {"name": "Hetzner",           "ats": None,              "slug": None,      "country": "DE"},  # German cloud / hosting
    {"name": "IONOS",             "ats": "greenhouse",      "slug": "eu:ionos2","country": "DE"},
    {"name": "OVHcloud",          "ats": None,              "slug": None,      "country": "FR"},
    # --- More defense / space ---
    {"name": "Isar Aerospace",    "ats": "greenhouse",      "slug": "isaraerospace",   "country": "DE"},
]


# --- India: 100 prestigious Indian companies ------------------------------
# Added for the India-only alerter. Every "greenhouse / lever / ashby /
# smartrecruiters / recruitee" slug below was live-probed at build time
# (2026-07-27) and returned a non-empty jobs array from the real company's
# board. Four look-alike slugs were probed and REJECTED because they belong
# to unrelated firms: greenhouse:pine (a Toronto mortgage broker, not Pine
# Labs), ashby:navi (an SF startup, not Navi), greenhouse:slice (a North
# Macedonian company, not slice), ashby:tiger (an SF startup, not Tiger
# Analytics).
#
# Everything else runs on an in-house portal, Workday, SAP SuccessFactors,
# Darwinbox or Keka with no anonymous JSON endpoint, so it is wired to
# `jobspy`, which reaches it through Google Jobs. jobspy is opt-in
# (--jobspy / USE_JOBSPY=1) and costs roughly 10s + an 8s throttle per
# company, so a full jobspy pass over this list takes ~30 min. The 23
# directly-wired boards above need none of that and run on every plain run.
INDIA = [
    # --- IT services / engineering R&D ---
    {"name": "Tata Consultancy Services", "ats": "jobspy", "slug": "tcs",              "country": "IN"},
    {"name": "Infosys",              "ats": "jobspy",          "slug": "infosys",       "country": "IN"},
    {"name": "Wipro",                "ats": "jobspy",          "slug": "wipro",         "country": "IN"},
    {"name": "HCLTech",              "ats": "jobspy",          "slug": "hcltech",       "country": "IN"},
    {"name": "Tech Mahindra",        "ats": "jobspy",          "slug": "techmahindra",  "country": "IN"},
    {"name": "LTIMindtree",          "ats": "jobspy",          "slug": "ltimindtree",   "country": "IN"},
    {"name": "L&T Technology Services","ats": "jobspy",        "slug": "ltts",          "country": "IN"},
    {"name": "Mphasis",              "ats": "smartrecruiters", "slug": "mphasis1",      "country": "IN"},  # 8 jobs
    {"name": "Persistent Systems",   "ats": "jobspy",          "slug": "persistent",    "country": "IN"},
    {"name": "Coforge",              "ats": "jobspy",          "slug": "coforge",       "country": "IN"},
    {"name": "Hexaware",             "ats": "jobspy",          "slug": "hexaware",      "country": "IN"},
    {"name": "Cyient",               "ats": "jobspy",          "slug": "cyient",        "country": "IN"},
    {"name": "KPIT Technologies",    "ats": "jobspy",          "slug": "kpit",          "country": "IN"},
    {"name": "Tata Elxsi",           "ats": "jobspy",          "slug": "tataelxsi",     "country": "IN"},
    {"name": "Birlasoft",            "ats": "jobspy",          "slug": "birlasoft",     "country": "IN"},
    {"name": "Sonata Software",      "ats": "jobspy",          "slug": "sonatasoftware","country": "IN"},
    {"name": "Happiest Minds",       "ats": "jobspy",          "slug": "happiestminds", "country": "IN"},
    {"name": "Zensar Technologies",  "ats": "jobspy",          "slug": "zensar",        "country": "IN"},
    {"name": "Sasken Technologies",  "ats": "jobspy",          "slug": "sasken",        "country": "IN"},
    {"name": "Newgen Software",      "ats": "jobspy",          "slug": "newgen",        "country": "IN"},

    # --- Consumer internet / commerce / mobility ---
    {"name": "Flipkart",             "ats": "jobspy",          "slug": "flipkart",      "country": "IN"},
    {"name": "Zomato",               "ats": "smartrecruiters", "slug": "zomato1",       "country": "IN"},  # 3 jobs
    {"name": "Swiggy",               "ats": "smartrecruiters", "slug": "swiggy",        "country": "IN"},  # 3 jobs
    {"name": "Meesho",               "ats": "lever",           "slug": "meesho",        "country": "IN"},  # 45 jobs
    {"name": "Myntra",               "ats": "jobspy",          "slug": "myntra",        "country": "IN"},
    {"name": "Nykaa",                "ats": "jobspy",          "slug": "nykaa",         "country": "IN"},
    {"name": "BigBasket",            "ats": "jobspy",          "slug": "bigbasket",     "country": "IN"},
    {"name": "Zepto",                "ats": "jobspy",          "slug": "zepto",         "country": "IN"},
    {"name": "Blinkit",              "ats": "jobspy",          "slug": "blinkit",       "country": "IN"},
    {"name": "Urban Company",        "ats": "jobspy",          "slug": "urbancompany",  "country": "IN"},
    {"name": "Udaan",                "ats": "jobspy",          "slug": "udaan",         "country": "IN"},
    {"name": "Lenskart",             "ats": "recruitee",       "slug": "lenskartcareers","country": "IN"},  # 72 jobs
    {"name": "Delhivery",            "ats": "jobspy",          "slug": "delhivery",     "country": "IN"},
    {"name": "Ola",                  "ats": "jobspy",          "slug": "olacabs",       "country": "IN"},
    {"name": "Ola Electric",         "ats": "jobspy",          "slug": "olaelectric",   "country": "IN"},
    {"name": "Rapido",               "ats": "jobspy",          "slug": "rapido",        "country": "IN"},
    {"name": "OYO",                  "ats": "jobspy",          "slug": "oyo",           "country": "IN"},
    {"name": "MakeMyTrip",           "ats": "jobspy",          "slug": "makemytrip",    "country": "IN"},
    {"name": "ixigo",                "ats": "smartrecruiters", "slug": "ixigo",         "country": "IN"},  # 9 jobs
    {"name": "Info Edge (Naukri)",   "ats": "jobspy",          "slug": "infoedge",      "country": "IN"},

    # --- Fintech / financial infrastructure ---
    {"name": "Paytm",                "ats": "lever",           "slug": "paytm",         "country": "IN"},  # 228 jobs
    {"name": "PhonePe",              "ats": "greenhouse",      "slug": "phonepe",       "country": "IN"},  # 61 jobs
    {"name": "Razorpay",             "ats": "jobspy",          "slug": "razorpay",      "country": "IN"},
    {"name": "CRED",                 "ats": "lever",           "slug": "cred",          "country": "IN"},  # 3 jobs
    {"name": "Zerodha",              "ats": "jobspy",          "slug": "zerodha",       "country": "IN"},
    {"name": "Groww",                "ats": "greenhouse",      "slug": "groww",         "country": "IN"},  # 11 jobs
    {"name": "Pine Labs",            "ats": "jobspy",          "slug": "pinelabs",      "country": "IN"},
    {"name": "Juspay",               "ats": "jobspy",          "slug": "juspay",        "country": "IN"},
    {"name": "Cashfree Payments",    "ats": "jobspy",          "slug": "cashfree",      "country": "IN"},
    {"name": "slice",                "ats": "jobspy",          "slug": "sliceit",       "country": "IN"},
    {"name": "Navi",                 "ats": "jobspy",          "slug": "navitechnologies","country": "IN"},
    {"name": "Fi Money",             "ats": "lever",           "slug": "epifi",         "country": "IN"},  # 8 jobs
    {"name": "Jupiter Money",        "ats": "jobspy",          "slug": "jupitermoney",  "country": "IN"},
    {"name": "Zeta",                 "ats": "lever",           "slug": "zeta",          "country": "IN"},  # 26 jobs
    {"name": "M2P Fintech",          "ats": "jobspy",          "slug": "m2pfintech",    "country": "IN"},
    {"name": "Perfios",              "ats": "jobspy",          "slug": "perfios",       "country": "IN"},
    {"name": "Policybazaar",         "ats": "jobspy",          "slug": "policybazaar",  "country": "IN"},
    {"name": "Angel One",            "ats": "jobspy",          "slug": "angelone",      "country": "IN"},
    {"name": "NPCI",                 "ats": "jobspy",          "slug": "npci",          "country": "IN"},
    {"name": "smallcase",            "ats": "jobspy",          "slug": "smallcase",     "country": "IN"},

    # --- SaaS / enterprise product ---
    {"name": "Zoho",                 "ats": "jobspy",          "slug": "zoho",          "country": "IN"},
    {"name": "Freshworks",           "ats": "smartrecruiters", "slug": "freshworks",    "country": "IN"},  # 143 jobs
    # Postman is Indian-founded and belongs in this tier, but it is already
    # wired in EXTRAS above (greenhouse:postman) — listing it twice would
    # fetch the same board twice, so the slot goes to Dream11 instead.
    {"name": "Dream11",              "ats": "jobspy",          "slug": "dream11",       "country": "IN"},
    {"name": "BrowserStack",         "ats": "jobspy",          "slug": "browserstack",  "country": "IN"},
    {"name": "Chargebee",            "ats": "jobspy",          "slug": "chargebee",     "country": "IN"},
    {"name": "Hasura",               "ats": "jobspy",          "slug": "hasura",        "country": "IN"},
    {"name": "Druva",                "ats": "greenhouse",      "slug": "druva",         "country": "IN"},  # 31 jobs
    {"name": "Icertis",              "ats": "jobspy",          "slug": "icertis",       "country": "IN"},
    {"name": "Innovaccer",           "ats": "jobspy",          "slug": "innovaccer",    "country": "IN"},
    {"name": "Darwinbox",            "ats": "jobspy",          "slug": "darwinbox",     "country": "IN"},
    {"name": "Whatfix",              "ats": "smartrecruiters", "slug": "whatfix",       "country": "IN"},  # 1 job
    {"name": "MoEngage",             "ats": "jobspy",          "slug": "moengage",      "country": "IN"},
    {"name": "CleverTap",            "ats": "jobspy",          "slug": "clevertap",     "country": "IN"},
    {"name": "Netcore Cloud",        "ats": "jobspy",          "slug": "netcore",       "country": "IN"},
    {"name": "Eightfold AI",         "ats": "jobspy",          "slug": "eightfold",     "country": "IN"},
    {"name": "Sprinklr",             "ats": "smartrecruiters", "slug": "sprinklr1",     "country": "IN"},  # 1 job
    {"name": "Amagi",                "ats": "jobspy",          "slug": "amagi",         "country": "IN"},
    {"name": "Atlan",                "ats": "ashby",           "slug": "atlan",         "country": "IN"},  # 5 jobs
    {"name": "Zluri",                "ats": "jobspy",          "slug": "zluri",         "country": "IN"},
    {"name": "Uniphore",             "ats": "jobspy",          "slug": "uniphore",      "country": "IN"},

    # --- AI / data / analytics / adtech ---
    {"name": "Sarvam AI",            "ats": "ashby",           "slug": "sarvam",        "country": "IN"},  # 61 jobs
    {"name": "Krutrim",              "ats": "jobspy",          "slug": "krutrim",       "country": "IN"},
    {"name": "Fractal Analytics",    "ats": "jobspy",          "slug": "fractal",       "country": "IN"},
    {"name": "Mu Sigma",             "ats": "jobspy",          "slug": "musigma",       "country": "IN"},
    {"name": "Tiger Analytics",      "ats": "jobspy",          "slug": "tigeranalytics","country": "IN"},
    {"name": "LatentView Analytics", "ats": "jobspy",          "slug": "latentview",    "country": "IN"},
    {"name": "Quantiphi",            "ats": "jobspy",          "slug": "quantiphi",     "country": "IN"},
    {"name": "InMobi",               "ats": "greenhouse",      "slug": "inmobi",        "country": "IN"},  # 69 jobs
    {"name": "Glance",               "ats": "greenhouse",      "slug": "glance",        "country": "IN"},  # 41 jobs
    {"name": "Observe.AI",           "ats": "greenhouse",      "slug": "observeai",     "country": "IN"},  # 17 jobs
    {"name": "Turing",               "ats": "greenhouse",      "slug": "turing",        "country": "IN"},  # 31 jobs

    # --- Space / defence / semis / EV hardware ---
    {"name": "Skyroot Aerospace",    "ats": "jobspy",          "slug": "skyroot",       "country": "IN"},
    {"name": "Agnikul Cosmos",       "ats": "jobspy",          "slug": "agnikul",       "country": "IN"},
    {"name": "Pixxel",               "ats": "jobspy",          "slug": "pixxel",        "country": "IN"},
    {"name": "Dhruva Space",         "ats": "jobspy",          "slug": "dhruvaspace",   "country": "IN"},
    {"name": "Bellatrix Aerospace",  "ats": "jobspy",          "slug": "bellatrix",     "country": "IN"},
    {"name": "ideaForge",            "ats": "jobspy",          "slug": "ideaforge",     "country": "IN"},
    {"name": "Tonbo Imaging",        "ats": "jobspy",          "slug": "tonboimaging",  "country": "IN"},
    {"name": "Tata Electronics",     "ats": "jobspy",          "slug": "tataelectronics","country": "IN"},
    {"name": "Ather Energy",         "ats": "jobspy",          "slug": "atherenergy",   "country": "IN"},
]

# --- India: conglomerates, banks, pharma, core engineering ----------------
# Bonus tier on top of the 100 above. These are the household-name Indian
# employers whose tech / R&D arms take interns but who never expose a public
# ATS JSON endpoint, so they are all jobspy-only.
INDIA_CORE = [
    {"name": "Reliance Industries",  "ats": "jobspy",          "slug": "reliance",      "country": "IN"},
    {"name": "Jio Platforms",        "ats": "jobspy",          "slug": "jio",           "country": "IN"},
    {"name": "Larsen & Toubro",      "ats": "jobspy",          "slug": "larsentoubro",  "country": "IN"},
    {"name": "Tata Motors",          "ats": "jobspy",          "slug": "tatamotors",    "country": "IN"},
    {"name": "Mahindra & Mahindra",  "ats": "jobspy",          "slug": "mahindra",      "country": "IN"},
    {"name": "Bajaj Auto",           "ats": "jobspy",          "slug": "bajajauto",     "country": "IN"},
    {"name": "Maruti Suzuki",        "ats": "jobspy",          "slug": "marutisuzuki",  "country": "IN"},
    {"name": "Adani Group",          "ats": "jobspy",          "slug": "adani",         "country": "IN"},
    {"name": "JSW Group",            "ats": "jobspy",          "slug": "jsw",           "country": "IN"},
    {"name": "Godrej",               "ats": "jobspy",          "slug": "godrej",        "country": "IN"},
    {"name": "Ultraviolette",        "ats": "jobspy",          "slug": "ultraviolette", "country": "IN"},
    {"name": "Sun Pharma",           "ats": "jobspy",          "slug": "sunpharma",     "country": "IN"},
    {"name": "Dr. Reddy's",          "ats": "jobspy",          "slug": "drreddys",      "country": "IN"},
    {"name": "Cipla",                "ats": "jobspy",          "slug": "cipla",         "country": "IN"},
    {"name": "Biocon",               "ats": "jobspy",          "slug": "biocon",        "country": "IN"},
    {"name": "Serum Institute of India","ats": "jobspy",       "slug": "seruminstitute","country": "IN"},
    {"name": "HDFC Bank",            "ats": "jobspy",          "slug": "hdfcbank",      "country": "IN"},
    {"name": "ICICI Bank",           "ats": "jobspy",          "slug": "icicibank",     "country": "IN"},
    {"name": "Axis Bank",            "ats": "jobspy",          "slug": "axisbank",      "country": "IN"},
    {"name": "Kotak Mahindra Bank",  "ats": "jobspy",          "slug": "kotak",         "country": "IN"},
]


def all_companies() -> list[dict]:
    out: list[dict] = []
    for c in (GLOBAL + GLOBAL_EU_BIASED + FINLAND + SWITZERLAND + EU_SCALEUPS
              + EXTRAS + INDIA + INDIA_CORE):
        c.setdefault("country", "")
        out.append(c)
    return out


def supported_companies() -> list[dict]:
    """Only companies wired to a working ATS slug."""
    return [c for c in all_companies() if c.get("ats") and c.get("slug")]
