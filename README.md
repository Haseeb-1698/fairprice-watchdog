# FairPrice Watchdog API

A FastAPI-based backend service for monitoring and detecting unfair pricing practices.

---

## 📊 Project Status (team)

Updated alongside the agent-pipeline integration. ✅ done · 🟡 partial/stub · ⬜ not started.

### Haseeb — Tech Lead & Agent Architect
| Item | Status |
|---|---|
| Agent pipeline (two-geo demo path): Crawler → Journey → Diff | ✅ |
| CrewAI orchestration + deterministic fallback | ✅ |
| Bright Data client — geo residential proxy, Browser API CDP, SERP stub, mock fallback | ✅ |
| Evidence vault — S3 client for **MinIO (local) + Cloudflare R2 (prod)**, SHA-256 hashing | ✅ |
| Multi-provider LLM (Claude Opus 4.7 / Kimi / Azure / OpenAI / offline mock) | ✅ |
| Firecrawl + markitdown extraction | ✅ |
| Backend wiring: `POST /scan`, `GET /results`, `GET /evidence`, Redis worker | ✅ |
| docker-compose + MinIO, requirements, `.env.example`, offline smoke test | ✅ |
| **Law-Mapper agent** (pgvector over Matas's FTC taxonomy — currently light in Diff) | 🟡 |
| **Discovery agent** (Bright Data SERP + Firecrawl — client stubbed) | 🟡 |
| **Filing agent** (structured complaint JSON → hands to PDF) | ⬜ |
| Skyvern live checkout nav (Playwright/CDP seam in place) | 🟡 |
| changedetection.io diff engine, PaddleOCR, mem0 | ⬜ optional |
| Live Bright Data run vs real target sites + credit tracking | ⬜ (needs `.env` creds) |
| Architecture diagram + backup demo video + submission tags | ⬜ |

### Eman — Backend Engineer & DevOps
| Item | Status |
|---|---|
| FastAPI scaffold, CORS, routers | ✅ |
| Postgres schema + Alembic (scans, listings, fees, evidence_snapshots, complaints, fee_taxonomy/pgvector) | ✅ |
| Redis queue service | ✅ (now consumed by the worker) |
| docker-compose (db, redis) | ✅ (extended with MinIO) |
| Stripe checkout/webhook | 🟡 stub |
| **`POST /generate-complaint`** real implementation | ⬜ placeholder |
| **Class-action evidence-bundle ZIP** endpoint | ⬜ |
| **Populate `fee_taxonomy`** with Matas's clauses + embeddings | ⬜ |
| **Integration tests** across the pipeline | ⬜ |
| **Deploy** to Railway/Fly.io + live application URL | ⬜ |

> Handoff note for Eman: `POST /scan` now creates the row + enqueues; the worker
> runs the pipeline and writes `listings`/`fees`/`evidence_snapshots`. Your
> `/generate-complaint` can read those rows (+ `app/agents/types.py` shapes) to
> build the complaint; the evidence vault (`app/services/storage.py`) gives you
> presigned URLs and SHA-256 hashes for the PDF.

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
│   │   ├── crew.py          #   CrewAI orchestrator
│   │   ├── crawler.py       #   Crawler agent (geo-load listing)
│   │   ├── journey.py       #   Journey Simulator (walk checkout, stop pre-payment)
│   │   ├── diff.py          #   Diff agent (advertised vs final, junk-fee + FTC mapping)
│   │   ├── llm.py           #   multi-provider LLM (Claude/Kimi/OpenAI/mock)
│   │   ├── extract.py       #   HTML→markdown + price/fee parsing
│   │   └── types.py         #   shared dataclasses
│   ├── services/            # brightdata.py, storage.py (MinIO/R2), firecrawl_client.py, queue.py
│   └── worker.py            # Redis-queue consumer → runs the pipeline
├── scripts/smoke_two_geo.py # offline end-to-end demo test
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

Required environment variables:
- `DATABASE_URL`: PostgreSQL connection string with asyncpg driver
- `REDIS_URL`: Redis connection string
- `BRIGHTDATA_API_KEY`: BrightData API key for web scraping
- `MINIO_ENDPOINT`: MinIO server endpoint
- `MINIO_ACCESS_KEY`: MinIO access key
- `MINIO_SECRET_KEY`: MinIO secret key

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
- `POST /api/scan` - Initiate a new price monitoring scan
- `GET /api/results/{id}` - Retrieve scan results by ID
- `GET /api/evidence/{id}` - Retrieve evidence data by ID
- `POST /api/generate-complaint` - Generate a formal complaint document

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

- **Bright Data**: `BRIGHTDATA_CUSTOMER_ID`, `BRIGHTDATA_ZONE`, `BRIGHTDATA_ZONE_PASSWORD`
  (residential geo) and `BRIGHTDATA_BROWSER_ZONE`/`_PASSWORD` (Browser API).
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
  -d '{"url":"https://example.com/listing","states":["CA","TX"]}'
# → {"scan_id":"...","status":"queued"}
curl localhost:8000/api/results/<scan_id>
```

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