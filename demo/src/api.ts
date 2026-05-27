import type { EvidenceSnapshot, ScanResults } from "./types";
import { mockEvidence, mockResults, toGeo } from "./lib/states";

export const API_BASE: string = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");
export const isLive = () => API_BASE.length > 0;

// Hard ceiling so the UI can NEVER hang forever (backend caps a scan at ~180s/state).
const MAX_POLL_MS = 210_000;
const POLL_INTERVAL_MS = 2500;
const REQ_TIMEOUT_MS = 12_000;

class ApiError extends Error {}

async function req(path: string, init?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    signal: AbortSignal.timeout(REQ_TIMEOUT_MS),
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new ApiError(`${path} → HTTP ${res.status}`);
  return res;
}

export async function startScan(url: string, states: string[]): Promise<string> {
  const res = await req("/api/scan", {
    method: "POST",
    body: JSON.stringify({ url, geos: states.map(toGeo) }),
  });
  const data = await res.json();
  return data.id ?? data.scan_id;
}

export interface PollHandle {
  onTick?: (elapsedSec: number, status: string) => void;
  signal?: AbortSignal;
}

/** Poll results until completed/failed or listings appear, with a hard time cap. */
export async function pollResults(scanId: string, h: PollHandle = {}): Promise<ScanResults> {
  const started = Date.now();
  let lastStatus = "queued";
  while (true) {
    if (h.signal?.aborted) throw new ApiError("cancelled");
    const elapsed = Date.now() - started;
    if (elapsed > MAX_POLL_MS) {
      throw new ApiError("timeout"); // caller decides how to surface
    }
    try {
      const res = await req(`/api/results/${scanId}`);
      const data: ScanResults = await res.json();
      lastStatus = data.scan?.status || lastStatus;
      h.onTick?.(Math.round(elapsed / 1000), lastStatus);
      const done = lastStatus === "completed" || lastStatus === "failed";
      if (done || (data.listings && data.listings.length > 0)) return data;
    } catch (e) {
      if (e instanceof ApiError && e.message === "cancelled") throw e;
      // transient network/timeout on one poll — keep going, surface via tick
      h.onTick?.(Math.round(elapsed / 1000), lastStatus);
    }
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
}

export async function getEvidence(scanId: string): Promise<EvidenceSnapshot[]> {
  try {
    const res = await req(`/api/evidence/${scanId}`);
    const data = await res.json();
    const items = Array.isArray(data) ? data : data.snapshots || [];
    return items.map((s: any) => ({
      id: s.id,
      scan_id: s.scan_id,
      sha256_hash: s.sha256_hash,
      timestamp: s.timestamp,
      storage_path: s.storage_path,
      state: s.state ?? null,
    }));
  } catch {
    return [];
  }
}

/** Trigger the evidence-bundle. Returns a blob URL (ZIP) or a link if the API returns JSON. */
export async function generateComplaint(scanId: string): Promise<{ kind: "blob" | "link"; url: string }> {
  const res = await req(`/api/generate-complaint/${scanId}`, { method: "POST" });
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const data = await res.json();
    return { kind: "link", url: data.complaint_url || data.url || "#" };
  }
  const blob = await res.blob();
  return { kind: "blob", url: URL.createObjectURL(blob) };
}

// ── Demo fallbacks (no backend, or backend unreachable) ──────────────────────
export function demoResults(url: string, states: string[]): ScanResults {
  return mockResults(url, states);
}
export function demoEvidence(states: string[]): EvidenceSnapshot[] {
  return mockEvidence(states);
}
