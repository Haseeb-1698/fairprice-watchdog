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
│   │       ├── scan.py      # POST /api/scan
│   │       ├── results.py   # GET /api/results/{id}
│   │       ├── evidence.py  # GET /api/evidence/{id}
│   │       └── complaint.py # POST /api/generate-complaint
│   ├── models/              # SQLAlchemy ORM models
│   ├── schemas/             # Pydantic request/response schemas
│   └── services/            # Business logic services
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