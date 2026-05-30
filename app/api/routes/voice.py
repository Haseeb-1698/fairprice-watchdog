"""
Voice endpoints — speech-to-text "voice scan" feature.

POST /api/voice/transcribe   — upload an audio clip, get back the transcript
                               plus a best-effort parse into scan intent
                               (URL or sector + locations).
"""
import logging
import re

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services import speech

router = APIRouter()
logger = logging.getLogger(__name__)

# Spoken location words → canonical codes.
_SPOKEN_GEO = {
    "california": "CA", "texas": "TX", "new york": "NY", "florida": "FL",
    "washington": "WA", "georgia": "GA", "illinois": "IL", "arizona": "AZ",
    "nevada": "NV", "colorado": "CO",
    "united kingdom": "GB", "uk": "GB", "britain": "GB", "england": "GB",
    "germany": "DE", "france": "FR", "italy": "IT", "spain": "ES",
    "netherlands": "NL", "ireland": "IE", "poland": "PL", "sweden": "SE",
}
_SECTORS = ("hotels", "rentals", "car_rental", "tickets", "retail")


def _parse_intent(text: str) -> dict:
    """Best-effort: pull a URL or sector + two locations out of spoken text."""
    t = text.lower()
    intent: dict = {"transcript": text}

    # URL (spoken "dot com" or a real domain)
    url_match = re.search(r"(https?://\S+|[\w-]+\.(?:com|org|net|io|co|de|uk)\S*)", t)
    if "dot com" in t or "dot org" in t:
        spoken = re.sub(r"\s+dot\s+", ".", t)
        url_match = re.search(r"([\w-]+\.(?:com|org|net|io|co|de|uk)\S*)", spoken) or url_match
    if url_match:
        u = url_match.group(1)
        intent["url"] = u if u.startswith("http") else f"https://{u}"

    # Sector
    for s in _SECTORS:
        if s.replace("_", " ") in t or s in t:
            intent["sector"] = s
            break
    if "hotel" in t and "sector" not in intent:
        intent["sector"] = "hotels"
    if ("car" in t or "rental car" in t) and "sector" not in intent:
        intent["sector"] = "car_rental"
    if "ticket" in t and "sector" not in intent:
        intent["sector"] = "tickets"

    # Locations (first two matches, in order)
    found: list[str] = []
    for name, code in _SPOKEN_GEO.items():
        idx = t.find(name)
        if idx >= 0:
            found.append((idx, code))
    found.sort()
    locs = []
    for _, code in found:
        if code not in locs:
            locs.append(code)
    if len(locs) >= 2:
        intent["locations"] = locs[:2]

    return intent


@router.post("/voice/transcribe")
async def voice_transcribe(audio: UploadFile = File(...)) -> dict:
    if not speech.is_live():
        raise HTTPException(status_code=503, detail="Voice transcription not configured")
    try:
        data = await audio.read()
        if not data:
            raise HTTPException(status_code=400, detail="empty audio")
        text = speech.transcribe(data, filename=audio.filename or "clip.webm")
        return {"ok": True, **_parse_intent(text)}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("voice transcribe failed: %s", e)
        raise HTTPException(status_code=500, detail=f"transcription failed: {e}")
