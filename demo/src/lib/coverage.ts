// Geographic coverage for FairPrice Watchdog — drives the world-map globe and
// the location pickers. The same violation pattern (advertised price ≠ checkout
// total) is enforced in all of these jurisdictions:
//
//   • US — FTC Junk Fees Rule (16 CFR Part 464) + FTC Act §5 + state UDAP
//   • UK — Digital Markets, Competition and Consumers Act 2024 (DMCCA)
//   • EU — Unfair Commercial Practices Directive 2005/29/EC + incoming Digital
//          Fairness Act, with Consumer Protection Cooperation (CPC) Network
//          coordinating sweeps across all 27 member states.

// [lon, lat] centroids. Used for globe rotation and pin placement.
export interface Coverage {
  code: string;
  name: string;
  region: "US" | "UK" | "EU";
  authority: string;          // primary enforcement framework
  coord: [number, number];
}

const US: Omit<Coverage, "region" | "authority">[] = [
  { code: "US",   name: "United States",     coord: [-98.0, 39.0] },
  { code: "CA",   name: "California",        coord: [-119.7, 36.8] },
  { code: "TX",   name: "Texas",             coord: [-99.0, 31.5] },
  { code: "NY",   name: "New York",          coord: [-75.5, 43.0] },
  { code: "FL",   name: "Florida",           coord: [-81.6, 27.9] },
  { code: "WA",   name: "Washington",        coord: [-120.7, 47.4] },
  { code: "GA",   name: "Georgia",           coord: [-83.6, 32.7] },
  { code: "IL",   name: "Illinois",          coord: [-89.2, 40.0] },
  { code: "AZ",   name: "Arizona",           coord: [-111.7, 34.3] },
  { code: "NV",   name: "Nevada",            coord: [-116.9, 38.8] },
  { code: "CO",   name: "Colorado",          coord: [-105.5, 39.0] },
];

const UK: Omit<Coverage, "region" | "authority">[] = [
  { code: "GB", name: "United Kingdom", coord: [-2.0, 54.0] },
];

// EU 27 — drip pricing is enforceable under the UCPD across all members. The
// Digital Fairness Act will extend total-price disclosure rules to every one.
const EU: Omit<Coverage, "region" | "authority">[] = [
  { code: "DE", name: "Germany",        coord: [10.5, 51.2] },
  { code: "FR", name: "France",         coord: [2.5, 46.5] },
  { code: "IT", name: "Italy",          coord: [12.6, 42.8] },
  { code: "ES", name: "Spain",          coord: [-3.7, 40.2] },
  { code: "NL", name: "Netherlands",    coord: [5.3, 52.2] },
  { code: "BE", name: "Belgium",        coord: [4.5, 50.6] },
  { code: "PL", name: "Poland",         coord: [19.4, 52.0] },
  { code: "SE", name: "Sweden",         coord: [16.0, 62.0] },
  { code: "FI", name: "Finland",        coord: [25.7, 62.0] },
  { code: "DK", name: "Denmark",        coord: [9.5, 56.0] },
  { code: "IE", name: "Ireland",        coord: [-8.0, 53.0] },
  { code: "PT", name: "Portugal",       coord: [-8.0, 39.4] },
  { code: "AT", name: "Austria",        coord: [14.5, 47.5] },
  { code: "CZ", name: "Czechia",        coord: [15.5, 49.8] },
  { code: "GR", name: "Greece",         coord: [22.0, 39.0] },
  { code: "HU", name: "Hungary",        coord: [19.0, 47.2] },
  { code: "RO", name: "Romania",        coord: [25.0, 46.0] },
  { code: "BG", name: "Bulgaria",       coord: [25.5, 42.7] },
  { code: "HR", name: "Croatia",        coord: [15.5, 45.1] },
  { code: "SK", name: "Slovakia",       coord: [19.5, 48.7] },
  { code: "SI", name: "Slovenia",       coord: [14.5, 46.1] },
  { code: "LT", name: "Lithuania",      coord: [23.9, 55.2] },
  { code: "LV", name: "Latvia",         coord: [25.0, 56.9] },
  { code: "EE", name: "Estonia",        coord: [25.6, 58.6] },
  { code: "CY", name: "Cyprus",         coord: [33.4, 35.1] },
  { code: "MT", name: "Malta",          coord: [14.4, 35.9] },
  { code: "LU", name: "Luxembourg",     coord: [6.1, 49.6] },
];

export const COVERAGE: Coverage[] = [
  ...US.map((x) => ({ ...x, region: "US" as const, authority: "FTC 16 CFR Part 464 / FTC Act §5 / state UDAP" })),
  ...UK.map((x) => ({ ...x, region: "UK" as const, authority: "UK DMCCA 2024 + CMA" })),
  ...EU.map((x) => ({ ...x, region: "EU" as const, authority: "EU UCPD 2005/29/EC + DFA + CPC Network" })),
];

const BY_CODE: Record<string, Coverage> = Object.fromEntries(COVERAGE.map((c) => [c.code, c]));

export function coverage(code: string): Coverage | undefined {
  return BY_CODE[code?.toUpperCase()];
}

export function geoCoord(code: string): [number, number] {
  return coverage(code)?.coord ?? [-98, 39];
}

export function geoName(code: string): string {
  return coverage(code)?.name ?? code;
}

export function isCountry(code: string): boolean {
  const c = coverage(code);
  return !!c && (c.region === "UK" || c.region === "EU" || c.code === "US");
}

export const US_STATES = COVERAGE.filter((c) => c.region === "US" && c.code !== "US");
export const ALL_COUNTRIES = COVERAGE.filter((c) => c.region === "UK" || c.region === "EU" || c.code === "US");

// Stats for the slide deck & the "coverage" pill in the UI.
export const COVERAGE_STATS = {
  countries: 1 + 1 + 27,   // US + UK + EU 27
  us_states: US.length - 1,
  jurisdictions: COVERAGE.length,
};
