import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Eye, Github, Info } from "lucide-react";
import ScanInput, { RunMode } from "./components/ScanInput";
import PipelineProgress from "./components/PipelineProgress";
import Results from "./components/Results";
import {
  API_BASE, isLive, startScan, pollResults, getEvidence, generateComplaint,
  demoResults, demoEvidence,
} from "./api";
import type { EvidenceSnapshot, ScanResults } from "./types";

type Phase = "input" | "running" | "results";

export default function App() {
  const [phase, setPhase] = useState<Phase>("input");
  const [meta, setMeta] = useState<{ url: string; states: [string, string] }>({ url: "", states: ["CA", "TX"] });
  const [elapsed, setElapsed] = useState(0);
  const [status, setStatus] = useState("queued");
  const [results, setResults] = useState<ScanResults | null>(null);
  const [evidence, setEvidence] = useState<EvidenceSnapshot[]>([]);
  const [isDemo, setIsDemo] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [bundle, setBundle] = useState<{ state: "idle" | "loading" | "done" | "error"; url?: string; kind?: "blob" | "link" }>({ state: "idle" });

  const abortRef = useRef<AbortController | null>(null);
  const cancelledRef = useRef(false);
  const tickRef = useRef<number | undefined>(undefined);
  const demoTimer = useRef<number | undefined>(undefined);
  const scanIdRef = useRef<string | null>(null);

  const stopTicker = () => { if (tickRef.current) window.clearInterval(tickRef.current); };

  function finishDemo(url: string, states: [string, string]) {
    stopTicker();
    setResults(demoResults(url, states));
    setEvidence(demoEvidence(states));
    setIsDemo(true);
    setPhase("results");
  }

  async function run(url: string, states: [string, string], mode: RunMode) {
    cancelledRef.current = false;
    setMeta({ url, states });
    setResults(null); setEvidence([]); setNotice(null); setBundle({ state: "idle" });
    setElapsed(0); setStatus("queued"); setPhase("running");
    const startedAt = Date.now();
    tickRef.current = window.setInterval(() => setElapsed(Math.round((Date.now() - startedAt) / 1000)), 1000);

    if (mode === "demo" || !isLive()) {
      demoTimer.current = window.setTimeout(() => {
        if (!cancelledRef.current) finishDemo(url, states);
      }, 9000);
      return;
    }

    const ac = new AbortController();
    abortRef.current = ac;
    try {
      const id = await startScan(url, states);
      scanIdRef.current = id;
      const res = await pollResults(id, { signal: ac.signal, onTick: (_s, st) => setStatus(st) });
      const ev = await getEvidence(id);
      if (cancelledRef.current) return;
      stopTicker();
      setResults(res); setEvidence(ev); setIsDemo(false); setPhase("results");
    } catch (e) {
      if (cancelledRef.current) return;
      stopTicker();
      // Resilience: live backend slow/unreachable/timed-out → never hang, show demo data.
      setNotice("Live backend was slow or unreachable — showing representative demo data so the flow stays live.");
      finishDemo(url, states);
    }
  }

  function cancel() {
    cancelledRef.current = true;
    abortRef.current?.abort();
    if (demoTimer.current) window.clearTimeout(demoTimer.current);
    stopTicker();
    setPhase("input");
  }

  function reset() {
    cancel();
    cancelledRef.current = false;
    setPhase("input");
    setResults(null);
  }

  async function onGenerateBundle() {
    if (isDemo || !scanIdRef.current || !isLive()) {
      // Demo: synthesize a downloadable JSON bundle client-side.
      const blob = new Blob(
        [JSON.stringify({ generated: new Date().toISOString(), demo: true, results, evidence }, null, 2)],
        { type: "application/json" }
      );
      setBundle({ state: "done", url: URL.createObjectURL(blob), kind: "blob" });
      return;
    }
    setBundle({ state: "loading" });
    try {
      const { kind, url } = await generateComplaint(scanIdRef.current);
      setBundle({ state: "done", url, kind });
    } catch {
      setBundle({ state: "error" });
    }
  }

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-40 border-b border-ink-600/60 bg-ink-900/70 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gold-500 text-ink-900"><Eye className="h-4.5 w-4.5" /></span>
            <span className="font-display text-base font-700">FairPrice <span className="text-gold-400">Watchdog</span></span>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span className={`hidden items-center gap-1.5 sm:inline-flex`}>
              <span className={`h-2 w-2 rounded-full ${isLive() ? "bg-fair" : "bg-slate-500"}`} />
              {isLive() ? `API: ${API_BASE.replace(/^https?:\/\//, "")}` : "Demo mode (no backend)"}
            </span>
            <a href="https://github.com/Haseeb-1698/fairprice-watchdog" target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:text-gold-400">
              <Github className="h-4 w-4" /> Repo
            </a>
          </div>
        </div>
      </header>

      {notice && (
        <div className="mx-auto mt-4 max-w-5xl px-5">
          <div className="flex items-center gap-2 rounded-xl border border-warn/40 bg-warn/10 px-4 py-2.5 text-sm text-warn">
            <Info className="h-4 w-4 shrink-0" /> {notice}
          </div>
        </div>
      )}

      <AnimatePresence mode="wait">
        {phase === "input" && (
          <motion.div key="input" exit={{ opacity: 0, y: -10 }}>
            <ScanInput live={isLive()} onRun={run} />
          </motion.div>
        )}
        {phase === "running" && (
          <motion.div key="running" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <PipelineProgress elapsedSec={elapsed} statusLabel={status} url={meta.url} states={meta.states} onCancel={cancel} />
          </motion.div>
        )}
        {phase === "results" && results && (
          <motion.div key="results" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Results results={results} evidence={evidence} isDemo={isDemo} onReset={reset} onGenerateBundle={onGenerateBundle} bundle={bundle} />
          </motion.div>
        )}
      </AnimatePresence>

      <footer className="mx-auto max-w-6xl px-5 py-10 text-center text-xs text-slate-600">
        Stops before any payment is submitted · evidence SHA-256 sealed · FTC 16 CFR Part 464
      </footer>
    </div>
  );
}
