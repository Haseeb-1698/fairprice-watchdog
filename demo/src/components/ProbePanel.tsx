import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Loader2, Zap, AlertTriangle } from "lucide-react";
import { isLive, priceProbe, type ProbeResult } from "../api";

/**
 * ProbePanel — fast geo price-discrimination check.
 *
 * Runs one product query, geo-biased to US/GB/DE, and shows the price each
 * country's shopper is shown — in ~3 seconds, no full scan. The instant
 * "the web shows a London shopper a different price than a Berlin shopper"
 * demo moment.
 */
const EXAMPLES = [
  "Marriott Marquis Times Square price per night",
  "Hilton London hotel price per night",
  "PlayStation 5 console price",
  "Sony WH-1000XM5 headphones price",
];

export default function ProbePanel() {
  const [q, setQ] = useState(EXAMPLES[0]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ProbeResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run(query?: string) {
    const term = (query ?? q).trim();
    if (!term || loading) return;
    setQ(term);
    setLoading(true);
    setErr(null);
    setResult(null);
    try {
      setResult(await priceProbe(term));
    } catch {
      setErr("Probe unavailable — the deep scan still works.");
    } finally {
      setLoading(false);
    }
  }

  if (!isLive()) return null;

  return (
    <section className="mx-auto max-w-6xl px-5 py-8">
      <div className="rounded-2xl border border-gold-600/30 bg-gradient-to-b from-gold-500/[0.06] to-transparent p-5 shadow-panel sm:p-6">
        <div className="mb-3 flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gold-500/15 text-gold-400">
            <Zap className="h-4 w-4" />
          </span>
          <h3 className="font-display text-base font-700 text-slate-100">
            Instant price-discrimination probe
          </h3>
          <span className="rounded bg-gold-500/15 px-1.5 py-0.5 text-[10px] font-600 uppercase text-gold-400">~3s</span>
        </div>
        <p className="mb-4 text-sm text-slate-400">
          See what shoppers in different countries are shown for the same product — live, in seconds.
        </p>

        <form
          onSubmit={(e) => { e.preventDefault(); run(); }}
          className="flex gap-2"
        >
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="e.g. Marriott Times Square price per night"
              className="w-full rounded-xl border border-ink-600 bg-ink-900 py-2.5 pl-10 pr-3 text-sm text-slate-100 placeholder:text-slate-600 focus:border-gold-500 focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-gold-500 px-4 py-2.5 font-display text-sm font-600 text-ink-900 shadow-gold transition-all hover:bg-gold-400 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            Probe
          </button>
        </form>

        <div className="mt-2 flex flex-wrap gap-1.5">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => run(ex)}
              className="rounded-full border border-ink-600 bg-ink-800 px-2.5 py-1 text-[11px] text-slate-400 transition-colors hover:border-gold-500/50 hover:text-gold-400"
            >
              {ex.length > 32 ? ex.slice(0, 32) + "…" : ex}
            </button>
          ))}
        </div>

        {err && <p className="mt-3 text-xs text-warn">{err}</p>}

        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-5"
            >
              {result.discrimination && (
                <div className="mb-3 inline-flex items-center gap-1.5 rounded-lg border border-violation/40 bg-violation/10 px-3 py-1.5 text-xs font-600 text-violation">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Price discrimination detected — shoppers see different prices by location
                </div>
              )}
              <div className="grid gap-3 sm:grid-cols-3">
                {result.results.map((c) => (
                  <div key={c.code} className="rounded-xl border border-ink-600 bg-ink-900/60 p-3">
                    <div className="mb-2 flex items-center gap-1.5 text-sm font-600 text-slate-200">
                      <span>{c.flag}</span> {c.label}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {c.prices.length ? (
                        c.prices.map((p, i) => (
                          <span
                            key={i}
                            className={`rounded-md px-2 py-0.5 font-mono text-xs ${
                              i === 0 ? "bg-gold-500/15 text-gold-300" : "bg-ink-700 text-slate-400"
                            }`}
                          >
                            {p}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-slate-600">no price surfaced</span>
                      )}
                    </div>
                    {c.top_url && (
                      <a
                        href={c.top_url}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2 block truncate text-[10px] text-slate-600 hover:text-gold-400"
                      >
                        {c.top_url.replace(/^https?:\/\//, "")}
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
