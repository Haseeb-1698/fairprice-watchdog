import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle, ShieldCheck, FileDown, Hash, FileWarning,
  TrendingUp, Scale, RotateCcw, Loader2, ExternalLink, ArrowLeft, Camera,
} from "lucide-react";
import type { EvidenceSnapshot, Listing, ScanResults } from "../types";
import { stateName } from "../lib/states";
import { API_BASE, isLive, generatePdfComplaint } from "../api";

const money = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

// Detectability tag derived from the FTC clause (works for live + mock).
function detectTag(clause?: string | null, isJunk?: boolean) {
  const c = (clause || "").toLowerCase();
  if (c.includes("outside rule scope") || c.includes("exempt") || c.includes("government"))
    return { label: "Exempt (govt)", cls: "bg-slate-500/15 text-slate-400" };
  if (c.includes("464.3") || c.includes("misrepresent"))
    return { label: "Needs review", cls: "bg-warn/15 text-warn" };
  if (isJunk) return { label: "Agent-clean", cls: "bg-fair/15 text-fair" };
  return null;
}

interface Props {
  results: ScanResults;
  evidence: EvidenceSnapshot[];
  isDemo: boolean;
  onReset: () => void;
  onGenerateBundle: () => void;
  bundle: { state: "idle" | "loading" | "done" | "error"; url?: string; kind?: "blob" | "link" };
}

export default function Results({ results, evidence, isDemo, onReset, onGenerateBundle, bundle }: Props) {
  const listings = results.listings || [];
  const cmp = useMemo(() => {
    if (listings.length < 2) return null;
    const [x, y] = listings;
    const high = x.final_price >= y.final_price ? x : y;
    const low = high === x ? y : x;
    const delta = Math.round((high.final_price - low.final_price) * 100) / 100;
    const pct = low.final_price ? Math.round((delta / low.final_price) * 1000) / 10 : 0;
    return { high, low, delta, pct };
  }, [listings]);

  const junkTotal = listings.reduce(
    (s, l) => s + l.fees.filter((f) => f.is_junk_fee).reduce((a, f) => a + f.fee_amount, 0),
    0
  );
  const discrimination = !!cmp && cmp.delta >= 1;

  // Graceful empty state (e.g. live scan completed but extracted no priced data)
  if (listings.length === 0) {
    return (
      <section className="mx-auto max-w-3xl px-5 py-16 text-center">
        <FileWarning className="mx-auto h-10 w-10 text-warn" />
        <h2 className="mt-4 font-display text-2xl font-600">Scan finished — no priced data extracted</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-slate-400">
          Status: <span className="font-mono text-slate-300">{results.scan?.status}</span>. The agents ran but
          couldn't read prices from this page (it may be heavily bot-protected or price by listing, not viewer).
          Try a viewer-priced target (hotel, car rental, ticketing) or Demo mode.
        </p>
        <button onClick={onReset} className="mt-6 inline-flex items-center gap-2 rounded-xl border border-ink-600 px-5 py-2.5 text-sm text-slate-200 hover:border-gold-500/60">
          <RotateCcw className="h-4 w-4" /> New scan
        </button>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-5xl px-5 py-10">
      {/* Back to new-scan */}
      <div className="mb-4">
        <button
          onClick={onReset}
          className="inline-flex items-center gap-1.5 rounded-xl border border-ink-600 bg-ink-800/60 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-gold-500/40 hover:text-gold-400"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to new scan
        </button>
      </div>

      {/* Verdict banner */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className={`flex flex-col gap-3 rounded-2xl border p-5 sm:flex-row sm:items-center sm:justify-between ${
          discrimination ? "border-violation/40 bg-violation/10" : "border-ink-600 bg-ink-800/80"
        }`}
      >
        <div className="flex items-center gap-3">
          {discrimination ? (
            <AlertTriangle className="h-7 w-7 shrink-0 text-violation" />
          ) : (
            <ShieldCheck className="h-7 w-7 shrink-0 text-fair" />
          )}
          <div>
            <h2 className="font-display text-lg font-700 sm:text-xl">
              {discrimination ? "Geographic price discrimination detected" : "No significant geo price gap"}
            </h2>
            {results.scan?.url ? (
              <a
                href={results.scan.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 font-mono text-xs text-slate-400 underline decoration-slate-600 underline-offset-2 hover:text-gold-400"
                title="Open the exact page that was scanned"
              >
                {results.scan.url}
                <ExternalLink className="h-3 w-3" />
              </a>
            ) : null}
            {isDemo && <span className="ml-1 font-mono text-xs text-slate-500">· demo data</span>}
          </div>
        </div>
        <button onClick={onReset} className="inline-flex items-center gap-2 self-start rounded-xl border border-ink-600 px-4 py-2 text-sm text-slate-300 hover:border-gold-500/60 sm:self-auto">
          <RotateCcw className="h-4 w-4" /> New scan
        </button>
      </motion.div>

      {/* Two-state split — the showstopper */}
      <div className="mt-6 grid grid-cols-1 items-stretch gap-4 md:grid-cols-[1fr_auto_1fr]">
        {cmp && [cmp.low, cmp.high].map((l, idx) => (
          <PriceCard key={l.location_state} listing={l} highlight={idx === 1 && discrimination} />
        ))}
        {cmp && (
          <div className="order-first flex items-center justify-center md:order-none">
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 200, damping: 18, delay: 0.15 }}
              className="rounded-2xl border border-gold-600/40 bg-gradient-to-b from-gold-500/15 to-transparent px-6 py-5 text-center"
            >
              <div className="flex items-center justify-center gap-1 text-xs uppercase tracking-wider text-gold-400">
                <TrendingUp className="h-3.5 w-3.5" /> Gap
              </div>
              <div className="mt-1 font-display text-3xl font-700 tabular text-gold-400 sm:text-4xl">
                {money(cmp.delta)}
              </div>
              <div className="mt-1 font-mono text-sm tabular text-slate-300">+{cmp.pct}%</div>
              <div className="mt-2 max-w-[10rem] text-xs text-slate-400">
                more in {stateName(cmp.high.location_state)}, same listing & moment
              </div>
            </motion.div>
          </div>
        )}
      </div>

      {/* Fees per location */}
      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
        {listings.map((l) => (
          <FeeBreakdown key={"fees-" + l.location_state} listing={l} />
        ))}
      </div>

      {/* Summary strip */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Junk fees flagged" value={String(listings.reduce((s, l) => s + l.fees.filter((f) => f.is_junk_fee).length, 0))} icon={<FileWarning className="h-4 w-4" />} />
        <Stat label="Hidden fee total" value={money(junkTotal)} icon={<Scale className="h-4 w-4" />} />
        <Stat label="Locations" value={String(listings.length)} icon={<TrendingUp className="h-4 w-4" />} />
        <Stat label="Evidence snapshots" value={String(evidence.length)} icon={<Hash className="h-4 w-4" />} />
      </div>

      {/* Visual evidence — both locations' screenshots side by side */}
      <ScreenshotEvidence scanId={results.scan?.id} states={listings.map((l) => l.location_state)} />

      {/* Evidence vault */}
      <div className="mt-8 rounded-2xl border border-ink-600 bg-ink-800/80 p-5 shadow-panel">
        <div className="flex items-center justify-between gap-3">
          <h3 className="flex items-center gap-2 font-display text-lg font-600">
            <Hash className="h-5 w-5 text-gold-400" /> Evidence vault
          </h3>
          <div className="flex flex-wrap items-center gap-2">
            {isLive() && results.scan?.id && <PdfComplaintButton scanId={results.scan.id} />}
            <BundleButton bundle={bundle} onClick={onGenerateBundle} />
          </div>
        </div>
        <p className="mt-1 text-xs text-slate-500">Timestamped HTML captures, SHA-256 sealed for chain-of-custody.</p>
        <ul className="mt-4 space-y-2">
          {evidence.length === 0 && <li className="text-sm text-slate-500">No snapshots returned.</li>}
          {evidence.map((e) => (
            <li key={e.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-ink-600 bg-ink-900/50 p-3">
              {e.state && <span className="rounded-md bg-gold-500/15 px-2 py-0.5 text-xs font-600 text-gold-400">{e.state}</span>}
              <code className="font-mono text-xs text-slate-300 break-all">{e.sha256_hash}</code>
              {e.storage_path && <span className="ml-auto truncate font-mono text-[11px] text-slate-600">{e.storage_path}</span>}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function PriceCard({ listing, highlight }: { listing: Listing; highlight: boolean }) {
  const hidden = Math.round((listing.final_price - listing.advertised_price) * 100) / 100;
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-2xl border p-5 ${highlight ? "border-violation/50 bg-violation/5 shadow-[0_0_40px_-12px_rgba(239,68,68,0.4)]" : "border-ink-600 bg-ink-800/80"}`}
    >
      <div className="flex items-center justify-between">
        <span className="font-display text-lg font-600">{stateName(listing.location_state)}</span>
        <span className="rounded-md border border-ink-600 px-2 py-0.5 font-mono text-xs text-slate-400">{listing.location_state}</span>
      </div>
      <dl className="mt-4 space-y-2 text-sm">
        <div className="flex items-center justify-between">
          <dt className="text-slate-400">Advertised</dt>
          <dd className="font-mono tabular text-slate-300">{money(listing.advertised_price)}</dd>
        </div>
        <div className="flex items-center justify-between border-t border-ink-600 pt-2">
          <dt className="text-slate-200">Final total</dt>
          <dd className="font-mono tabular text-xl font-700 text-slate-50">{money(listing.final_price)}</dd>
        </div>
        <div className="flex items-center justify-between">
          <dt className="text-slate-500">Hidden in checkout</dt>
          <dd className="font-mono tabular text-violation">+{money(hidden)}</dd>
        </div>
      </dl>
    </motion.div>
  );
}

function FeeBreakdown({ listing }: { listing: Listing }) {
  return (
    <div className="rounded-2xl border border-ink-600 bg-ink-800/80 p-5">
      <h4 className="font-display text-sm font-600 text-slate-200">
        Fees added in {stateName(listing.location_state)}
      </h4>
      <ul className="mt-3 space-y-2">
        {listing.fees.length === 0 && <li className="text-sm text-slate-500">No itemized fees captured.</li>}
        {listing.fees.map((f, i) => (
          <li key={i} className="group rounded-lg border border-ink-600 bg-ink-900/40 p-2.5">
            <div className="flex items-center justify-between gap-2">
              <span className="flex flex-wrap items-center gap-2 text-sm text-slate-200">
                {f.is_junk_fee && (
                  <span className="rounded bg-violation/15 px-1.5 py-0.5 text-[10px] font-700 uppercase tracking-wide text-violation">Junk</span>
                )}
                {(() => {
                  const t = detectTag(f.ftc_clause, f.is_junk_fee);
                  return t ? (
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-600 ${t.cls}`}>{t.label}</span>
                  ) : null;
                })()}
                {f.fee_name}
              </span>
              <span className="font-mono tabular text-sm text-slate-100">{money(f.fee_amount)}</span>
            </div>
            {f.ftc_clause && (
              <p className="mt-1 flex items-start gap-1.5 text-[11px] leading-snug text-slate-500">
                <Scale className="mt-0.5 h-3 w-3 shrink-0 text-gold-600" />
                <span>
                  <span className="font-mono font-700 text-gold-500">
                    {(f.ftc_clause || "").split(" ").slice(0, 3).join(" ")}
                  </span>{" "}
                  <span className="text-slate-500">
                    {(f.ftc_clause || "").split(" ").slice(3).join(" ")}
                  </span>
                </span>
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ScreenshotEvidence({ scanId, states }: { scanId?: string; states: string[] }) {
  const [available, setAvailable] = useState<Record<string, boolean>>({});
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!scanId || !isLive()) { setChecked(true); return; }
    fetch(`${API_BASE}/api/screenshots/${scanId}`, { signal: AbortSignal.timeout(8000) })
      .then((r) => r.json())
      .then((d) => {
        const map: Record<string, boolean> = {};
        (d.screenshots || []).forEach((s: any) => { map[(s.state || "").toUpperCase()] = true; });
        setAvailable(map);
      })
      .catch(() => {})
      .finally(() => setChecked(true));
  }, [scanId]);

  if (!checked) return null;
  const shots = states.filter((s) => available[s.toUpperCase()]);
  if (!scanId || shots.length === 0) return null;

  return (
    <div className="mt-8">
      <h3 className="mb-1 flex items-center gap-2 font-display text-lg font-600">
        <Camera className="h-5 w-5 text-gold-400" /> Visual evidence — captured checkouts
      </h3>
      <p className="mb-3 text-xs text-slate-500">
        Full-page screenshots taken at scan time, sealed with SHA-256 in the evidence vault and embedded in the PDF complaint.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {shots.map((s) => (
          <figure key={s} className="overflow-hidden rounded-xl border border-ink-600 bg-ink-900">
            <figcaption className="flex items-center justify-between border-b border-ink-600 px-3 py-2">
              <span className="font-display text-sm font-600 text-slate-100">{stateName(s)}</span>
              <span className="rounded-md border border-ink-600 px-2 py-0.5 font-mono text-[10px] text-slate-400">{s}</span>
            </figcaption>
            <a
              href={`${API_BASE}/api/screenshot/${scanId}/${s}`}
              target="_blank"
              rel="noreferrer"
              title="Open full screenshot"
            >
              <img
                src={`${API_BASE}/api/screenshot/${scanId}/${s}`}
                alt={`Captured checkout from ${stateName(s)}`}
                loading="lazy"
                className="block max-h-[420px] w-full object-cover object-top transition-opacity hover:opacity-90"
              />
            </a>
          </figure>
        ))}
      </div>
    </div>
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

function PdfComplaintButton({ scanId }: { scanId: string }) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");

  async function run() {
    if (state === "loading") return;
    setState("loading");
    try {
      const url = await generatePdfComplaint(scanId);
      // Trigger the download programmatically (one click, no second step).
      const a = document.createElement("a");
      a.href = url;
      a.download = `ftc-complaint-${scanId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
      setState("done");
    } catch {
      setState("error");
    }
  }

  return (
    <button
      onClick={run}
      disabled={state === "loading"}
      title="Generate + download the court-ready FTC complaint PDF (with screenshot exhibits)"
      className={`inline-flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-600 disabled:opacity-50 ${
        state === "done"
          ? "border-fair/50 bg-fair/10 text-fair"
          : "border-gold-500/50 bg-gold-500/10 text-gold-300 hover:bg-gold-500/20"
      }`}
    >
      {state === "loading" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />}
      {state === "loading" ? "Building PDF… (~30s)"
        : state === "done" ? "PDF downloaded ✓ — click for another"
        : state === "error" ? "PDF failed — retry"
        : "Download PDF complaint"}
    </button>
  );
}

function BundleButton({ bundle, onClick }: { bundle: Props["bundle"]; onClick: () => void }) {
  if (bundle.state === "done" && bundle.url) {
    return (
      <a
        href={bundle.url}
        download={bundle.kind === "blob" ? "fairprice-evidence-bundle.zip" : undefined}
        target={bundle.kind === "link" ? "_blank" : undefined}
        rel="noreferrer"
        className="inline-flex items-center gap-2 rounded-xl bg-fair px-4 py-2 text-sm font-600 text-ink-900"
      >
        {bundle.kind === "link" ? <ExternalLink className="h-4 w-4" /> : <FileDown className="h-4 w-4" />}
        Download bundle
      </a>
    );
  }
  return (
    <button
      onClick={onClick}
      disabled={bundle.state === "loading"}
      className="inline-flex items-center gap-2 rounded-xl bg-gold-500 px-4 py-2 text-sm font-600 text-ink-900 transition-colors hover:bg-gold-400 disabled:opacity-50"
    >
      {bundle.state === "loading" ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />}
      {bundle.state === "loading" ? "Sealing…" : bundle.state === "error" ? "Retry bundle" : "Generate Evidence Bundle"}
    </button>
  );
}
