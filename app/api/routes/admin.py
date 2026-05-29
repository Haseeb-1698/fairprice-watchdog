"""
Admin endpoints — manual recovery actions for the live demo.

POST /api/admin/reset
    Flushes the scan + hunt Redis queues, deletes per-scan event streams, and
    kicks any stuck worker so a fresh one re-launches from supervisor or the
    next manual launch (worker autorestarts via the wrapper script when run
    under setsid).

POST /api/admin/restart-worker
    Same as reset, but ALSO best-effort kills the worker process so the next
    BLPOP loop picks up cleanly.

Light protection: requires ADMIN_TOKEN env var match if set (so the public
demo URL can't be hammered). When unset, accepts any request (dev/test).
"""
import logging
import os
import signal
import subprocess
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from app.services.queue import get_redis_client

router = APIRouter()
logger = logging.getLogger(__name__)


def _check_token(provided: Optional[str]) -> None:
    expected = os.environ.get("ADMIN_TOKEN", "").strip()
    if not expected:
        return  # no token configured = open (demo / dev)
    if (provided or "").strip() != expected:
        raise HTTPException(status_code=401, detail="invalid admin token")


async def _flush_queues_and_events() -> dict:
    """Delete the queues + per-scan event streams. Returns counts."""
    redis = await get_redis_client()
    scan_q = await redis.llen("scan_queue")
    hunt_q = await redis.llen("hunt_queue")
    await redis.delete("scan_queue", "hunt_queue")
    # Delete every scan:{id}:events key (the studio feed streams).
    event_keys: list[str] = []
    async for k in redis.scan_iter(match="scan:*:events"):
        event_keys.append(k)
    if event_keys:
        await redis.delete(*event_keys)
    return {
        "scan_queue_cleared": scan_q,
        "hunt_queue_cleared": hunt_q,
        "event_streams_cleared": len(event_keys),
    }


def _kill_worker() -> int:
    """Best-effort: kill any running worker processes. Returns kill count.
    Worker process restarts itself if running under nohup/setsid + a watcher,
    or stays dead until the operator relaunches — we surface that in the response."""
    killed = 0
    try:
        out = subprocess.run(
            ["pgrep", "-f", "python.*-m app.worker"],
            capture_output=True, text=True, timeout=5,
        )
        for pid_str in out.stdout.split():
            try:
                pid = int(pid_str)
                os.kill(pid, signal.SIGKILL)
                killed += 1
            except (ProcessLookupError, ValueError, PermissionError):
                continue
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return killed


def _worker_alive() -> bool:
    try:
        out = subprocess.run(
            ["pgrep", "-f", "python.*-m app.worker"],
            capture_output=True, text=True, timeout=3,
        )
        return bool(out.stdout.strip())
    except Exception:
        return False


def _relaunch_worker() -> bool:
    """Launch a detached worker. Best-effort — returns True if pgrep sees it
    within ~5 seconds. The detached process survives this API request returning."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    py = os.path.join(repo_root, "venv", "bin", "python")
    if not os.path.isfile(py):
        py = "python3"
    worker_log = os.path.join(repo_root, "worker.log")
    try:
        with open(worker_log, "ab") as logf:
            subprocess.Popen(
                [py, "-u", "-m", "app.worker"],
                cwd=repo_root,
                stdout=logf,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,  # detach from this process
            )
    except Exception as e:
        logger.warning("worker relaunch failed: %s", e)
        return False
    # Give it ~5s to come up
    for _ in range(10):
        if _worker_alive():
            return True
        time.sleep(0.5)
    return False


@router.post("/admin/reset")
async def admin_reset(x_admin_token: Optional[str] = Header(default=None)) -> dict:
    """Flush all queues + event streams. Does not touch the DB."""
    _check_token(x_admin_token)
    summary = await _flush_queues_and_events()
    return {"ok": True, **summary, "worker_alive": _worker_alive()}


@router.post("/admin/restart-worker")
async def admin_restart_worker(x_admin_token: Optional[str] = Header(default=None)) -> dict:
    """Kill the worker, flush queues, attempt to relaunch a fresh worker.
    Falls back to 'manual restart needed' if the relaunch couldn't be confirmed."""
    _check_token(x_admin_token)
    killed = _kill_worker()
    time.sleep(1)  # give processes a moment to release sockets
    summary = await _flush_queues_and_events()
    relaunched = _relaunch_worker()
    return {
        "ok": True,
        "workers_killed": killed,
        **summary,
        "worker_relaunched": relaunched,
        "worker_alive": _worker_alive(),
    }


@router.get("/admin/status")
async def admin_status() -> dict:
    """Public health snapshot (no token needed) — drives the UI badge."""
    redis = await get_redis_client()
    return {
        "worker_alive": _worker_alive(),
        "scan_queue": await redis.llen("scan_queue"),
        "hunt_queue": await redis.llen("hunt_queue"),
    }
