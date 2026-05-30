"""
FairPrice Watchdog - Main FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import scan, results, evidence, complaint, stripe, hunt, events, admin, voice
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
app.include_router(hunt.router, prefix="/api", tags=["hunts"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(voice.router, prefix="/api", tags=["voice"])

# Serve the built demo UI at /app (if present) — reuses the API's open port so
# the demo is reachable without opening another firewall port. Guarded so the
# app still starts when demo/dist hasn't been built.
import os as _os
from fastapi.staticfiles import StaticFiles

_demo_dist = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "demo", "dist")
if _os.path.isdir(_demo_dist):
    app.mount("/app", StaticFiles(directory=_demo_dist, html=True), name="demo")


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
