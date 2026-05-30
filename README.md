<p align="center">
  <img src="docs/assets/logo.png" alt="FairPrice Watchdog" width="180" />
</p>

<h1 align="center">FairPrice Watchdog</h1>

<p align="center">
  <strong>AI agents that catch hidden fees & geographic price discrimination — live, with court-ready, hash-sealed evidence across 29 jurisdictions.</strong>
</p>

<p align="center">
  <a href="https://takochi.duckdns.org/"><img alt="Live Demo" src="https://img.shields.io/badge/live%20demo-takochi.duckdns.org-F4C752?style=for-the-badge" /></a>
  <a href="https://takochi.duckdns.org/app/#arch"><img alt="Architecture" src="https://img.shields.io/badge/architecture-diagram-818cf8?style=for-the-badge" /></a>
  <a href="https://takochi.duckdns.org/docs"><img alt="API" src="https://img.shields.io/badge/API-docs-34d399?style=for-the-badge" /></a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10-3776AB?logo=python&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white" />
  <img alt="React" src="https://img.shields.io/badge/React-Vite-61DAFB?logo=react&logoColor=black" />
  <img alt="Bright Data" src="https://img.shields.io/badge/Bright%20Data-4%20products-2A4DD0" />
  <img alt="FTC" src="https://img.shields.io/badge/FTC-16%20CFR%20Part%20464-444" />
</p>

> **Web Data UNLOCKED Hackathon** (Bright Data) — submitted to **Security & Compliance** (primary) and **Finance & Market Intelligence**, with the **AI/ML API Challenge** (AIMLAPI vision + reasoning). Built on the Bright Data web-data stack.

---

## 🎬 Try it in 60 seconds

**Live:** **[takochi.duckdns.org](https://takochi.duckdns.org/)**

1. **Instant probe** — type *"Marriott Marquis Times Square price per night"* → see a US shopper is shown **$341** while a UK shopper sees **£141** for the same room, in ~3 seconds.
2. **Deep scan** — click the **Hotels.com** proven-target card (auto-fills GB vs US) → **Run Live Scan** → watch six agents capture the page, then:
   - a real geo gap (**$137 GB vs $117 US**, same hotel & dates — captured live),
   - **both location screenshots** side-by-side, SHA-256 sealed,
   - every fee mapped to its exact **FTC clause**,
   - a one-click **court-ready PDF complaint** with the screenshots embedded as exhibits.

---

## The problem

US consumers lose an estimated **$64 billion a year** to drip pricing and hidden fees. In **May 2025** the FTC's **Junk Fees Rule (16 CFR Part 464)** made undisclosed mandatory fees illegal across all 50 states — with penalties up to **$51,744 per violation**. Enforcement is already landing: **Greystar ($23M)**, **Invitation Homes ($48M)**.

But there's a bottleneck: **the same listing can cost a shopper in London more than one in New York, at the same moment — and nobody can prove it at scale.** Regulators and class-action firms need timestamped, tamper-proof evidence. Collecting it by hand doesn't scale.

**FairPrice Watchdog is the picks-and-shovels for that evidence.**

---

## What it does

A swarm of six specialized agents takes a single URL and produces a filable complaint:

| # | Agent | Role |
|---|---|---|
| 1 | **Crawler** | Loads the listing from a chosen location via Bright Data geo-proxies and reads the advertised price |
| 2 | **Journey Simulator** | Walks the checkout funnel — and **stops before payment** — to capture the real final total |
| 3 | **Diff** | Compares advertised vs. final, extracts every line-item fee |
| 4 | **Law-Mapper** | Maps each fee to its exact FTC clause with a **detectability tier** (agent-clean / needs-review / exempt) |
| 5 | **Discovery** | Finds new operators to monitor via live web search |
| 6 | **Filing** | Assembles the SHA-256-sealed evidence bundle + court-ready PDF complaint |

### What makes it different

- **It reads prices like a human.** When a site renders prices in JavaScript (invisible to raw scraping), the agent captures a **fully-rendered screenshot via the Bright Data Browser API** and a **vision model reads the price off the image** — no brittle selectors.
- **It never hangs.** Every fetch has a hard deadline and falls back gracefully (Web Unlocker → Residential → Browser API → honest "mock" label). A blocked site degrades to a labeled result, never a frozen demo.
- **It's honest.** Every result is tagged `live` / `partial` / `mock`. We never present synthetic data as real.
- **It's court-ready.** Every HTML + screenshot capture is SHA-256 hashed and embedded in a filable FTC complaint PDF.

📐 **Full architecture diagram:** **[takochi.duckdns.org/app/#arch](https://takochi.duckdns.org/app/#arch)**

---

## Built on the Bright Data stack (Application of Technology)

| Product | Used for |
|---|---|
| **Web Unlocker** | Anti-bot bypass + country-level geo on real commerce sites |
| **Residential Proxies** | True **US state-level** geo targeting — verified live (CA → Sacramento, TX → Katy) |
| **Browser API** | A real Chromium we control — waits for JS to render, then full-page screenshot (the key to JS-rendered prices) |
| **SERP API** | The Discovery agent's runtime target search |
| **Zone Management API** | Zones created **programmatically** (`scripts/bd_create_zone.py`) |

**Plus:** vision price-reading (GPT-4o), an LLM fallback chain (Kimi → gateway), live web search for discovery, knowledge-graph memory for cross-scan recall, and speech-to-text for voice-driven scans.

---

## Detectable + defensible: the FTC taxonomy

The Law-Mapper runs on a **16-fee taxonomy** ([`docs/FTC_Fee_Taxonomy.xlsx`](docs/FTC_Fee_Taxonomy.xlsx)) that maps each fee to a clause and a **detectability tier** — so we never over-claim in court:

| Tier | Meaning | Examples |
|---|---|---|
| 🟢 **Agent-clean** | Hard disclosure violation, §464.2(a) — bankable | resort, cleaning, facility, amenity, booking |
| 🟡 **Needs review** | Disclosure clean; misrepresentation (§464.3) needs a human | service, admin, convenience |
| ⚪ **Exempt** | Government charges (§464.1) — **stripped** from the junk-fee total | tax, occupancy tax |

Regenerate the agent taxonomy from the sheet anytime:
```bash
python scripts/gen_taxonomy_from_xlsx.py   # docs/FTC_Fee_Taxonomy.xlsx → app/agents/ftc_taxonomy.py
python scripts/seed_taxonomy.py            # → Postgres fee_taxonomy (pgvector)
```

---

## Coverage: 29 jurisdictions

The same violation pattern — advertised price ≠ checkout total — is enforceable in every region we cover:

- **🇺🇸 United States** — FTC 16 CFR Part 464 (lodging + ticketing) + FTC Act §5 + state UDAP
- **🇬🇧 United Kingdom** — Digital Markets, Competition & Consumers Act 2024
- **🇪🇺 European Union (27)** — Unfair Commercial Practices Directive + the incoming Digital Fairness Act

---

## Hackathon tracks

| Track / Challenge | How FairPrice Watchdog fits |
|---|---|
| **🛡️ Security & Compliance** *(primary)* | Detects **illegal pricing practices** under the FTC Junk Fees Rule (16 CFR §464) and produces **tamper-proof, court-ready compliance evidence** for regulators and risk/legal teams. Regulatory risk, end to end. |
| **📈 Finance & Market Intelligence** | Cross-market price intelligence — compares the same product across geographies, quantifies the gap, and surfaces hidden fee structures. |
| **🤖 AI/ML API Challenge** | Uses **AIMLAPI** as the intelligence layer: GPT-4o **vision** reads JS-rendered prices off rendered screenshots, plus LLM reasoning for fee classification and FTC clause mapping. |
| **✅ Bright Data (required)** | Four products in production — Web Unlocker, Residential, Browser API, SERP — plus the Zone Management API. |

---

## Architecture

```
[React/Vite UI]  →  [FastAPI]  →  [Postgres + pgvector]  →  [Redis queue]
                                                                  ↓
                                                            [Worker (systemd)]
                                                                  ↓  per geo, in parallel
   Crawler → Journey → Diff → Law-Mapper → Filing
        │        │
        │   Bright Data: Web Unlocker → Residential → Browser API   (hard deadlines, never hangs)
        │   Vision (GPT-4o reads JS prices off the screenshot)
        │   LLM (Kimi → gateway fallback)
        ↓
   [Evidence Vault: MinIO / Cloudflare R2 · SHA-256]  →  screenshots + court-ready PDF complaint
```

- **Backend:** FastAPI · SQLAlchemy async · asyncpg · Postgres + pgvector · Redis · Alembic
- **Agents:** CrewAI orchestration with a deterministic fallback (reproducible — critical for legal evidence)
- **Frontend:** React · Vite · TypeScript · TailwindCSS · framer-motion · canvas/SVG world map · live "studio" agent feed
- **Deploy:** Vultr VM · **systemd** services (auto-restart) · **Caddy** reverse proxy with auto-HTTPS

---

## Run locally

```bash
# 1. Backend (needs Postgres + Redis; copy .env.example → .env)
python -m venv venv && ./venv/bin/pip install -r requirements.txt
alembic upgrade head && python scripts/seed_taxonomy.py
uvicorn app.main:app --host 0.0.0.0 --port 8000      # API
python -m app.worker                                 # scan worker (separate shell)

# 2. Frontend
cd demo && npm install
VITE_API_BASE=http://localhost:8000 npm run dev
```

With no credentials the whole stack runs in a **fee-aware offline mock mode**, so the demo works end-to-end without keys.

---

## Key API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/scan` | Start a two-geo scan |
| `GET` | `/api/results/{id}` | Listings + fees + FTC clauses |
| `GET` | `/api/scan/{id}/events` | Live agent "thinking" stream |
| `GET` | `/api/screenshot/{id}/{geo}` | Sealed page screenshot |
| `POST` | `/api/generate-complaint/{id}/pdf` | Court-ready PDF complaint |
| `GET` | `/api/probe?q=` | Instant geo price-discrimination probe |

Full interactive docs: **[/docs](https://takochi.duckdns.org/docs)**

---

## Team

| Member | Role |
|---|---|
| **Haseeb (Takochi)** | Tech Lead & Agent Architect — pipeline, Bright Data, vision, evidence vault, deploy |
| **Eman** | Backend Engineer & DevOps — FastAPI, Postgres, evidence service, PDF generator |
| **Tanzila** | Frontend Lead & Visual Design |
| **Eman Bashir** | Frontend Support & PDF Generator |
| **Matas (MrCheese)** | Domain Research — FTC taxonomy, enforcement sourcing |
| **Tom (MrSlime)** | Business Model & Market Sizing |

---

## Honest scope

The FTC Junk Fees Rule covers **lodging + ticketing** today; rental housing is enforced via FTC Act §5 + state UDAP (the basis of the Greystar case), with a dedicated rental rule in FTC rulemaking since Dec 2025. We catch both. Where a site is too heavily fortified to capture cleanly in one pass, the system says so — and seals whatever it does capture. **Real evidence, honestly labeled.**

<p align="center"><em>The law landed in May 2025. The cases are landing now. The bottleneck is evidence — and that's what we built.</em></p>
