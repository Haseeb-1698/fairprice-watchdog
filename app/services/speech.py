"""
speech.py — voice-to-text for the "voice scan" feature.

Lets a user speak a target instead of typing it. Uses a batch speech-to-text
provider: submit the recorded audio, poll until the job completes, return the
transcript. Short clips (a spoken URL / sector + locations) transcribe in a few
seconds.

Self-contained: raises a clear error if no key is configured so the route can
return a clean 503 and the UI can fall back to typing.
"""
from __future__ import annotations

import logging
import time

import requests

from app.core.config import settings

logger = logging.getLogger(__name__)


def is_live() -> bool:
    return bool(getattr(settings, "SPEECHMATICS_API_KEY", ""))


def transcribe(audio_bytes: bytes, filename: str = "clip.webm", language: str = "en",
               poll_timeout: int = 45) -> str:
    """
    Transcribe an audio clip to text. Submits a batch job, polls for completion,
    returns the plain-text transcript. Raises RuntimeError on failure.
    """
    if not is_live():
        raise RuntimeError("Speech-to-text not configured (set SPEECHMATICS_API_KEY)")

    base = settings.SPEECHMATICS_BATCH_URL.rstrip("/")
    headers = {"Authorization": f"Bearer {settings.SPEECHMATICS_API_KEY}"}
    config = (
        '{"type":"transcription",'
        f'"transcription_config":{{"language":"{language}","operating_point":"enhanced"}}}}'
    )

    # 1. Submit the job (multipart: config + audio file).
    resp = requests.post(
        f"{base}/jobs",
        headers=headers,
        files={
            "config": (None, config, "application/json"),
            "data_file": (filename, audio_bytes, "application/octet-stream"),
        },
        timeout=(15, 30),
    )
    resp.raise_for_status()
    job_id = resp.json()["id"]
    logger.info("[Speech] submitted job %s (%d bytes)", job_id, len(audio_bytes))

    # 2. Poll until done.
    deadline = time.time() + poll_timeout
    while time.time() < deadline:
        time.sleep(2)
        st = requests.get(f"{base}/jobs/{job_id}", headers=headers, timeout=(10, 20))
        st.raise_for_status()
        status = st.json().get("job", {}).get("status", "running")
        if status == "done":
            break
        if status in ("rejected", "deleted", "expired"):
            raise RuntimeError(f"transcription job {status}")

    # 3. Fetch the transcript as plain text.
    tr = requests.get(
        f"{base}/jobs/{job_id}/transcript",
        headers=headers,
        params={"format": "txt"},
        timeout=(10, 20),
    )
    tr.raise_for_status()
    text = tr.text.strip()
    logger.info("[Speech] job %s → %r", job_id, text[:120])
    return text
