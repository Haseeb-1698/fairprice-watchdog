# FairPrice Watchdog API

A FastAPI-based backend service for monitoring and detecting unfair pricing practices.

---

## 📊 Project Status

**Integrated:** the agent pipeline and the backend API are merged on a single `main`.
**Deployed:** running on a Vultr VM — one API (`:8000`) + one worker against Postgres + Redis.

✅ done · 🟡 partial · ⬜ not started · ⛔ blocked on a teammate

### Haseeb — Tech Lead & Agent Architect
| Item | Status |
|---|---|
| 6-agent pipeline: Crawler, Journey Simulator, Diff, Law-Mapper, Discovery, Filing | ✅ |
| CrewAI orchestration + deterministic fallback | ✅ |
| Bright Data — residential geo zone (created via API), Web Unlocker, Browser API, SERP; credit cap | ✅ |
| **State-level geo verified live** (CA → Sacramento, TX → Katy) | ✅ |
| Evidence vault — MinIO (local) + Cloudflare R2 (prod), SHA-256 hash chain | ✅ |
| Multi-provider LLM (Kimi active / Claude Opus 4.7 / Azure / OpenAI / offline mock) | ✅ |
| FTC Junk Fee taxonomy v1 (16 CFR Part 464) + pgvector seed | ✅ |
| Firecrawl + markitdown extraction | ✅ |
| VM deployment (API + worker + migrations + taxonomy seed) | ✅ |
| Offline end-to-end smoke test | ✅ |
| Live two-geo scan on **real** target sites | ⛔ needs Matas's demo URLs |
| Real FTC taxonomy + semantic embeddings | ⛔ needs Matas's taxonomy sheet |
| Skyvern live checkout walking (Playwright/CDP seam in place) | 🟡 |
| Architecture diagram · backup demo video · submission tags | ⬜ |

### Eman — Backend Engineer & DevOps
| Item | Status |
|---|---|
| FastAPI app, routers, CORS | ✅ |
| Postgres schema + Alembic (scans, listings, fees, evidence_snapshots, complaints, fee_taxonomy/pgvector) | ✅ |
| Redis queue (now consumed by the worker) | ✅ |
| DB-backed endpoints: `/scan`, `/results`, `/evidence`, `/generate-complaint` | ✅ |
| Evidence vault service + class-action bundle ZIP | ✅ |
| Integration tests (pytest) | ✅ |
| Stripe checkout/webhook | 🟡 stub |
| `fee_taxonomy` populated | ✅ v1 (Matas's real taxonomy pending) |
| Deploy + public application URL | ⬜ |

Others: **Matas** — FTC taxonomy sheet + 5 demo target sites + video script; **Tanzila / Eman Bashir** — view field needs + PDF input JSON shape; **Tom** — business model.

### ⛔ Blocking the live demo
1. **Matas:** 5 demo URLs that price by *viewer* location and aren't behind heavy anti-bot (Cloudflare) — apartments.com prices by *listing* location, so it won't show a geo split.
2. **Matas:** FTC taxonomy spreadsheet (`fee_type → clause → description`) to replace the v1 seed.
3. **Eman:** public deploy URL; align the complaint JSON (Filing agent output ↔ PDF generator input).
4. **Note:** don't run `pytest` against the shared production DB — it drops the tables. Use a separate test DB / `.env.test`.

---

## Project Structure

```
fairprice-watchdog/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   ├── config.py        # Environment configuration
│   │   └── database.py      # SQLAlchemy async engine
│   ├── api/
│   │   └── routes/
│   │       ├── scan.py      # POST /api/scan
│   │       ├── results.py   # GET /api/results/{id}
│   │       ├── evidence.py  # GET /api/evidence/{id}
│   │       └── complaint.py # POST /api/generate-complaint
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   ├── agents/              # Agent pipeline (Haseeb)
│   │   ├── pipeline.py      #   run_scan() — two-geo orchestration entrypoint
│   │   ├── crew.py          #   CrewAI orchestrator (deterministic fallback)
│   │   ├── crawler.py       #   Crawler (geo-load listing → advertised $)
│   │   ├── journey.py       #   Journey Simulator (walk checkout, stop pre-payment)
│   │   ├── diff.py          #   Diff (advertised vs final, junk-fee detection)
│   │   ├── law_mapper.py    #   Law-Mapper (fee → FTC clause, taxonomy match)
│   │   ├── discovery.py     #   Discovery (SERP + Firecrawl operator finder)
│   │   ├── filing.py        #   Filing (court-ready complaint/evidence JSON)
│   │   ├── ftc_taxonomy.py  #   v1 FTC Junk Fee Rule taxonomy
│   │   ├── embeddings.py    #   384-dim embeddings (optional)
│   │   ├── llm.py           #   multi-provider LLM (Kimi/Claude/OpenAI/mock)
│   │   ├── extract.py       #   HTML→markdown + price/fee parsing
│   │   └── types.py         #   shared dataclasses
│   ├── services/            # brightdata.py, storage.py (MinIO/R2), firecrawl_client.py, credits.py, evidence.py, bundle.py, queue.py
│   └── worker.py            # Redis-queue consumer → runs the pipeline
├── scripts/
│   ├── smoke_full.py        # offline end-to-end test (all agents)
│   ├── smoke_two_geo.py     # offline two-geo demo test
│   ├── seed_taxonomy.py     # seed fee_taxonomy (pgvector)
│   ├── bd_create_zone.py    # create Bright Data zones via API
│   └── live_check.py        # live geo-fetch validation
├── requirements.txt
├── .env.example
└── README.md
```

## Setup Instructions

### 1. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and update with your actual values:

```bash
cp .env.example .env
```

Only two are **required**:
- `DATABASE_URL`: PostgreSQL connection string with the asyncpg driver
- `REDIS_URL`: Redis connection string

Everything else (Bright Data, LLM, MinIO/R2) is **optional** — leave blank to run the
pipeline in fully offline **mock mode** (no credentials, no credits used). See "Going live" below.

### 4. Run the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Health Check
- `GET /` - Root endpoint
- `GET /health` - Health check

### Scan Operations
- `POST /api/scan` — start a scan: `{"url": "...", "geos": ["california", "texas"]}` → `{id, status, ...}`
- `GET /api/scan/{scan_id}` — scan status
- `GET /api/results/{scan_id}` — listings + fees + geo comparison
- `GET /api/evidence/{scan_id}` — evidence snapshots (SHA-256 hashed)
- `POST /api/generate-complaint/{scan_id}` — court-ready evidence bundle ZIP

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Technology Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy 2.x**: Async ORM for database operations
- **asyncpg**: PostgreSQL async driver
- **Redis**: Caching and task queue
- **MinIO**: Object storage for evidence files
- **Pydantic**: Data validation and settings management

## Agent Pipeline (Tech Lead — Haseeb)

The agentic core that walks checkout funnels, proves geo-price discrimination,
and produces hashed evidence. Orchestrated with **CrewAI** (primary) with a
deterministic fallback.

### Two-geo demo flow (the punchline)

```
POST /api/scan {url, states:["CA","TX"]}
        │  creates scans row → LPUSH scan_queue
        ▼
   worker (BLPOP) ──► pipeline.run_scan(scan_id, url, states)
        │
        ├─ per state, in parallel ──────────────────────────────┐
        │     Crawler   → load listing via Bright Data geo proxy │  (advertised $)
        │     Journey   → walk checkout via Browser API, STOP    │  (final $ + fees)
        │                 before payment, capture DOM            │
        │     Diff      → advertised vs final, flag junk fees,   │
        │                 map to FTC clause                      │
        │     Vault     → store HTML snapshot + SHA-256 (MinIO/R2)│
        └────────────────────────────────────────────────────────┘
        ▼
   GeoComparison (two-state price split) → persist Listing/Fee/EvidenceSnapshot
        ▼
GET /api/results/{id}     → listings, fees, comparison, summary
GET /api/evidence/{id}    → snapshots + presigned download URLs
```

### Starred-repo integrations

| Agent / concern        | Powered by                          | Status |
|------------------------|-------------------------------------|--------|
| Orchestration          | **CrewAI** (`agents/crew.py`)       | wired  |
| HTML → markdown        | **markitdown** (`agents/extract.py`)| wired  |
| Crawler / Discovery    | **Firecrawl** (`services/firecrawl_client.py`) | wired (set `FIRECRAWL_API_KEY`) |
| Geo fetch / Browser    | **Bright Data** (`services/brightdata.py`) | wired |
| Journey live nav       | **Skyvern**                         | optional drop-in (`journey._walk_live`) |
| Diff engine            | **changedetection.io**              | pattern (advertised-vs-checkout diff) |
| Law-Mapper reasoning   | **open_deep_research** (LangGraph)  | pattern (later agent) |
| Agent memory           | **mem0**                            | optional |
| Screenshot OCR         | **PaddleOCR**                       | optional (evidence vault) |

### Mock mode (zero credentials)

Every external call degrades gracefully. With no Bright Data / LLM / storage
credentials the pipeline runs fully offline — Bright Data returns synthetic,
state-varying listing pages, the LLM uses a fee-aware heuristic, and snapshots
land in `./evidence_store/`. Verify it end-to-end without any infra:

```bash
python scripts/smoke_two_geo.py
# → CA $2527.00 vs TX $2122.68 — $404.32 (19%) gap, 4 junk fees, evidence hashed
```

### Going live

Fill the relevant blocks in `.env` (all optional, mix and match):

- **Bright Data**: `BRIGHTDATA_CUSTOMER_ID`, `BRIGHTDATA_RESIDENTIAL_ZONE`/`_PASSWORD`
  (state/ZIP geo — the demo axis), `BRIGHTDATA_API_KEY` + `BRIGHTDATA_ZONE` (Web Unlocker
  `/request`), and `BRIGHTDATA_BROWSER_ZONE`/`_PASSWORD` (Browser API). Create a geo-capable
  residential zone with `python scripts/bd_create_zone.py <name> resi`.
- **LLM**: any one of `ANTHROPIC_API_KEY`, `KIMI_API_KEY`, `AZURE_KIMI_*`, `OPENAI_API_KEY`.
- **Evidence vault**: default MinIO (in docker-compose), or set `STORAGE_BACKEND=r2`
  with `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`.

### Run the whole stack locally

```bash
cp .env.example .env          # fill in what you have; blanks = mock mode
docker compose up --build     # db + redis + minio + api + worker
docker compose exec api alembic upgrade head   # create tables

curl -X POST localhost:8000/api/scan \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com/listing","geos":["california","texas"]}'
# → {"id":"...","status":"queued", ...}
curl localhost:8000/api/results/<id>
```

> **Deployment:** a live instance runs on the project VM — one API on `:8000` + one
> worker (the worker consumes the shared Redis `scan_queue`, so run exactly one).
> Recreate tables after a fresh DB with `alembic upgrade head`, then seed the
> taxonomy with `python scripts/seed_taxonomy.py`.

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black app/
```

### Type Checking

```bash
mypy app/
```

## License

MIT