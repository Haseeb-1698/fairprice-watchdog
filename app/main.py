"""
FairPrice Watchdog - Main FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import scan, results, evidence, complaint, stripe
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    print(f"🚀 Starting {settings.APP_NAME}...")
    print(f"📊 Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'Not configured'}")
    print(f"🔴 Redis: {settings.REDIS_URL}")
    print(f"📦 MinIO: {settings.MINIO_ENDPOINT}")
    
    yield
    
    # Shutdown
    print(f"🛑 Shutting down {settings.APP_NAME}...")


# Create FastAPI application
app = FastAPI(
    title="FairPrice Watchdog",
    description="API for monitoring and detecting unfair pricing practices",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware - Allow all origins for hackathon
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(scan.router, prefix="/api", tags=["scan"])
app.include_router(results.router, prefix="/api", tags=["results"])
app.include_router(evidence.router, prefix="/api", tags=["evidence"])
app.include_router(complaint.router, prefix="/api", tags=["complaint"])
app.include_router(stripe.router, prefix="/api", tags=["stripe"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "ok",
        "app": "FairPrice Watchdog"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Made with Bob
