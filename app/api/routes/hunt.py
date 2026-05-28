"""
Hunt endpoints — agent-led target discovery + scan.

GET  /api/hunts/presets       — available hunt presets
POST /api/hunts/start         — start a new hunt
GET  /api/hunts/{hunt_id}     — poll hunt status + progressive results
"""
from fastapi import APIRouter, HTTPException

from app.agents.hunt import HUNT_PRESETS, HuntOrchestrator
from app.schemas import HuntStartRequest, HuntStatusResponse
from app.services.queue import get_redis_client
import json

router = APIRouter()


@router.get("/hunts/presets")
async def get_hunt_presets() -> dict:
    """Return available hunt presets with labels, icons, and defaults."""
    presets = [
        {
            "id": p["id"],
            "label": p["label"],
            "icon": p["icon"],
            "description": p["description"],
            "default_city": p["default_city"],
            "default_locations": p["default_locations"],
            "demo_reliability": p["demo_reliability"],
        }
        for p in HUNT_PRESETS.values()
    ]
    return {"presets": presets}


@router.post("/hunts/start")
async def start_hunt(body: HuntStartRequest) -> dict:
    """Start a new agent-led hunt for the given sector."""
    if body.sector not in HUNT_PRESETS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown sector '{body.sector}'. Valid: {list(HUNT_PRESETS)}",
        )

    orchestrator = HuntOrchestrator()
    hunt_id = await orchestrator.start_hunt(
        sector=body.sector,
        city=body.city,
        locations=body.locations,
    )
    return {"hunt_id": hunt_id, "status": "queued"}


@router.get("/hunts/{hunt_id}", response_model=HuntStatusResponse)
async def get_hunt_status(hunt_id: str) -> HuntStatusResponse:
    """Poll hunt status and progressive results."""
    redis = await get_redis_client()
    raw = await redis.get(f"hunt:{hunt_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Hunt not found")
    data = json.loads(raw)
    return HuntStatusResponse(
        id=data.get("id", hunt_id),
        sector=data.get("sector", ""),
        label=data.get("label", ""),
        city=data.get("city", ""),
        locations=data.get("locations", []),
        status=data.get("status", "unknown"),
        phase=data.get("phase", ""),
        candidates=data.get("candidates", []),
        scout_results=data.get("scout_results", []),
        scan_ids=data.get("scan_ids", []),
        results=data.get("results", []),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
    )
