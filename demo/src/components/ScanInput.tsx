import { useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Search, MapPin, Zap, Globe2 } from "lucide-react";
import { US_STATES, geoName, COVERAGE } from "../lib/coverage";
import WorldMap from "./WorldMap";

// Selectable jurisdictions grouped for the dropdown: US states, then UK, then EU 27.
const UK_COUNTRIES = COVERAGE.filter((c) => c.region === "UK");
const EU_COUNTRIES = COVERAGE.filter((c) => c.region === "EU");
const US_COUNTRY = COVERAGE.find((c) => c.code === "US");

export type RunMode = "live" | "demo";

interface Props {
  live: boolean;
  onRun: (url: string, states: [string, string], mode: RunMode) => void;
  disabled?: boolean;
}

const PRESETS: Array<{ label: string; url: string; a: string; b: string }> = [
  { label: "Atlanta apartment", url: "https://www.apartments.com/atlanta-ga/", a: "CA", b: "TX" },
  { label: "Vegas hotel", url: "https://www.hotels.com/", a: "CA", b: "NY" },
  { label: "Event tickets", url: "https://www.ticketmaster.com/", a: "CA", b: "FL" },
];

export default function ScanInput({ live, onRun, disabled }: Props) {
  const [url, setUrl] = useState(PRESETS[0].url);
  const [a, setA] = useState("CA");
  const [b, setB] = useState("TX");
  const [mode, setMode] = useState<RunMode>(live ? "live" : "demo");
  const [touched, setTouched] = useState(false);

  const urlValid = /^https?:\/\/.+\..+/.test(url.trim());
  const statesValid = a !== b;
  const canRun = urlValid && statesValid && !disabled;

  return (
    <section className="mx-auto max-w-6xl px-5 pt-10 pb-10 sm:pt-16">
      {/* Hero — headline */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="max-w-3xl"
      >
        <div className="inline-flex items-center gap-2 rounded-full border border-gold-600/40 bg-gold-500/10 px-3 py-1 text-xs font-medium text-gold-400">
          <ShieldCheck className="h-3.5 w-3.5" /> US FTC · UK CMA · EU UCPD coverage
        </div>

        <h1 className="mt-5 font-display text-4xl font-700 leading-[1.05] tracking-tight sm:text-6xl">
          Catch hidden fees and
          <br />
          <span className="bg-gradient-to-r from-gold-400 to-gold-600 bg-clip-text text-transparent">
            price discrimination
          </span>{" "}
          in real time.
        </h1>
        <p className="mt-4 max-w-2xl text-base text-slate-400 sm:text-lg">
          Paste a target URL, pick two locations, and watch our agents walk the checkout —
          exposing junk fees, mapping them to the exact FTC clause, and sealing court-ready
          evidence in seconds.
        </p>

        {/* Compact coverage stats */}
        <div className="mt-6 grid max-w-xl grid-cols-3 gap-3 text-center">
          <div className="rounded-lg border border-ink-600 bg-ink-800/60 px-3 py-2">
            <div className="font-display text-xl font-700 text-gold-400">29</div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">jurisdictions</div>
          </div>
          <div className="rounded-lg border border-ink-600 bg-ink-800/60 px-3 py-2">
            <div className="font-display text-xl font-700 text-gold-400">$71M+</div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">recovered</div>
          </div>
          <div className="rounded-lg border border-ink-600 bg-ink-800/60 px-3 py-2">
            <div className="font-display text-xl font-700 text-gold-400">May 2025</div>
            <div className="text-[10px] uppercase tracking-wider text-slate-500">rule live</div>
          </div>
        </div>
      </motion.div>

      {/* World map showing actual coverage + selected locations */}
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.08, ease: "easeOut" }}
        className="mt-9 overflow-hidden rounded-2xl border border-ink-600 bg-ink-900/50 shadow-panel"
      >
        <WorldMap geoA={a} geoB={b} />
      </motion.div>

      {/* The actual input — front and centre, never hidden */}
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.12, ease: "easeOut" }}
        onSubmit={(e) => {
          e.preventDefault();
          setTouched(true);
          if (canRun) onRun(url.trim(), [a, b], mode);
        }}
        className="mt-10 rounded-2xl border border-ink-600 bg-ink-800/80 p-5 shadow-panel backdrop-blur sm:p-6"
      >
        <label htmlFor="target-url" className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-300">
          <Globe2 className="h-4 w-4 text-gold-400" /> Target listing or checkout URL
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            id="target-url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onBlur={() => setTouched(true)}
            placeholder="https://…"
            aria-invalid={touched && !urlValid}
            className="w-full rounded-xl border border-ink-600 bg-ink-900 py-3 pl-10 pr-3 font-mono text-sm text-slate-100 placeholder:text-slate-600 focus:border-gold-500 focus:outline-none"
          />
        </div>
        {touched && !urlValid && (
          <p role="alert" className="mt-1.5 text-xs text-violation">Enter a valid http(s) URL to scan.</p>
        )}

        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {[
            { id: "state-a", label: "Shopper location A", val: a, set: setA },
            { id: "state-b", label: "Shopper location B", val: b, set: setB },
          ].map((s) => (
            <div key={s.id}>
              <label htmlFor={s.id} className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-300">
                <MapPin className="h-4 w-4 text-gold-400" /> {s.label}
              </label>
              <select
                id={s.id}
                value={s.val}
                onChange={(e) => s.set(e.target.value)}
                className="w-full rounded-xl border border-ink-600 bg-ink-900 px-3 py-3 text-sm text-slate-100 focus:border-gold-500 focus:outline-none"
              >
                <optgroup label="🇺🇸 United States">
                  {US_COUNTRY && (
                    <option key={US_COUNTRY.code} value={US_COUNTRY.code}>
                      {US_COUNTRY.name} (whole country)
                    </option>
                  )}
                  {US_STATES.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name} ({c.code})
                    </option>
                  ))}
                </optgroup>
                <optgroup label="🇬🇧 United Kingdom — DMCCA 2024">
                  {UK_COUNTRIES.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="🇪🇺 European Union — UCPD + DFA">
                  {EU_COUNTRIES.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name} ({c.code})
                    </option>
                  ))}
                </optgroup>
              </select>
            </div>
          ))}
        </div>
        {touched && !statesValid && (
          <p role="alert" className="mt-1.5 text-xs text-violation">Pick two different locations to compare.</p>
        )}
        <p className="mt-1.5 text-[11px] text-slate-500">
          Tip: US-state pairs (e.g. <span className="font-mono text-slate-400">CA vs TX</span>) use Bright Data's state-level
          residential proxy for true geo targeting. International picks (UK / EU) compare at the country level.
        </p>

        <div className="mt-5 flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-500">Try:</span>
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => { setUrl(p.url); setA(p.a); setB(p.b); }}
              className="rounded-full border border-ink-600 bg-ink-700 px-3 py-1 text-xs text-slate-300 transition-colors hover:border-gold-500/60 hover:text-gold-400"
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="inline-flex rounded-xl border border-ink-600 bg-ink-900 p-1 text-xs">
            <button
              type="button"
              onClick={() => setMode("live")}
              disabled={!live}
              title={live ? "Run against the live backend" : "Backend not configured (set VITE_API_BASE)"}
              className={`rounded-lg px-3 py-1.5 font-medium transition-colors ${
                mode === "live" ? "bg-gold-500 text-ink-900" : "text-slate-400"
              } ${!live ? "cursor-not-allowed opacity-40" : ""}`}
            >
              Live scan
            </button>
            <button
              type="button"
              onClick={() => setMode("demo")}
              className={`rounded-lg px-3 py-1.5 font-medium transition-colors ${
                mode === "demo" ? "bg-gold-500 text-ink-900" : "text-slate-400"
              }`}
            >
              Demo (mock)
            </button>
          </div>

          <button
            type="submit"
            disabled={!canRun}
            className="group inline-flex items-center justify-center gap-2 rounded-xl bg-gold-500 px-6 py-3 font-display text-sm font-600 text-ink-900 shadow-gold transition-all hover:bg-gold-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Zap className="h-4 w-4" />
            {mode === "live" ? "Run Live Scan" : "Run Demo Scan"}
          </button>
        </div>
        <p className="mt-3 text-xs text-slate-500">
          {mode === "live"
            ? "Live mode walks the funnel via Bright Data geo-proxies — typically 1–3 min on real sites. Progress is shown live."
            : "Demo mode uses built-in mock data — instant, no backend or credits used."}
        </p>
      </motion.form>
    </section>
  );
}
