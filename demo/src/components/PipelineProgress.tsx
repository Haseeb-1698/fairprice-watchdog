import { motion } from "framer-motion";
import {
  Globe, Footprints, GitCompareArrows, Scale, Radar, FileCheck2,
  Check, Loader2, X, Clock,
} from "lucide-react";
import { stateName } from "../lib/states";

interface Props {
  elapsedSec: number;
  statusLabel: string;
  url: string;
  states: [string, string];
  onCancel: () => void;
}

const AGENTS = [
  { name: "Crawler", desc: "Loads the listing from each state via geo-proxy", Icon: Globe, at: 0 },
  { name: "Journey Simulator", desc: "Walks the checkout funnel, stops before payment", Icon: Footprints, at: 4 },
  { name: "Diff", desc: "Advertised vs. final total — extracts every fee", Icon: GitCompareArrows, at: 10 },
  { name: "Law-Mapper", desc: "Maps each fee to its FTC clause", Icon: Scale, at: 18 },
  { name: "Discovery", desc: "Correlates operators across the monitoring set", Icon: Radar, at: 26 },
  { name: "Filing", desc: "Builds the hash-sealed evidence bundle", Icon: FileCheck2, at: 34 },
];

function fmt(s: number) {
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

export default function PipelineProgress({ elapsedSec, statusLabel, url, states, onCancel }: Props) {
  // Advance stages by elapsed time; the last unfinished stage stays "active".
  const lastDone = AGENTS.reduce((acc, a, i) => (elapsedSec >= AGENTS[Math.min(i + 1, AGENTS.length - 1)].at && i < AGENTS.length - 1 ? i : acc), -1);

  return (
    <section className="mx-auto max-w-3xl px-5 py-10">
      <div className="rounded-2xl border border-ink-600 bg-ink-800/80 p-6 shadow-panel backdrop-blur">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-xl font-600 text-slate-100">Agent pipeline running</h2>
            <p className="mt-1 truncate font-mono text-xs text-slate-500" title={url}>{url}</p>
            <p className="mt-1 text-xs text-slate-400">
              Comparing <span className="text-gold-400">{stateName(states[0])}</span> vs{" "}
              <span className="text-gold-400">{stateName(states[1])}</span>
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

        <ul className="mt-6 space-y-2">
          {AGENTS.map((a, i) => {
            const done = i <= lastDone;
            const active = i === lastDone + 1;
            const Icon = a.Icon;
            return (
              <motion.li
                key={a.name}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className={`flex items-center gap-3 rounded-xl border p-3 transition-colors ${
                  active ? "border-gold-500/50 bg-gold-500/5" : "border-ink-600 bg-ink-900/50"
                }`}
              >
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                    done ? "bg-fair/15 text-fair" : active ? "bg-gold-500/15 text-gold-400 animate-pulseRing" : "bg-ink-700 text-slate-500"
                  }`}
                >
                  <Icon className="h-4.5 w-4.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-600 ${done || active ? "text-slate-100" : "text-slate-500"}`}>{a.name}</span>
                    <span className="font-mono text-[10px] uppercase tracking-wider text-slate-600">agent {i + 1}/6</span>
                  </div>
                  <p className="truncate text-xs text-slate-500">{a.desc}</p>
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

        {/* Live shimmer bar — transparent "working" feedback, never a frozen spinner */}
        <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-ink-700">
          <div className="relative h-full w-1/3 rounded-full bg-gradient-to-r from-gold-600 to-gold-400">
            <span className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/40 to-transparent" />
          </div>
        </div>
        <p className="mt-2 text-center text-xs text-slate-500" aria-live="polite">
          {statusLabel} · capturing pricing from each state (stops before any payment is submitted)
        </p>
      </div>
    </section>
  );
}
