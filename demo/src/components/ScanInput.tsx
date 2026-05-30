import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Search, MapPin, Zap, Globe2, Mic, Loader2 } from "lucide-react";
import { US_STATES, geoName, COVERAGE } from "../lib/coverage";
import { isLive, transcribeVoice } from "../api";
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

// Team-verified live targets — each scrapes cleanly through the pipeline and
// has a known result. Ranked best-first. Clicking one auto-fills the URL AND
// both locations and switches to Live mode.
interface ProvenTarget {
  rank: number;
  label: string;
  sector: string;
  url: string;
  a: string;
  b: string;
  note: string;
  tier: "Headline" | "Strong" | "Reliable";
}

const PROVEN_TARGETS: ProvenTarget[] = [
  {
    rank: 1,
    label: "Properstar — international property",
    sector: "Real estate · UK↔EU",
    url: "https://www.properstar.com/",
    a: "GB", b: "DE",
    note: "Live scrape · 548 KB · real €100k+ listings · sealed HTML + screenshot",
    tier: "Headline",
  },
  {
    rank: 2,
    label: "GlobalListings — property portal",
    sector: "Real estate · US↔EU",
    url: "https://www.globallistings.com/",
    a: "US", b: "DE",
    note: "Live scrape · real $275k–$2.4M listings · US↔EU coverage",
    tier: "Strong",
  },
  {
    rank: 3,
    label: "ScrapingCourse — product page",
    sector: "E-commerce",
    url: "https://www.scrapingcourse.com/ecommerce/product/abominable-hoodie/",
    a: "CA", b: "TX",
    note: "Live capture $69 · clean single-price scrape + screenshot",
    tier: "Strong",
  },
  {
    rank: 4,
    label: "Books to Scrape — single product",
    sector: "Retail (reliability anchor)",
    url: "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
    a: "CA", b: "TX",
    note: "Always-on £51.77 · proves the full 6-agent pipeline + evidence chain",
    tier: "Reliable",
  },
];

const TIER_STYLE: Record<ProvenTarget["tier"], string> = {
  Headline: "border-gold-500/50 bg-gold-500/10 text-gold-300",
  Strong: "border-fair/40 bg-fair/10 text-fair",
  Reliable: "border-ink-600 bg-ink-700 text-slate-400",
};

export default function ScanInput({ live, onRun, disabled }: Props) {
  const [url, setUrl] = useState(PROVEN_TARGETS[0].url);
  const [a, setA] = useState(PROVEN_TARGETS[0].a);
  const [b, setB] = useState(PROVEN_TARGETS[0].b);
  const [mode, setMode] = useState<RunMode>(live ? "live" : "demo");
  const [touched, setTouched] = useState(false);
  const [pickedTarget, setPickedTarget] = useState<number>(PROVEN_TARGETS[0].rank);

  function selectTarget(t: ProvenTarget) {
    setUrl(t.url);
    setA(t.a);
    setB(t.b);
    setPickedTarget(t.rank);
    if (live) setMode("live");   // proven targets run live, not mock
    setTouched(false);
  }

  // Voice scan state
  const [voiceState, setVoiceState] = useState<"idle" | "recording" | "transcribing">("idle");
  const [voiceMsg, setVoiceMsg] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function toggleVoice() {
    if (voiceState === "recording") {
      recorderRef.current?.stop();
      return;
    }
    if (voiceState === "transcribing") return;
    setVoiceMsg(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setVoiceState("transcribing");
        try {
          const blob = new Blob(chunksRef.current, { type: "audio/webm" });
          const intent = await transcribeVoice(blob);
          setVoiceMsg(`Heard: "${intent.transcript}"`);
          if (intent.url) setUrl(intent.url);
          if (intent.locations && intent.locations.length >= 2) {
            setA(intent.locations[0]);
            setB(intent.locations[1]);
          }
        } catch (err) {
          setVoiceMsg("Couldn't transcribe — type your target instead.");
        } finally {
          setVoiceState("idle");
        }
      };
      rec.start();
      recorderRef.current = rec;
      setVoiceState("recording");
      // Auto-stop after 7s so the clip stays short.
      window.setTimeout(() => { if (rec.state === "recording") rec.stop(); }, 7000);
    } catch {
      setVoiceMsg("Microphone access denied.");
      setVoiceState("idle");
    }
  }

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
        <div className="flex gap-2">
          <div className="relative flex-1">
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
          {isLive() && (
            <button
              type="button"
              onClick={toggleVoice}
              title="Speak your target — e.g. 'scan booking dot com from California and Texas'"
              className={`flex shrink-0 items-center gap-1.5 rounded-xl border px-3 text-sm font-medium transition-colors ${
                voiceState === "recording"
                  ? "border-violation/60 bg-violation/15 text-violation animate-pulse"
                  : voiceState === "transcribing"
                    ? "border-gold-500/40 bg-gold-500/10 text-gold-400"
                    : "border-ink-600 bg-ink-900 text-slate-300 hover:border-gold-500/60 hover:text-gold-400"
              }`}
            >
              {voiceState === "transcribing" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Mic className="h-4 w-4" />
              )}
              <span className="hidden sm:inline">
                {voiceState === "recording" ? "Listening…" : voiceState === "transcribing" ? "…" : "Voice"}
              </span>
            </button>
          )}
        </div>
        {touched && !urlValid && (
          <p role="alert" className="mt-1.5 text-xs text-violation">Enter a valid http(s) URL to scan.</p>
        )}
        {voiceMsg && (
          <p className="mt-1.5 text-xs text-gold-400">{voiceMsg}</p>
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
                      {c.name} ({c.code})
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

        {/* Team-verified live targets — click to auto-fill URL + locations */}
        <div className="mt-5">
          <div className="mb-2 flex items-center gap-2 text-xs">
            <span className="font-600 uppercase tracking-wider text-gold-500">Proven live targets</span>
            <span className="rounded bg-fair/15 px-1.5 py-0.5 text-[10px] font-600 uppercase text-fair">team-verified</span>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {PROVEN_TARGETS.map((t) => {
              const active = pickedTarget === t.rank && url === t.url;
              return (
                <button
                  key={t.rank}
                  type="button"
                  onClick={() => selectTarget(t)}
                  className={`flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition-colors ${
                    active
                      ? "border-gold-500/70 bg-gold-500/10"
                      : "border-ink-600 bg-ink-900/60 hover:border-gold-500/40"
                  }`}
                >
                  <div className="flex w-full items-center gap-2">
                    <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-ink-700 font-mono text-[10px] font-700 text-slate-300">
                      {t.rank}
                    </span>
                    <span className="flex-1 truncate font-display text-sm font-600 text-slate-100">{t.label}</span>
                    <span className={`shrink-0 rounded-full border px-1.5 py-0.5 text-[9px] font-600 uppercase ${TIER_STYLE[t.tier]}`}>
                      {t.tier}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-slate-500">
                    <span>{t.sector}</span>
                    <span className="font-mono text-slate-400">{t.a} vs {t.b}</span>
                  </div>
                  <p className="text-[11px] leading-snug text-slate-500">{t.note}</p>
                </button>
              );
            })}
          </div>
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
