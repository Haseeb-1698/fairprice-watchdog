import type { EvidenceSnapshot, HuntPreset, HuntStatus, HuntScanResult, ScanResults } from "./types";
import { mockEvidence, mockListing, mockResults, toGeo } from "./lib/states";

export const API_BASE: string = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");
export const isLive = () => API_BASE.length > 0;

// Hard ceiling so the UI can NEVER hang forever. Backend caps each state at
// 300s; 2 states run in parallel; UI ceiling = 300s + 60s buffer = 360s.
const MAX_POLL_MS = 360_000;
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
  // Send canonical codes (CA/TX/GB/DE/...) — the backend normalizes either form,
  // but uppercase codes round-trip cleanly through the proxy username builder.
  const res = await req("/api/scan", {
    method: "POST",
    body: JSON.stringify({ url, geos: states.map((s) => s.toUpperCase()) }),
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

// ── Hunt API ──────────────────────────────────────────────────────────────────

const DEMO_HUNT_PRESETS: HuntPreset[] = [
  { id: "hotels", label: "Hotel Resort Fee Hunt", icon: "hotel",
    description: "Find hotels hiding mandatory resort/destination fees.", default_city: "Las Vegas",
    default_locations: ["CA", "TX"], demo_reliability: "Best" },
  { id: "rentals", label: "Apartment Junk Fee Hunt", icon: "home",
    description: "Hunt apartment listings for hidden application and admin fees.", default_city: "Atlanta",
    default_locations: ["CA", "TX"], demo_reliability: "Good" },
  { id: "car_rental", label: "Car Rental Surcharge Hunt", icon: "car",
    description: "Expose hidden surcharges in car rentals.", default_city: "Miami",
    default_locations: ["NY", "FL"], demo_reliability: "Medium" },
  { id: "tickets", label: "Ticket Service Fee Hunt", icon: "ticket",
    description: "Track service fees through ticket checkout.", default_city: "New York",
    default_locations: ["CA", "NY"], demo_reliability: "Experimental" },
  { id: "retail", label: "Online Retail Drip Pricing Hunt", icon: "shopping-cart",
    description: "Detect drip pricing and surprise checkout fees.", default_city: "Chicago",
    default_locations: ["CA", "IL"], demo_reliability: "Experimental" },
];

export async function getHuntPresets(): Promise<HuntPreset[]> {
  if (!isLive()) return DEMO_HUNT_PRESETS;
  try {
    const res = await req("/api/hunts/presets");
    const data = await res.json();
    return data.presets ?? DEMO_HUNT_PRESETS;
  } catch {
    return DEMO_HUNT_PRESETS;
  }
}

export async function startHunt(sector: string, city: string, locations: string[]): Promise<string> {
  const res = await req("/api/hunts/start", {
    method: "POST",
    body: JSON.stringify({ sector, city, locations }),
  });
  const data = await res.json();
  return data.hunt_id;
}

const MAX_HUNT_POLL_MS = 720_000; // hunts can have multiple scans queued (5x300s + scout + serp)

export async function pollHuntStatus(huntId: string, h: PollHandle = {}): Promise<HuntStatus> {
  const started = Date.now();
  let lastStatus = "queued";
  while (true) {
    if (h.signal?.aborted) throw new ApiError("cancelled");
    const elapsed = Date.now() - started;
    if (elapsed > MAX_HUNT_POLL_MS) throw new ApiError("timeout");
    try {
      const res = await req(`/api/hunts/${huntId}`);
      const data: HuntStatus = await res.json();
      lastStatus = data.status;
      h.onTick?.(Math.round(elapsed / 1000), lastStatus);
      if (lastStatus === "completed" || lastStatus === "failed") return data;
      // Progressive: return partial data if we have results coming in
      if (data.results && data.results.length > 0 && lastStatus === "scanning") {
        h.onTick?.(Math.round(elapsed / 1000), lastStatus);
      }
    } catch (e) {
      if (e instanceof ApiError && e.message === "cancelled") throw e;
      h.onTick?.(Math.round(elapsed / 1000), lastStatus);
    }
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }
}

// ── Voice scan (speech-to-text) ──────────────────────────────────────────────

export interface VoiceIntent {
  ok: boolean;
  transcript: string;
  url?: string;
  sector?: string;
  locations?: string[];
}

export async function transcribeVoice(audio: Blob): Promise<VoiceIntent> {
  const form = new FormData();
  form.append("audio", audio, "clip.webm");
  const res = await fetch(`${API_BASE}/api/voice/transcribe`, {
    method: "POST",
    body: form,
    signal: AbortSignal.timeout(60_000),
  });
  if (!res.ok) throw new ApiError(`voice → HTTP ${res.status}`);
  return await res.json();
}

// ── Admin: reset / restart worker (manual recovery for live demo) ────────────

export interface AdminStatus {
  worker_alive: boolean;
  scan_queue: number;
  hunt_queue: number;
}

export async function adminStatus(): Promise<AdminStatus | null> {
  if (!isLive()) return null;
  try {
    const res = await req("/api/admin/status");
    return await res.json();
  } catch {
    return null;
  }
}

export async function adminRestartWorker(): Promise<any> {
  const res = await req("/api/admin/restart-worker", {
    method: "POST",
    headers: localStorage.getItem("admin_token")
      ? { "X-Admin-Token": localStorage.getItem("admin_token") as string }
      : {},
  });
  return await res.json();
}

/** Generate a mock hunt result for demo mode with a simulated delay. */
export function demoHuntStatus(sector: string, city: string, locations: string[]): HuntStatus {
  const label = DEMO_HUNT_PRESETS.find((p) => p.id === sector)?.label ?? "Hunt";
  const [a, b] = locations.length >= 2 ? [locations[0], locations[1]] : ["CA", "TX"];
  const sectors: Record<string, string[]> = {
    hotels: ["Grand Summit Resort", "City Center Hotel", "Coastal Inn & Suites"],
    rentals: ["Parkview Apartments", "Downtown Lofts LLC", "Metro Living Rentals"],
    car_rental: ["Premier Car Rentals", "FastDrive Autos", "City Wheels"],
    tickets: ["EventHub", "TicketPlus", "ShowTime Tickets"],
    retail: ["ShopNow.com", "DealMart", "QuickBuy"],
  };
  const names = sectors[sector] ?? ["Target A", "Target B", "Target C"];

  const candidates = names.map((name, i) => ({
    title: name, url: `https://${name.toLowerCase().replace(/\s+/g, "-")}.com/`, source: "mock_serp",
  }));

  const scoutResults = candidates.map((c, i) => ({
    url: c.url, title: c.title, reachable: true, blocked: false,
    has_prices: true, has_fee_keywords: true,
    score: [0.95, 0.82, 0.41][i] ?? 0.5, source: "mock", eligible: i < 2,
  }));

  const mockScanResult = (name: string, url: string): HuntScanResult => ({
    scan_id: `demo-${Math.random().toString(36).slice(2, 8)}`,
    url, title: name, honesty_label: "mock_fallback",
    summary: `Demo fixture — ${a} $2,527.00 vs ${b} $2,122.68 — $404.32 (19%) geo gap.`,
    listings: [mockListing(a), mockListing(b)],
  });

  return {
    id: `demo-hunt-${sector}`, sector, label, city,
    locations: [a, b],
    status: "completed", phase: "done",
    candidates,
    scout_results: scoutResults,
    scan_ids: [],
    results: [mockScanResult(names[0], candidates[0].url), mockScanResult(names[1], candidates[1].url)],
    created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
  };
}
