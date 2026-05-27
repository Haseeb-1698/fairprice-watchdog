import type { EvidenceSnapshot, Listing, ScanResults } from "../types";

export const US_STATES: Record<string, string> = {
  CA: "California",
  TX: "Texas",
  NY: "New York",
  FL: "Florida",
  WA: "Washington",
  GA: "Georgia",
  IL: "Illinois",
  AZ: "Arizona",
  NV: "Nevada",
  CO: "Colorado",
};

export const stateName = (code: string) => US_STATES[code?.toUpperCase()] || code;

// Approximate centroid [lon, lat] per state — drives the globe rotation + pins.
export const STATE_COORDS: Record<string, [number, number]> = {
  CA: [-119.7, 36.8], TX: [-99.0, 31.5], NY: [-75.5, 43.0], FL: [-81.6, 27.9],
  WA: [-120.7, 47.4], GA: [-83.6, 32.7], IL: [-89.2, 40.0], AZ: [-111.7, 34.3],
  NV: [-116.9, 38.8], CO: [-105.5, 39.0],
};
export const stateCoord = (code: string): [number, number] => STATE_COORDS[code?.toUpperCase()] || [-98, 39];

// Geo-name form the API's ScanCreate expects (e.g. "california").
export const toGeo = (code: string) => stateName(code).toLowerCase();

// ── Deterministic, state-varying mock (mirrors the backend's offline mock) ──
const FACTOR: Record<string, number> = {
  CA: 1.0, NY: 1.08, TX: 0.84, FL: 0.92, WA: 1.04,
  GA: 0.88, IL: 0.97, AZ: 0.86, NV: 0.9, CO: 0.95,
};

const factor = (code: string) => FACTOR[code?.toUpperCase()] ?? 0.95;

const FEE_TEMPLATES: Array<[string, number, string, string]> = [
  ["Mandatory Resort Fee", 149, "resort", "16 CFR §464.2(a) — mandatory resort fee omitted from the advertised total price"],
  ["Cleaning Fee", 95, "cleaning", "16 CFR §464.2(a) — mandatory cleaning fee drip-priced after the advertised total"],
  ["Application/Admin Fee", 199, "admin", "16 CFR §464.2(a) — undisclosed mandatory administrative fee"],
  ["Mandatory Service Charge", 89, "service", "16 CFR §464.2(a) — mandatory service fee excluded from the advertised total price"],
];

export function mockListing(code: string): Listing {
  const f = factor(code);
  const advertised = Math.round(1995 * f * 100) / 100;
  const fees = FEE_TEMPLATES.map(([fee_name, base, fee_type, ftc_clause]) => ({
    fee_name,
    fee_amount: Math.round(base * f * 100) / 100,
    fee_type,
    is_junk_fee: true,
    ftc_clause,
  }));
  const final = Math.round((advertised + fees.reduce((s, x) => s + x.fee_amount, 0)) * 100) / 100;
  return { location_state: code.toUpperCase(), advertised_price: advertised, final_price: final, fees };
}

export function mockResults(url: string, states: string[]): ScanResults {
  return {
    scan: { id: "demo-" + Math.random().toString(36).slice(2, 8), url, status: "completed", geos: states.map(toGeo) },
    listings: states.map(mockListing),
  };
}

export function mockEvidence(states: string[]): EvidenceSnapshot[] {
  // Stable-looking pseudo hashes for the demo.
  const hash = (s: string) => {
    let h = 0;
    for (const c of s) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return (h.toString(16) + "a3f9c0114bd7e2685fce10d4427b9").padEnd(64, "0").slice(0, 64);
  };
  return states.map((code, i) => ({
    id: "ev-" + i,
    scan_id: "demo",
    sha256_hash: hash("snapshot-" + code),
    timestamp: new Date().toISOString(),
    state: code.toUpperCase(),
    storage_path: `s3://fairprice-evidence/demo/${code.toUpperCase()}/checkout.html`,
  }));
}
