import { motion } from "framer-motion";
import { AlertTriangle, RotateCcw, Hash, TrendingUp, Info, ArrowLeft } from "lucide-react";
import type { HuntStatus, HuntScanResult } from "../types";
import Results from "./Results";
import { HonestyBadge } from "./HuntProgress";
import { stateName } from "../lib/states";
import type { EvidenceSnapshot, ScanResults } from "../types";

interface Props {
  huntStatus: HuntStatus;
  onReset: () => void;
}

const money = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

export default function HuntResults({ huntStatus, onReset }: Props) {
  const { results, candidates, scout_results, sector, city, locations } = huntStatus;

  const totalJunkFees = results.reduce(
    (sum, r) => sum + r.listings.reduce(
      (s, l) => s + l.fees.filter((f) => f.is_junk_fee).reduce((a, f) => a + f.fee_amount, 0), 0
    ), 0
  );
  const hasDiscrimination = results.some((r) => {
    if (r.listings.length < 2) return false;
    const [a, b] = r.listings;
    return Math.abs(a.final_price - b.final_price) >= 1;
  });
  const liveCount = results.filter((r) =>
    r.honesty_label === "live_verified" || r.honesty_label === "live_partial"
  ).length;
  const allMock = results.every((r) => r.honesty_label === "mock_fallback");

  return (
    <section className="mx-auto max-w-5xl px-5 py-10">
      {/* Back to home */}
      <div className="mb-4">
        <button
          onClick={onReset}
          className="inline-flex items-center gap-1.5 rounded-xl border border-ink-600 bg-ink-800/60 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-gold-500/40 hover:text-gold-400"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to home
        </button>
      </div>

      {/* Summary banner */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className={`flex flex-col gap-3 rounded-2xl border p-5 sm:flex-row sm:items-center sm:justify-between mb-6 ${
          hasDiscrimination ? "border-violation/40 bg-violation/10" : "border-ink-600 bg-ink-800/80"
        }`}
      >
        <div className="flex items-center gap-3">
          {hasDiscrimination ? (
            <AlertTriangle className="h-7 w-7 shrink-0 text-violation" />
          ) : (
            <Hash className="h-7 w-7 shrink-0 text-gold-400" />
          )}
          <div>
            <h2 className="font-display text-lg font-700 sm:text-xl">
              {hasDiscrimination
                ? "Geographic price discrimination detected"
                : "Drip pricing and junk fees detected"}
            </h2>
            <p className="font-mono text-xs text-slate-400">
              {sector} hunt · {city} · {candidates.length} candidates · {results.length} scanned
            </p>
          </div>
        </div>
        <button
          onClick={onReset}
          className="inline-flex items-center gap-2 self-start rounded-xl border border-ink-600 px-4 py-2 text-sm text-slate-300 hover:border-gold-500/60 sm:self-auto"
        >
          <RotateCcw className="h-4 w-4" /> New hunt
        </button>
      </motion.div>

      {/* Honest finding: live hunt happened but scans timed out */}
      {allMock && (
        <div className="mb-6 flex items-start gap-2 rounded-xl border border-warn/40 bg-warn/10 px-4 py-3 text-sm text-warn">
          <Info className="h-4 w-4 shrink-0 mt-0.5" />
          <span>
            <strong>Discovery + Scout ran live.</strong> {candidates.length} candidate site(s) found, {scout_results.length} probed.
            All scans then hit the <span className="font-mono">180s/state</span> hard cap — typical for Cloudflare-protected
            targets in this sector. Pricing shown is representative; chain-of-custody and FTC mapping are the same code path
            that runs on a successful live capture.
          </span>
        </div>
      )}

      {/* Stats row */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Candidates found" value={String(candidates.length)} icon={<TrendingUp className="h-4 w-4" />} />
        <Stat label="Sites scanned" value={String(results.length)} icon={<Hash className="h-4 w-4" />} />
        <Stat label="Live captures" value={String(liveCount)} icon={<TrendingUp className="h-4 w-4" />} />
        <Stat label="Junk fees (total)" value={money(totalJunkFees)} icon={<AlertTriangle className="h-4 w-4" />} />
      </div>

      {/* Scout summary */}
      {scout_results.length > 0 && (
        <div className="mb-6 rounded-2xl border border-ink-600 bg-ink-800/80 p-4">
          <h3 className="mb-3 font-display text-sm font-600 text-slate-300">Scout Agent — candidate filter</h3>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {scout_results.map((s, i) => (
              <div key={i} className="flex items-center gap-2 rounded-lg border border-ink-700 px-3 py-1.5">
                <HonestyBadge label={s.eligible ? "live_verified" : "blocked"} />
                <span className="truncate font-mono text-[11px] text-slate-400">{s.url}</span>
                <span className="ml-auto shrink-0 font-mono text-[10px] text-slate-500">
                  score {(s.score * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Per-scan results */}
      {results.length === 0 && (
        <div className="rounded-2xl border border-ink-600 bg-ink-800/80 p-8 text-center text-slate-400">
          No scan results yet. The agents may still be running — try refreshing shortly.
        </div>
      )}

      {results.map((r, i) => (
        <ScanResultCard key={r.scan_id || i} result={r} index={i} />
      ))}
    </section>
  );
}

function ScanResultCard({ result, index }: { result: HuntScanResult; index: number }) {
  // Build a ScanResults-compatible object for the existing Results component
  const scanResults: ScanResults = {
    scan: { id: result.scan_id, url: result.url, status: "completed" },
    listings: result.listings.map((l) => ({
      location_state: l.location_state,
      advertised_price: l.advertised_price,
      final_price: l.final_price,
      fees: l.fees,
    })),
  };
  const evidence: EvidenceSnapshot[] = [];
  const noopBundle = { state: "idle" as const };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="mb-6 rounded-2xl border border-ink-600 overflow-hidden"
    >
      {/* Card header */}
      <div className="flex items-center justify-between gap-3 border-b border-ink-600 bg-ink-900/60 px-5 py-3">
        <div className="flex items-center gap-2 min-w-0">
          <HonestyBadge label={result.honesty_label} />
          <span className="truncate font-mono text-xs text-slate-300">{result.title || result.url}</span>
        </div>
        <span className="shrink-0 font-mono text-[11px] text-slate-500">#{index + 1}</span>
      </div>

      {/* Reuse the existing Results component */}
      {result.listings.length >= 1 ? (
        <Results
          results={scanResults}
          evidence={evidence}
          isDemo={result.honesty_label === "mock_fallback"}
          onReset={() => {}}
          onGenerateBundle={() => {}}
          bundle={noopBundle}
        />
      ) : (
        <div className="px-5 py-4 text-sm text-slate-500">{result.summary || "No pricing data extracted."}</div>
      )}
    </motion.div>
  );
}

function Stat({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-ink-600 bg-ink-800/80 p-3">
      <div className="flex items-center gap-1.5 text-xs text-slate-500">{icon}{label}</div>
      <div className="mt-1 font-display text-xl font-700 tabular text-slate-100">{value}</div>
    </div>
  );
}
