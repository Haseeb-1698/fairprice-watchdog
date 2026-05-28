import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Footprints, Globe, GitCompareArrows, Scale, FileCheck2, Radar,
  Loader2, CheckCircle2, AlertCircle, Brain, Hash, Activity,
} from "lucide-react";
import { API_BASE, isLive } from "../api";

export interface AgentEvent {
  ts: number;
  agent: string;
  level: "queued" | "started" | "thinking" | "action" | "result" | "warn" | "error" | "done";
  message: string;
  data?: Record<string, any>;
}

interface Props {
  scanId: string | null;          // when null, render demo events
  active: boolean;                // poll while true
  startedAt: number;              // ms timestamp
  className?: string;
}

const ICONS: Record<string, React.ElementType> = {
  Crawler: Globe,
  "Journey Simulator": Footprints,
  Diff: GitCompareArrows,
  "Law-Mapper": Scale,
  Filing: FileCheck2,
  "Evidence Vault": Hash,
  Discovery: Radar,
  Scout: Radar,
  Pipeline: Activity,
};

const LEVEL_STYLE: Record<AgentEvent["level"], { color: string; bg: string; ring: string }> = {
  queued:   { color: "text-slate-400", bg: "bg-slate-500/10", ring: "ring-slate-500/30" },
  started:  { color: "text-gold-400",  bg: "bg-gold-500/10",  ring: "ring-gold-500/30" },
  thinking: { color: "text-purple-300",bg: "bg-purple-500/10",ring: "ring-purple-500/30" },
  action:   { color: "text-blue-300",  bg: "bg-blue-500/10",  ring: "ring-blue-500/30" },
  result:   { color: "text-fair",      bg: "bg-fair/10",      ring: "ring-fair/30" },
  warn:     { color: "text-warn",      bg: "bg-warn/10",      ring: "ring-warn/30" },
  error:    { color: "text-violation", bg: "bg-violation/10", ring: "ring-violation/30" },
  done:     { color: "text-fair",      bg: "bg-fair/10",      ring: "ring-fair/30" },
};

function elapsed(eventTs: number, startedAt: number): string {
  const sec = Math.max(0, Math.round((eventTs - startedAt) / 1000));
  const m = Math.floor(sec / 60);
  const r = sec % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

// ── Demo fallback events — runs when there's no live backend or scanId ───────
const DEMO_EVENTS: Omit<AgentEvent, "ts">[] = [
  { agent: "Pipeline", level: "queued",   message: "Scan accepted · comparing CA vs TX" },
  { agent: "Crawler", level: "started",   message: "Loading listing from CA via Bright Data residential proxy" },
  { agent: "Crawler", level: "thinking",  message: "Routing through proxy username brd-customer-…-state-ca" },
  { agent: "Crawler", level: "result",    message: "Advertised price from CA: $1,995.00" },
  { agent: "Journey Simulator", level: "started",  message: "Walking checkout funnel from CA (stops before payment)" },
  { agent: "Journey Simulator", level: "action",   message: "Clicked 'Reserve' → reading checkout summary" },
  { agent: "Journey Simulator", level: "result",   message: "Final total from CA: $2,527.00 · 4 fee line-item(s)" },
  { agent: "Diff", level: "thinking",     message: "Comparing advertised vs final for CA" },
  { agent: "Diff", level: "result",       message: "CA: $532.00 hidden in checkout · 4 fees · 4 likely junk" },
  { agent: "Law-Mapper", level: "thinking", message: "Matching fees to FTC clauses (16 CFR Part 464)" },
  { agent: "Law-Mapper", level: "result", message: "CA: 4 fee(s) classified · §464.2(a) drip pricing" },
  { agent: "Crawler", level: "started",   message: "Loading listing from TX via Bright Data residential proxy" },
  { agent: "Journey Simulator", level: "result", message: "Final total from TX: $2,122.68 · 4 fee line-item(s)" },
  { agent: "Diff", level: "result",       message: "TX: $446.88 hidden · same junk fees, different totals" },
  { agent: "Evidence Vault", level: "done", message: "Both snapshots SHA-256 sealed · chain-of-custody complete" },
  { agent: "Filing", level: "done",       message: "Scan complete · CA $2,527 vs TX $2,122.68 — $404 (19%) geo gap" },
];

export default function AgentFeed({ scanId, active, startedAt, className = "" }: Props) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const sinceRef = useRef(0);
  const demoTimer = useRef<number | undefined>(undefined);
  const pollTimer = useRef<number | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);

  // Reset when the scan changes.
  useEffect(() => {
    setEvents([]);
    sinceRef.current = 0;
    if (demoTimer.current) clearTimeout(demoTimer.current);
    if (pollTimer.current) clearTimeout(pollTimer.current);
  }, [scanId]);

  // Live poll OR demo replay.
  useEffect(() => {
    if (!active) return;
    let stopped = false;

    async function pollOnce() {
      if (!scanId || !isLive()) return false;
      try {
        const url = `${API_BASE}/api/scan/${scanId}/events?since=${sinceRef.current}`;
        const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
        if (!res.ok) return false;
        const data = await res.json();
        if (Array.isArray(data.events) && data.events.length > 0) {
          setEvents((prev) => [...prev, ...data.events]);
          sinceRef.current = data.next_since ?? sinceRef.current + data.events.length;
          return true;
        }
      } catch {
        // ignore — transient network blip
      }
      return false;
    }

    function schedulePoll() {
      if (stopped) return;
      pollTimer.current = window.setTimeout(async () => {
        await pollOnce();
        schedulePoll();
      }, 1000);
    }

    function replayDemo() {
      let i = 0;
      const tick = () => {
        if (stopped || i >= DEMO_EVENTS.length) return;
        const base = DEMO_EVENTS[i];
        const ev: AgentEvent = { ...base, ts: Date.now() };
        setEvents((prev) => [...prev, ev]);
        i++;
        demoTimer.current = window.setTimeout(tick, 700 + Math.random() * 700);
      };
      tick();
    }

    if (scanId && isLive()) {
      schedulePoll();
    } else {
      replayDemo();
    }

    return () => {
      stopped = true;
      if (demoTimer.current) clearTimeout(demoTimer.current);
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, [active, scanId]);

  // Autoscroll to bottom on new events.
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events.length]);

  return (
    <div
      ref={containerRef}
      className={`rounded-2xl border border-ink-600 bg-ink-900/60 p-4 shadow-panel backdrop-blur ${className}`}
      style={{ maxHeight: "440px", overflowY: "auto" }}
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-purple-400" />
          <h3 className="font-display text-sm font-700 text-slate-100">Agent thinking feed</h3>
          {!isLive() || !scanId ? (
            <span className="rounded bg-slate-500/15 px-1.5 py-0.5 text-[10px] font-600 uppercase text-slate-400">
              demo replay
            </span>
          ) : (
            <span className="rounded bg-fair/15 px-1.5 py-0.5 text-[10px] font-600 uppercase text-fair">
              live
            </span>
          )}
        </div>
        <span className="font-mono text-xs text-slate-500">{events.length} event(s)</span>
      </div>

      {events.length === 0 && (
        <div className="flex items-center gap-2 py-6 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin text-gold-400" />
          Waiting for the worker to pick up the scan…
        </div>
      )}

      <ul className="space-y-2">
        <AnimatePresence initial={false}>
          {events.map((e, idx) => {
            const Icon = ICONS[e.agent] ?? Activity;
            const style = LEVEL_STYLE[e.level] ?? LEVEL_STYLE.action;
            return (
              <motion.li
                key={`${e.ts}-${idx}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.25 }}
                className={`flex items-start gap-3 rounded-xl border border-ink-600 ${style.bg} p-2.5`}
              >
                <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ring-1 ${style.ring} ${style.color}`}>
                  {e.level === "thinking" ? (
                    <Brain className="h-3.5 w-3.5" />
                  ) : e.level === "done" || e.level === "result" ? (
                    <CheckCircle2 className="h-3.5 w-3.5" />
                  ) : e.level === "warn" || e.level === "error" ? (
                    <AlertCircle className="h-3.5 w-3.5" />
                  ) : (
                    <Icon className="h-3.5 w-3.5" />
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <span className={`text-xs font-700 ${style.color}`}>{e.agent}</span>
                    <span className="text-[10px] uppercase tracking-wider text-slate-500">{e.level}</span>
                    <span className="ml-auto font-mono text-[10px] text-slate-600">{elapsed(e.ts, startedAt)}</span>
                  </div>
                  <p className="mt-0.5 text-xs leading-snug text-slate-300">{e.message}</p>
                </div>
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ul>
    </div>
  );
}
