// Mirrors the FairPrice Watchdog API response shapes (FastAPI / Pydantic).

export interface Fee {
  id?: string;
  fee_name: string;
  fee_amount: number;
  fee_type: string;
  is_junk_fee: boolean;
  ftc_clause?: string | null;
}

export interface Listing {
  id?: string;
  location_state: string; // e.g. "CA"
  advertised_price: number;
  final_price: number;
  fees: Fee[];
}

export interface ScanMeta {
  id: string;
  url: string;
  status: string; // queued | processing | completed | failed
  created_at?: string;
  geos?: string[];
}

export interface ScanResults {
  scan: ScanMeta;
  listings: Listing[];
}

export interface EvidenceSnapshot {
  id: string;
  scan_id: string;
  sha256_hash: string;
  timestamp?: string;
  storage_path?: string | null;
  state?: string | null;
}

// UI-side derived comparison between two states.
export interface GeoComparison {
  high: Listing;
  low: Listing;
  delta: number;
  pct: number;
}

// ── Hunt types ────────────────────────────────────────────────────────────────

export type HonestyLabel = "live_verified" | "live_partial" | "mock_fallback" | "blocked";

export interface HuntPreset {
  id: string;
  label: string;
  icon: string;
  description: string;
  default_city: string;
  default_locations: string[];
  demo_reliability: string;
}

export interface HuntCandidate {
  title: string;
  url: string;
  source: string;
}

export interface ScoutResult {
  url: string;
  title: string;
  reachable: boolean;
  blocked: boolean;
  has_prices: boolean;
  has_fee_keywords: boolean;
  score: number;
  source: string;
  eligible?: boolean;
}

export interface HuntScanResult {
  scan_id: string;
  url: string;
  title: string;
  honesty_label: HonestyLabel;
  summary: string;
  listings: Listing[];
}

export interface HuntStatus {
  id: string;
  sector: string;
  label: string;
  city: string;
  locations: string[];
  status: "queued" | "discovering" | "scouting" | "scanning" | "completed" | "failed";
  phase: string;
  candidates: HuntCandidate[];
  scout_results: ScoutResult[];
  scan_ids: string[];
  results: HuntScanResult[];
  created_at: string;
  updated_at: string;
}
