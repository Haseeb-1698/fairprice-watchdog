# FairPrice Watchdog API

A FastAPI-based backend service for monitoring and detecting unfair pricing practices.

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
│   │       ├── scan.py      # POST /api/scan, GET /api/scan/{id}
│   │       ├── results.py   # GET /api/results/{id}
│   │       ├── evidence.py  # GET /api/evidence/{id}
│   │       ├── complaint.py # POST /api/generate-complaint/{id}
│   │       └── stripe.py    # Stripe payment endpoints
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   └── services/
│       ├── queue.py         # Redis queue service
│       ├── evidence.py      # Evidence storage service
│       └── bundle.py        # Evidence bundle generation
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
- `GET /api/scan/{scan_id}` - Get scan status by ID
- `GET /api/results/{scan_id}` - Retrieve complete scan results with listings and fees
- `GET /api/evidence/{scan_id}` - Retrieve evidence snapshots by scan ID
- `POST /api/generate-complaint/{scan_id}` - Generate and download evidence bundle ZIP file

### Evidence Bundle
The `/api/generate-complaint/{scan_id}` endpoint generates a comprehensive ZIP file containing:
- **scan_summary.json**: Complete scan details, listings, and fees
- **evidence/{snapshot_id}.html**: All HTML evidence snapshots
- **manifest.json**: SHA256 hashes of all files for integrity verification

This bundle is designed for class-action lawsuits and regulatory complaints.

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

## Development

### Running Tests

Run all integration tests:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run specific test:
```bash
pytest tests/test_api.py::test_health_check
```

See `tests/README.md` for more details on the test suite.

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