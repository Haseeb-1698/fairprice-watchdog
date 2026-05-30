import { motion } from "framer-motion";
import {
  Network, Globe, Footprints, GitCompareArrows, Scale, FileCheck2, Radar,
  Camera, Brain, Database, ShieldCheck, Eye, Hash, Search,
} from "lucide-react";

/**
 * Arch — in-depth architecture page for FairPrice Watchdog.
 *
 * Hand-built SVG (no external diagram lib) with phase bands, typed nodes, and
 * animated flow arrows. Reflects the real system: ingress → geo acquisition
 * (Bright Data) → 6-agent pipeline + intelligence (LLM / vision / web search /
 * memory) → court-ready evidence & delivery.
 */

// Palette (matches the app theme)
const C = {
  gold: "#F4C752", goldDim: "#D4AF37",
  fair: "#34d399", info: "#818cf8", warn: "#fbbf24", violation: "#f87171",
  ink: "#0b1120", panel: "#141d33", line: "#64748b", text: "#e2e8f0", muted: "#94a3b8",
};

// A flowing dash animation for the arrows
const flow = {
  strokeDasharray: "6 6",
  animate: { strokeDashoffset: [0, -24] },
  transition: { duration: 1.1, repeat: Infinity, ease: "linear" as const },
};

function FlowArrow({ d, color = C.line, w = 2, marker = "arr", dashed = false }: any) {
  return (
    <motion.path
      d={d} fill="none" stroke={color} strokeWidth={w}
      markerEnd={`url(#${marker})`}
      strokeDasharray={dashed ? "5 5" : "6 6"}
      animate={{ strokeDashoffset: [0, -24] }}
      transition={{ duration: 1.1, repeat: Infinity, ease: "linear" }}
      opacity={0.85}
    />
  );
}

const STACK = [
  { icon: Globe, label: "Bright Data — Web Unlocker", note: "anti-bot bypass · country geo" },
  { icon: Network, label: "Bright Data — Residential", note: "US state-level geo (CA/TX)" },
  { icon: Camera, label: "Bright Data — Browser API", note: "real Chromium · waits for JS · screenshot" },
  { icon: Search, label: "Bright Data — SERP", note: "Discovery agent targets" },
  { icon: Brain, label: "LLM — Kimi → AIMLAPI", note: "extraction + legal reasoning (fallback chain)" },
  { icon: Eye, label: "Vision — GPT-4o", note: "reads JS-rendered prices off screenshots" },
  { icon: Database, label: "Cognee memory + Postgres/pgvector", note: "cross-scan operator recall" },
];

export default function Arch({ onBack }: { onBack: () => void }) {
  return (
    <section className="mx-auto max-w-6xl px-5 py-10">
      {/* Heading */}
      <div className="mb-2 flex items-center gap-2 text-xs">
        <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-gold-500/15 text-gold-400">
          <Network className="h-3.5 w-3.5" />
        </span>
        <span className="font-600 uppercase tracking-[0.2em] text-gold-500">System Architecture</span>
      </div>
      <h1 className="font-display text-3xl font-700 tracking-tight sm:text-4xl">
        How a URL becomes a <span className="bg-gradient-to-r from-gold-400 to-gold-600 bg-clip-text text-transparent">filable complaint.</span>
      </h1>
      <p className="mt-3 max-w-3xl text-sm text-slate-400 sm:text-base">
        Deterministic ingress on the left, the six-agent pipeline with multi-strategy geo acquisition in the
        middle, and court-ready evidence on the right. Every fetch falls back gracefully; every capture is
        SHA-256 sealed.
      </p>

      {/* Diagram */}
      <div className="mt-8 overflow-x-auto rounded-2xl border border-ink-600 bg-ink-900/60 p-4 shadow-panel">
        <svg viewBox="0 0 1260 600" className="block min-w-[1000px]" role="img"
             aria-label="FairPrice Watchdog architecture diagram">
          <defs>
            {["arr", "ok", "info", "warn", "gold"].map((id) => {
              const fill = id === "ok" ? C.fair : id === "info" ? C.info : id === "warn" ? C.warn
                : id === "gold" ? C.gold : C.line;
              return (
                <marker key={id} id={id} markerWidth="9" markerHeight="9" refX="8" refY="4.5"
                        orient="auto" markerUnits="strokeWidth">
                  <path d="M0,0 L9,4.5 L0,9 z" fill={fill} />
                </marker>
              );
            })}
            <linearGradient id="bandg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(255,255,255,0.035)" />
              <stop offset="100%" stopColor="rgba(255,255,255,0.01)" />
            </linearGradient>
          </defs>

          {/* Phase bands */}
          <rect x="16" y="56" width="270" height="470" rx="14" fill="url(#bandg)" stroke="rgba(148,163,184,0.18)" />
          <rect x="300" y="56" width="600" height="470" rx="14" fill="url(#bandg)" stroke="rgba(244,199,82,0.22)" />
          <rect x="914" y="56" width="330" height="470" rx="14" fill="url(#bandg)" stroke="rgba(52,211,153,0.22)" />
          <text x="151" y="44" textAnchor="middle" fill={C.muted} fontSize="12" fontWeight="700" letterSpacing="1">INGRESS · deterministic</text>
          <text x="600" y="44" textAnchor="middle" fill={C.gold} fontSize="12" fontWeight="700" letterSpacing="1">AGENT PIPELINE · per geo, parallel</text>
          <text x="1079" y="44" textAnchor="middle" fill={C.fair} fontSize="12" fontWeight="700" letterSpacing="1">EVIDENCE &amp; DELIVERY</text>

          {/* ── INGRESS ── */}
          {node(40, 82, "Demo UI", "React · Vite · world map · studio feed", C.gold)}
          {node(40, 168, "FastAPI", "POST /api/scan · normalises geos", C.text)}
          {node(40, 254, "Postgres + pgvector", "scans · listings · fees · evidence", C.text)}
          {node(40, 340, "Redis queue", "scan_queue · hunt_queue · event stream", C.text)}
          {node(40, 426, "Worker (systemd)", "BLPOP · per-geo fan-out · auto-restart", C.info)}
          <FlowArrow d="M151 142 L151 168" />
          <FlowArrow d="M151 228 L151 254" />
          <FlowArrow d="M151 314 L151 340" />
          <FlowArrow d="M151 400 L151 426" />

          {/* ── PIPELINE (center) — 6 agents ── */}
          {agent(320, 82, Globe, "1 · Crawler", "geo-loads listing · reads advertised $", C.gold)}
          {agent(320, 170, Footprints, "2 · Journey Simulator", "walks checkout · STOPS before payment", C.gold)}
          {agent(320, 258, GitCompareArrows, "3 · Diff", "advertised vs final · extracts every fee", C.gold)}
          {agent(320, 346, Scale, "4 · Law-Mapper", "fee → FTC §464 clause · detectability", C.gold)}
          {agent(320, 434, Radar, "5 · Discovery", "web search → candidate operators", C.info)}

          {/* acquisition + intelligence column */}
          {acq(626, 82, Camera, "Bright Data acquisition", "Unlocker → Residential → Browser API", C.fair,
            ["Web Unlocker (anti-bot, 90s)", "Residential (US state geo)", "Browser API (full render + wait)"])}
          {acq(626, 226, Eye, "Vision price read", "GPT-4o reads JS prices off screenshot", C.info,
            ["fires when HTML price is weak", "retry w/ Browser API render", "currency-aware"])}
          {acq(626, 358, Brain, "LLM reasoning", "Kimi → AIMLAPI fallback chain", C.info,
            ["fee classification", "FTC clause mapping", "deterministic mock offline"])}

          {/* arrows within pipeline */}
          <FlowArrow d="M540 116 L626 116" color={C.fair} marker="ok" />
          <FlowArrow d="M540 204 L626 130" color={C.fair} marker="ok" dashed />
          <FlowArrow d="M626 250 L560 280" color={C.info} marker="info" dashed />
          <FlowArrow d="M626 382 L560 372" color={C.info} marker="info" dashed />
          {/* agent chain down */}
          <FlowArrow d="M430 146 L430 170" color={C.gold} marker="gold" />
          <FlowArrow d="M430 234 L430 258" color={C.gold} marker="gold" />
          <FlowArrow d="M430 322 L430 346" color={C.gold} marker="gold" />

          {/* ── EVIDENCE & DELIVERY ── */}
          {node(934, 82, "Evidence Vault", "MinIO / Cloudflare R2 · SHA-256 chain", C.fair)}
          {node(934, 168, "Screenshots", "both geos · sealed · served to UI", C.fair)}
          {agent(934, 254, FileCheck2, "6 · Filing", "court-ready PDF complaint (ReportLab)", C.fair)}
          {node(934, 340, "Studio event stream", "live agent thinking feed (Redis)", C.info)}
          {node(934, 426, "Results + PDF download", "two-geo split · exhibits · one-click PDF", C.gold)}
          <FlowArrow d="M1044 142 L1044 168" color={C.fair} marker="ok" />
          <FlowArrow d="M1044 222 L1044 254" color={C.fair} marker="ok" />
          <FlowArrow d="M1044 312 L1044 340" color={C.info} marker="info" />
          <FlowArrow d="M1044 400 L1044 426" color={C.gold} marker="gold" />

          {/* cross-band: worker → pipeline, pipeline → vault */}
          <FlowArrow d="M262 460 Q300 460 320 120" color={C.info} marker="info" />
          <FlowArrow d="M790 130 Q900 130 934 116" color={C.fair} marker="ok" w={2.4} />

          {/* footer band — placed BELOW the phase bands (which end at y=526) with a gap */}
          <rect x="16" y="548" width="1228" height="36" rx="8" fill="rgba(244,199,82,0.06)" stroke="rgba(244,199,82,0.18)" />
          <text x="36" y="566" fill={C.gold} fontSize="10" fontWeight="700" letterSpacing="0.5">CROSS-CUTTING</text>
          <text x="36" y="579" fill={C.muted} fontSize="11">
            hard 90s/strategy deadlines · 300s/geo cap (never hangs) · credit budget · honesty labels (live / partial / mock) · 29-jurisdiction geo (US · UK · EU 27)
          </text>
        </svg>
      </div>

      {/* Stack legend cards */}
      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {STACK.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }} transition={{ delay: i * 0.05 }}
            className="flex items-start gap-3 rounded-xl border border-ink-600 bg-ink-800/70 p-4"
          >
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gold-500/12 text-gold-400">
              <s.icon className="h-4.5 w-4.5" />
            </span>
            <div>
              <div className="font-display text-sm font-700 text-slate-100">{s.label}</div>
              <div className="mt-0.5 text-xs text-slate-400">{s.note}</div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Principles */}
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          { icon: ShieldCheck, t: "Never hangs", d: "Hard per-strategy deadlines + 300s/geo cap. A blocked site degrades to an honest label, never a frozen demo." },
          { icon: Hash, t: "Court-ready", d: "Every HTML + screenshot capture is SHA-256 sealed and embedded in a filable FTC complaint PDF." },
          { icon: Eye, t: "Reads like a human", d: "When prices are JS-rendered, vision reads them off the fully-rendered screenshot — no brittle selectors." },
        ].map((p) => (
          <div key={p.t} className="rounded-xl border border-ink-600 bg-ink-800/70 p-5">
            <p.icon className="h-5 w-5 text-gold-400" />
            <div className="mt-2 font-display text-base font-700 text-slate-100">{p.t}</div>
            <p className="mt-1 text-sm text-slate-400">{p.d}</p>
          </div>
        ))}
      </div>

      <div className="mt-8">
        <button onClick={onBack} className="inline-flex items-center gap-2 rounded-xl bg-gold-500 px-5 py-2.5 font-display text-sm font-600 text-ink-900 shadow-gold hover:bg-gold-400">
          ← Back to the live demo
        </button>
      </div>
    </section>
  );
}

// ── SVG node helpers ──────────────────────────────────────────────────────────
function node(x: number, y: number, title: string, sub: string, color: string) {
  return (
    <g>
      <rect x={x} y={y} width={222} height={60} rx={11} fill={C.panel} stroke={color} strokeOpacity={0.5} />
      <rect x={x} y={y} width={4} height={60} rx={2} fill={color} />
      <text x={x + 16} y={y + 26} fill={C.text} fontSize="14" fontWeight="700">{title}</text>
      <text x={x + 16} y={y + 45} fill={C.muted} fontSize="11">{sub}</text>
    </g>
  );
}

function agent(x: number, y: number, _Icon: any, title: string, sub: string, color: string) {
  return (
    <g>
      <rect x={x} y={y} width={222} height={64} rx={11} fill={C.panel} stroke={color} strokeOpacity={0.6} />
      <rect x={x} y={y} width={4} height={64} rx={2} fill={color} />
      <text x={x + 16} y={y + 26} fill={color} fontSize="13" fontWeight="800">{title}</text>
      <text x={x + 16} y={y + 47} fill={C.muted} fontSize="11">{sub}</text>
    </g>
  );
}

function acq(x: number, y: number, _Icon: any, title: string, sub: string, color: string, chips: string[]) {
  const h = 30 + chips.length * 22 + 30;
  return (
    <g>
      <rect x={x} y={y} width={244} height={h} rx={12} fill={C.panel} stroke={color} strokeOpacity={0.6} />
      <rect x={x} y={y} width={4} height={h} rx={2} fill={color} />
      <text x={x + 16} y={y + 24} fill={color} fontSize="13" fontWeight="800">{title}</text>
      <text x={x + 16} y={y + 42} fill={C.muted} fontSize="11">{sub}</text>
      {chips.map((c, i) => (
        <g key={c}>
          <rect x={x + 14} y={y + 54 + i * 22} width={216} height={18} rx={4} fill="rgba(255,255,255,0.04)" />
          <text x={x + 22} y={y + 67 + i * 22} fill="#cbd5e1" fontSize="10" fontFamily="JetBrains Mono, monospace">{c}</text>
        </g>
      ))}
    </g>
  );
}
