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
