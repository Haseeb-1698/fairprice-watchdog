import { motion } from "framer-motion";
import { Radar, Search, Zap, Check, Loader2, X, Clock, Shield } from "lucide-react";
import type { HuntStatus } from "../types";

interface Props {
  huntStatus: Partial<HuntStatus> | null;
  elapsedSec: number;
  sector: string;
  city: string;
  onCancel: () => void;
}

const PHASES = [
  { key: "discovery", name: "Discovery Agent", Icon: Radar,
    desc: "Searching the web for candidate targets via SERP API" },
  { key: "scout", name: "Scout Agent", Icon: Search,
    desc: "Testing URLs for fetchability, prices, and fee keywords" },
  { key: "pipeline", name: "Full Pipeline Scan", Icon: Zap,
    desc: "Crawler → Journey → Diff → Law-Mapper across two states" },
  { key: "done", name: "Evidence Filing", Icon: Shield,
    desc: "Sealing SHA-256 evidence bundle" },
];

const PHASE_ORDER = ["queued", "discovery", "scout", "pipeline", "done"];

function fmt(s: number) {
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

export default function HuntProgress({ huntStatus, elapsedSec, sector, city, onCancel }: Props) {
  const currentPhase = huntStatus?.phase ?? "queued";
  const phaseIdx = PHASE_ORDER.indexOf(currentPhase);

  const candidates = huntStatus?.candidates ?? [];
  const scoutResults = huntStatus?.scout_results ?? [];
  const results = huntStatus?.results ?? [];

  return (
    <section className="mx-auto max-w-3xl px-5 py-10">
      <div className="rounded-2xl border border-ink-600 bg-ink-800/80 p-6 shadow-panel backdrop-blur">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-xl font-600 text-slate-100">
              Agent hunt in progress
            </h2>
            <p className="mt-1 text-xs text-slate-400 font-mono">
              Sector: <span className="text-gold-400">{sector}</span>
              {city && <> · City: <span className="text-gold-400">{city}</span></>}
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="inline-flex items-center gap-1.5 rounded-lg border border-ink-600 bg-ink-900 px-2.5 py-1.5 font-mono text-sm tabular text-gold-400">
              <Clock className="h-3.5 w-3.5" /> {fmt(elapsedSec)}
            </div>
            <button
              onClick={onCancel}
              className="inline-flex items-center gap-1 rounded-lg border border-ink-600 px-2.5 py-1 text-xs text-slate-400 transition-colors hover:border-violation/60 hover:text-violation"
            >
              <X className="h-3.5 w-3.5" /> Cancel
            </button>
          </div>
        </div>

        {/* Phase steps */}
        <ul className="mt-6 space-y-2">
          {PHASES.map((phase, i) => {
            const phasePos = PHASE_ORDER.indexOf(phase.key);
            const done = phaseIdx > phasePos;
            const active = phaseIdx === phasePos;
            const Icon = phase.Icon;
            return (
              <motion.li
                key={phase.key}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.06 }}
                className={`flex items-center gap-3 rounded-xl border p-3 transition-colors ${
                  active ? "border-gold-500/50 bg-gold-500/5" : "border-ink-600 bg-ink-900/50"
                }`}
              >
                <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                  done ? "bg-fair/15 text-fair" : active ? "bg-gold-500/15 text-gold-400 animate-pulseRing" : "bg-ink-700 text-slate-500"
                }`}>
                  <Icon className="h-4.5 w-4.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-600 ${done || active ? "text-slate-100" : "text-slate-500"}`}>{phase.name}</span>
                  </div>
                  <p className="truncate text-xs text-slate-500">{phase.desc}</p>
                </div>
                <div className="shrink-0">
                  {done ? (
                    <Check className="h-5 w-5 text-fair" />
                  ) : active ? (
                    <Loader2 className="h-5 w-5 animate-spin text-gold-400" />
                  ) : (
                    <span className="block h-2 w-2 rounded-full bg-ink-600" />
                  )}
                </div>
              </motion.li>
            );
          })}
        </ul>

        {/* Live candidate feed */}
        {candidates.length > 0 && (
          <div className="mt-5">
            <p className="mb-2 text-xs font-600 text-slate-400 uppercase tracking-wide">
              {candidates.length} candidate{candidates.length !== 1 ? "s" : ""} discovered
            </p>
            <ul className="space-y-1 max-h-28 overflow-y-auto">
              {candidates.slice(0, 8).map((c, i) => {
                const scout = scoutResults.find((s) => s.url === c.url);
                return (
                  <li key={i} className="flex items-center justify-between gap-2 rounded-lg border border-ink-700 bg-ink-900/60 px-3 py-1.5">
                    <span className="truncate font-mono text-[11px] text-slate-400">{c.url}</span>
                    {scout && (
                      <span className={`shrink-0 rounded text-[10px] font-600 px-1.5 py-0.5 ${
                        scout.eligible ? "bg-fair/15 text-fair" : "bg-violation/10 text-violation"
                      }`}>
                        {scout.eligible ? `✓ ${(scout.score * 100).toFixed(0)}%` : "filtered"}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {/* Partial results streaming in */}
        {results.length > 0 && (
          <div className="mt-4">
            <p className="mb-2 text-xs font-600 text-slate-400 uppercase tracking-wide">
              {results.length} result{results.length !== 1 ? "s" : ""} so far
            </p>
            {results.map((r, i) => (
              <div key={i} className="mb-2 rounded-lg border border-ink-700 bg-ink-900/60 px-3 py-2">
                <div className="flex items-center gap-2">
                  <HonestyBadge label={r.honesty_label} />
                  <span className="truncate font-mono text-xs text-slate-300">{r.title || r.url}</span>
                </div>
                {r.summary && <p className="mt-1 text-[11px] text-slate-500">{r.summary}</p>}
              </div>
            ))}
          </div>
        )}

        {/* Shimmer progress bar */}
        <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-ink-700">
          <div className="relative h-full w-1/3 rounded-full bg-gradient-to-r from-gold-600 to-gold-400">
            <span className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/40 to-transparent" />
          </div>
        </div>
        <p className="mt-2 text-center text-xs text-slate-500" aria-live="polite">
          {currentPhase === "queued" && "Queued — agents starting up…"}
          {currentPhase === "discovery" && "Discovering targets — searching SERP for candidates…"}
          {currentPhase === "scout" && "Scouting — testing each URL for prices and fees…"}
          {currentPhase === "pipeline" && "Scanning — Crawler → Journey → Diff from two US states…"}
          {currentPhase === "done" && "Filing evidence — sealing SHA-256 bundle…"}
        </p>
      </div>
    </section>
  );
}

export function HonestyBadge({ label }: { label: string }) {
  const cfg: Record<string, { text: string; cls: string }> = {
    live_verified: { text: "Live verified", cls: "bg-fair/15 text-fair border-fair/30" },
    live_partial: { text: "Live partial", cls: "bg-warn/15 text-warn border-warn/30" },
    mock_fallback: { text: "Mock fallback", cls: "bg-slate-500/15 text-slate-400 border-slate-500/30" },
    blocked: { text: "Blocked", cls: "bg-violation/15 text-violation border-violation/30" },
  };
  const c = cfg[label] ?? cfg.mock_fallback;
  return (
    <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-600 uppercase tracking-wide ${c.cls}`}>
      {c.text}
    </span>
  );
}
