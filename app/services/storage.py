"""
storage.py — S3-compatible evidence vault for FairPrice Watchdog.

One client, two backends (chosen by settings.STORAGE_BACKEND):
  • minio  — local MinIO in docker-compose (default for dev)
  • r2     — Cloudflare R2 (zero-egress cloud storage for the deployed demo)

Both speak the S3 API, so a single boto3 client serves either by swapping the
endpoint + credentials. Every captured snapshot is SHA-256 hashed and keyed by
that hash → the hash chain that makes the evidence court-ready (PRD §5.4).

Degrades gracefully: if boto3/creds are unavailable it writes to a local
./evidence_store directory so the pipeline never breaks during a demo.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_LOCAL_FALLBACK_DIR = Path(os.environ.get("EVIDENCE_LOCAL_DIR", "./evidence_store"))
_client = None
_resolved_backend: Optional[str] = None


@dataclass
class StoredSnapshot:
    """Receipt for a stored evidence snapshot."""
    sha256: str
    storage_path: str                 # s3://bucket/key  or  file://...
    public_url: Optional[str]
    backend: str                      # minio | r2 | local
    timestamp: datetime
    size: int


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ── Client resolution ─────────────────────────────────────────────────────────

def _bucket() -> str:
    return settings.R2_BUCKET if settings.STORAGE_BACKEND == "r2" else settings.MINIO_BUCKET


def _get_client():
    """Lazy-init a boto3 S3 client for the configured backend. None on failure."""
    global _client, _resolved_backend
    if _client is not None:
        return _client
    try:
        import boto3
        from botocore.config import Config

        backend = settings.STORAGE_BACKEND.lower()
        if backend == "r2":
            if not (settings.R2_ACCOUNT_ID and settings.R2_ACCESS_KEY_ID and settings.R2_SECRET_ACCESS_KEY):
                logger.warning("R2 selected but credentials incomplete — using local fallback")
                return None
            endpoint = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
            _client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name="auto",
                config=Config(signature_version="s3v4"),
            )
        else:  # minio (default)
            scheme = "https" if settings.MINIO_SECURE else "http"
            endpoint = f"{scheme}://{settings.MINIO_ENDPOINT}"
            _client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=settings.MINIO_SECRET_KEY,
                region_name="us-east-1",
                config=Config(signature_version="s3v4"),
            )

        _resolved_backend = backend
        _ensure_bucket(_client, _bucket())
        logger.info("Evidence vault ready: backend=%s endpoint=%s bucket=%s", backend, endpoint, _bucket())
        return _client
    except ImportError:
        logger.warning("boto3 not installed — evidence vault using local fallback")
        return None
    except Exception as e:
        logger.warning("Evidence vault unavailable (%s) — using local fallback", e)
        return None


def _ensure_bucket(client, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        try:
            client.create_bucket(Bucket=bucket)
            logger.info("Created bucket: %s", bucket)
        except Exception as e:
            logger.debug("Bucket ensure skipped for %s: %s", bucket, e)


# ── Public API ────────────────────────────────────────────────────────────────

def store_snapshot(scan_id: str, state: str, html: str, step: str = "checkout") -> StoredSnapshot:
    """
    Store an HTML evidence snapshot. Key = {scan_id}/{state}/{step}-{sha256}.html
    Returns a StoredSnapshot with the SHA-256 hash for the evidence chain.
    """
    data = html.encode("utf-8", errors="ignore")
    digest = sha256_hex(data)
    key = f"{scan_id}/{state}/{step}-{digest[:16]}.html"
    ts = datetime.now(timezone.utc)

    client = _get_client()
    if client is not None:
        try:
            client.put_object(
                Bucket=_bucket(),
                Key=key,
                Body=data,
                ContentType="text/html; charset=utf-8",
                Metadata={"sha256": digest, "scan_id": scan_id, "state": state, "step": step},
            )
            return StoredSnapshot(
                sha256=digest,
                storage_path=f"s3://{_bucket()}/{key}",
                public_url=_public_url(key),
                backend=_resolved_backend or settings.STORAGE_BACKEND,
                timestamp=ts,
                size=len(data),
            )
        except Exception as e:
            logger.warning("Snapshot upload failed (%s) — local fallback", e)

    # Local fallback
    path = _LOCAL_FALLBACK_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return StoredSnapshot(
        sha256=digest,
        storage_path=f"file://{path.resolve()}",
        public_url=None,
        backend="local",
        timestamp=ts,
        size=len(data),
    )


def store_json(scan_id: str, name: str, payload: dict) -> StoredSnapshot:
    """Store a JSON artifact (e.g. structured complaint / evidence bundle manifest)."""
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    digest = sha256_hex(data)
    key = f"{scan_id}/{name}"
    ts = datetime.now(timezone.utc)

    client = _get_client()
    if client is not None:
        try:
            client.put_object(Bucket=_bucket(), Key=key, Body=data, ContentType="application/json")
            return StoredSnapshot(digest, f"s3://{_bucket()}/{key}", _public_url(key),
                                  _resolved_backend or settings.STORAGE_BACKEND, ts, len(data))
        except Exception as e:
            logger.warning("JSON upload failed (%s) — local fallback", e)

    path = _LOCAL_FALLBACK_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return StoredSnapshot(digest, f"file://{path.resolve()}", None, "local", ts, len(data))


def presigned_url(key: str, expires_hours: int = 24) -> Optional[str]:
    """Generate a presigned GET URL (works on both MinIO and R2)."""
    client = _get_client()
    if client is None:
        return None
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket(), "Key": key},
            ExpiresIn=int(timedelta(hours=expires_hours).total_seconds()),
        )
    except Exception as e:
        logger.warning("presigned_url failed for %s: %s", key, e)
        return None


def _public_url(key: str) -> Optional[str]:
    """Direct public URL when an R2 public/custom domain is configured."""
    if settings.STORAGE_BACKEND == "r2" and settings.R2_PUBLIC_BASE_URL:
        return f"{settings.R2_PUBLIC_BASE_URL.rstrip('/')}/{key}"
    return None
