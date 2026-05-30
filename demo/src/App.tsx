import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Eye, Github, Info, RefreshCw, Loader2 } from "lucide-react";
import ScanInput, { RunMode } from "./components/ScanInput";
import PipelineProgress from "./components/PipelineProgress";
import Results from "./components/Results";
import Landing from "./components/Landing";
import HuntPresets from "./components/HuntPresets";
import ProbePanel from "./components/ProbePanel";
import HuntProgress from "./components/HuntProgress";
import HuntResults from "./components/HuntResults";
import {
  API_BASE, isLive, startScan, pollResults, getEvidence, generateComplaint,
  demoResults, demoEvidence,
  getHuntPresets, startHunt, pollHuntStatus, demoHuntStatus,
  adminStatus, adminRestartWorker,
} from "./api";
import type { AdminStatus } from "./api";
import type { EvidenceSnapshot, HuntPreset, HuntStatus, ScanResults } from "./types";

type Phase = "input" | "running" | "results" | "hunt_running" | "hunt_results";

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
  const [currentScanId, setCurrentScanId] = useState<string | null>(null);
  const [runStartedAt, setRunStartedAt] = useState<number>(0);

  // Admin controls — worker health + manual reset button
  const [adminInfo, setAdminInfo] = useState<AdminStatus | null>(null);
  const [resetting, setResetting] = useState(false);
  const [resetMsg, setResetMsg] = useState<string | null>(null);

  // Hunt state
  const [huntPresets, setHuntPresets] = useState<HuntPreset[]>([]);
  const [huntStatus, setHuntStatus] = useState<HuntStatus | null>(null);
  const [huntSector, setHuntSector] = useState("");
  const [huntCity, setHuntCity] = useState("");

  const abortRef = useRef<AbortController | null>(null);
  const cancelledRef = useRef(false);
  const tickRef = useRef<number | undefined>(undefined);
  const demoTimer = useRef<number | undefined>(undefined);
  const scanIdRef = useRef<string | null>(null);

  const stopTicker = () => { if (tickRef.current) window.clearInterval(tickRef.current); };

  // Load presets on mount
  useEffect(() => {
    getHuntPresets().then(setHuntPresets).catch(() => {});
  }, []);

  // Poll admin status every 8 s so the worker-alive badge reflects reality.
  useEffect(() => {
    if (!isLive()) return;
    let stopped = false;
    const tick = async () => {
      const s = await adminStatus();
      if (!stopped) setAdminInfo(s);
    };
    tick();
    const id = window.setInterval(tick, 8000);
    return () => { stopped = true; window.clearInterval(id); };
  }, []);

  async function handleReset() {
    if (resetting) return;
    if (!window.confirm(
      "Restart the worker and flush both queues? In-flight scans will be lost. Use this if the pipeline looks stuck."
    )) return;
    setResetting(true);
    setResetMsg(null);
    try {
      const data = await adminRestartWorker();
      setResetMsg(
        data.worker_relaunched
          ? `Worker restarted · flushed ${data.scan_queue_cleared} scan(s), ${data.event_streams_cleared} event stream(s).`
          : `Worker killed and queues flushed, but relaunch couldn't be confirmed — ask the operator to start it manually.`
      );
      const s = await adminStatus();
      setAdminInfo(s);
    } catch (e) {
      setResetMsg(`Reset failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setResetting(false);
      window.setTimeout(() => setResetMsg(null), 8000);
    }
  }

  function finishDemo(url: string, states: [string, string]) {
    stopTicker();
    setResults(demoResults(url, states));
    setEvidence(demoEvidence(states));
    setIsDemo(true);
    setPhase("results");
  }

  // ── Standard URL scan ──────────────────────────────────────────────────────
  async function run(url: string, states: [string, string], mode: RunMode) {
    cancelledRef.current = false;
    setMeta({ url, states });
    setResults(null); setEvidence([]); setNotice(null); setBundle({ state: "idle" });
    setCurrentScanId(null);
    setElapsed(0); setStatus("queued"); setPhase("running");
    const startedAt = Date.now();
    setRunStartedAt(startedAt);
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
      setCurrentScanId(id);     // surface to AgentFeed for live event polling
      const res = await pollResults(id, { signal: ac.signal, onTick: (_s, st) => setStatus(st) });
      const ev = await getEvidence(id);
      if (cancelledRef.current) return;
      stopTicker();
      setResults(res); setEvidence(ev); setIsDemo(false); setPhase("results");
    } catch (e) {
      if (cancelledRef.current) return;
      stopTicker();
      // Pull the agent event stream to explain what *actually* went wrong —
      // the user sees a real reason (e.g. "all live strategies exhausted")
      // instead of a silent fallback to demo.
      const id = scanIdRef.current;
      let reason = e instanceof Error ? e.message : "Live scan did not return";
      if (id && isLive()) {
        try {
          const r = await fetch(`${API_BASE}/api/scan/${id}/events?since=0`, {
            signal: AbortSignal.timeout(6000),
          });
          const data = await r.json();
          const warns = (data.events || []).filter(
            (ev: any) => ev.level === "warn" || ev.level === "error"
          );
          if (warns.length > 0) {
            const last = warns[warns.length - 1];
            reason = `${last.agent}: ${last.message}`;
          }
        } catch {
          /* ignore — keep generic reason */
        }
      }
      setNotice(
        `Live scan did not return a real capture · ${reason} · ` +
        "Showing representative data so you can see the rest of the flow (chain-of-custody " +
        "and FTC mapping are the same code path as a successful live run)."
      );
      finishDemo(url, states);
    }
  }

  // ── Hunt flow ──────────────────────────────────────────────────────────────
  async function startHuntFlow(sector: string, city: string, locations: [string, string]) {
    cancelledRef.current = false;
    setHuntSector(sector);
    setHuntCity(city);
    setHuntStatus(null);
    setNotice(null);
    setElapsed(0);
    setPhase("hunt_running");

    const startedAt = Date.now();
    tickRef.current = window.setInterval(() => setElapsed(Math.round((Date.now() - startedAt) / 1000)), 1000);

    if (!isLive()) {
      // Demo mode: simulate hunt phases with a timed delay
      let phase_: string = "discovery";
      const steps = ["discovery", "scout", "pipeline", "done"];
      let stepIdx = 0;
      const advance = () => {
        if (cancelledRef.current) return;
        stepIdx++;
        phase_ = steps[Math.min(stepIdx, steps.length - 1)];
        setHuntStatus((prev) => prev ? { ...prev, phase: phase_, status: stepIdx < steps.length - 1 ? "scanning" : "completed" } : null);
        if (stepIdx < steps.length - 1) {
          demoTimer.current = window.setTimeout(advance, 3500);
        } else {
          stopTicker();
          const finalStatus = demoHuntStatus(sector, city, Array.from(locations));
          setHuntStatus(finalStatus);
          setPhase("hunt_results");
        }
      };
      // Init with queued state
      setHuntStatus({ id: `demo-${sector}`, sector, label: sector, city, locations: Array.from(locations),
        status: "discovering", phase: "discovery", candidates: [], scout_results: [],
        scan_ids: [], results: [], created_at: new Date().toISOString(), updated_at: new Date().toISOString() });
      demoTimer.current = window.setTimeout(advance, 3000);
      return;
    }

    const ac = new AbortController();
    abortRef.current = ac;
    try {
      const huntId = await startHunt(sector, city, Array.from(locations));
      // Poll for progressive updates
      const finalStatus = await pollHuntStatus(huntId, {
        signal: ac.signal,
        onTick: (_s, st) => {
          setStatus(st);
          // Fetch partial state for progressive rendering
          fetch(`${API_BASE}/api/hunts/${huntId}`)
            .then((r) => r.json())
            .then((data) => { if (!cancelledRef.current) setHuntStatus(data); })
            .catch(() => {});
        },
      });
      if (cancelledRef.current) return;
      stopTicker();
      // Honest finding: if the hunt ran live but every internal scan hit
      // the per-state timeout, surface that — it's not "no backend".
      const liveScans = finalStatus.results?.filter(
        (r) => r.honesty_label === "live_verified" || r.honesty_label === "live_partial"
      ).length ?? 0;
      const allMock = finalStatus.results?.length > 0 &&
        finalStatus.results.every((r) => r.honesty_label === "mock_fallback");
      if (allMock) {
        setNotice(
          `Live hunt found ${finalStatus.candidates.length} candidate(s) and scouted them, but every target ` +
          `hit the 180s/state hard cap (likely Cloudflare-protected). Showing representative pricing so the flow lands.`
        );
      } else if (liveScans === 0 && (finalStatus.results?.length ?? 0) === 0) {
        setNotice("Live hunt ran but no eligible targets were scanned. Showing demo results.");
      }
      setHuntStatus(finalStatus);
      setPhase("hunt_results");
    } catch (e) {
      if (cancelledRef.current) return;
      stopTicker();
      setNotice("Live hunt could not reach the backend — showing demo results so the flow stays usable.");
      const fallback = demoHuntStatus(sector, city, Array.from(locations));
      setHuntStatus(fallback);
      setPhase("hunt_results");
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
    setHuntStatus(null);
  }

  async function onGenerateBundle() {
    if (isDemo || !scanIdRef.current || !isLive()) {
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
            {isLive() && adminInfo && (
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-medium ${
                  adminInfo.worker_alive
                    ? "border-fair/40 bg-fair/10 text-fair"
                    : "border-violation/40 bg-violation/10 text-violation"
                }`}
                title={`scan queue ${adminInfo.scan_queue} · hunt queue ${adminInfo.hunt_queue}`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    adminInfo.worker_alive ? "bg-fair animate-pulse" : "bg-violation"
                  }`}
                />
                worker {adminInfo.worker_alive ? "live" : "down"}
                {adminInfo.scan_queue > 0 && ` · ${adminInfo.scan_queue} queued`}
              </span>
            )}
            {isLive() && !adminInfo && (
              <span className="hidden items-center gap-1.5 sm:inline-flex">
                <span className="h-2 w-2 animate-pulse rounded-full bg-slate-500" />
                checking worker…
              </span>
            )}
            {!isLive() && (
              <span className="hidden items-center gap-1.5 sm:inline-flex">
                <span className="h-2 w-2 rounded-full bg-slate-500" />
                Demo mode (no backend)
              </span>
            )}
            {isLive() && (
              <button
                onClick={handleReset}
                disabled={resetting}
                title="Restart worker + flush queues (use if a scan is stuck)"
                className="inline-flex items-center gap-1 rounded-lg border border-ink-600 px-2 py-1 text-[11px] text-slate-400 transition-colors hover:border-warn/60 hover:text-warn disabled:opacity-50"
              >
                {resetting ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5" />
                )}
                Reset worker
              </button>
            )}
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

      {resetMsg && (
        <div className="mx-auto mt-3 max-w-5xl px-5">
          <div className="flex items-center gap-2 rounded-xl border border-fair/40 bg-fair/10 px-4 py-2 text-sm text-fair">
            <RefreshCw className="h-4 w-4 shrink-0" /> {resetMsg}
          </div>
        </div>
      )}

      <AnimatePresence mode="wait">
        {phase === "input" && (
          <motion.div key="input" exit={{ opacity: 0, y: -10 }}>
            {/* HERO: URL + location picker + world map — at the top */}
            <ScanInput live={isLive()} onRun={run} />
            {/* Fast geo price-discrimination probe — instant demo moment */}
            <ProbePanel />
            {/* Sector hunt cards — below the hero */}
            <HuntPresets presets={huntPresets} onStartHunt={startHuntFlow} />
            {/* Regulatory "Why now" — at the bottom */}
            <Landing />
          </motion.div>
        )}

        {phase === "running" && (
          <motion.div key="running" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <PipelineProgress
              elapsedSec={elapsed}
              statusLabel={status}
              url={meta.url}
              states={meta.states}
              scanId={currentScanId}
              startedAt={runStartedAt}
              onCancel={cancel}
            />
          </motion.div>
        )}

        {phase === "results" && results && (
          <motion.div key="results" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Results results={results} evidence={evidence} isDemo={isDemo} onReset={reset} onGenerateBundle={onGenerateBundle} bundle={bundle} />
          </motion.div>
        )}

        {phase === "hunt_running" && (
          <motion.div key="hunt_running" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <HuntProgress
              huntStatus={huntStatus}
              elapsedSec={elapsed}
              sector={huntSector}
              city={huntCity}
              onCancel={cancel}
            />
          </motion.div>
        )}

        {phase === "hunt_results" && huntStatus && (
          <motion.div key="hunt_results" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <HuntResults huntStatus={huntStatus} onReset={reset} />
          </motion.div>
        )}
      </AnimatePresence>

      <footer className="mx-auto max-w-6xl px-5 py-10 text-center text-xs text-slate-600">
        Stops before any payment is submitted · evidence SHA-256 sealed · FTC 16 CFR Part 464
      </footer>
    </div>
  );
}
