import { useState } from "react";
import { motion } from "framer-motion";
import {
  Building2, Home, Car, Ticket, ShoppingCart, Zap, MapPin, Search,
} from "lucide-react";
import type { HuntPreset } from "../types";

interface Props {
  presets: HuntPreset[];
  onStartHunt: (sector: string, city: string, locations: [string, string]) => void;
}

const ICONS: Record<string, React.ElementType> = {
  hotel: Building2, home: Home, car: Car,
  ticket: Ticket, "shopping-cart": ShoppingCart,
};

const RELIABILITY_COLOR: Record<string, string> = {
  Best: "text-fair bg-fair/10 border-fair/30",
  Good: "text-gold-400 bg-gold-500/10 border-gold-500/30",
  Medium: "text-warn bg-warn/10 border-warn/30",
  Experimental: "text-slate-400 bg-slate-500/10 border-slate-500/30",
};

/**
 * Sector hunt cards — auto-discovery flow. The Discovery agent searches the web
 * for sites in the chosen sector, Scout filters out bot-blocked ones, then the
 * full pipeline scans the top picks live from two US states.
 *
 * Rendered BELOW the main hero (URL + location picker). For users who don't
 * have a specific URL in mind — pick a sector, let the agents go hunting.
 */
export default function HuntPresets({ presets, onStartHunt }: Props) {
  const [activeSector, setActiveSector] = useState<string | null>(null);
  const [cities, setCities] = useState<Record<string, string>>({});

  function cityFor(preset: HuntPreset) {
    return cities[preset.id] ?? preset.default_city;
  }
  function handleStart(preset: HuntPreset) {
    const city = cityFor(preset);
    const [a, b] = preset.default_locations as [string, string];
    setActiveSector(preset.id);
    onStartHunt(preset.id, city, [a, b]);
  }

  if (!presets.length) return null;

  return (
    <section className="mx-auto max-w-6xl px-5 py-12">
      <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-xs font-600 uppercase tracking-[0.2em] text-gold-500">
            Or — auto-hunt a sector
          </div>
          <h2 className="mt-2 font-display text-2xl font-700 tracking-tight sm:text-3xl">
            Let the agents pick the targets.
          </h2>
        </div>
        <p className="max-w-md text-sm text-slate-400">
          Discovery agent searches for sites · Scout filters bot-blocked ones · Pipeline scans the
          top picks live from two US locations. ~30–90 s end-to-end.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {presets.map((preset, i) => {
          const Icon = ICONS[preset.icon] ?? Search;
          const reliabilityClass =
            RELIABILITY_COLOR[preset.demo_reliability] ?? RELIABILITY_COLOR.Experimental;
          return (
            <motion.div
              key={preset.id}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-50px" }}
              transition={{ delay: i * 0.06, duration: 0.4 }}
              className="flex h-full flex-col rounded-2xl border border-ink-600 bg-ink-800/80 p-5 shadow-panel backdrop-blur transition-colors hover:border-gold-500/40"
            >
              <div className="mb-3 flex items-start justify-between gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gold-500/15 text-gold-400">
                  <Icon className="h-5 w-5" />
                </div>
                <span
                  className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-600 uppercase tracking-wide ${reliabilityClass}`}
                >
                  {preset.demo_reliability}
                </span>
              </div>

              <h3 className="font-display text-base font-700 text-slate-100">{preset.label}</h3>
              <p className="mt-1 flex-1 text-xs leading-relaxed text-slate-400">
                {preset.description}
              </p>

              <div className="mt-4">
                <label className="mb-1 flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-slate-500">
                  <MapPin className="h-3 w-3 text-gold-400" /> City
                </label>
                <input
                  type="text"
                  value={cityFor(preset)}
                  onChange={(e) =>
                    setCities((prev) => ({ ...prev, [preset.id]: e.target.value }))
                  }
                  className="w-full rounded-lg border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-600 focus:border-gold-500 focus:outline-none"
                />
              </div>

              <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                <span className="font-mono">
                  Compare{" "}
                  <span className="rounded bg-ink-900 px-1.5 py-0.5 text-slate-300">
                    {preset.default_locations[0]}
                  </span>{" "}
                  vs{" "}
                  <span className="rounded bg-ink-900 px-1.5 py-0.5 text-slate-300">
                    {preset.default_locations[1]}
                  </span>
                </span>
              </div>

              <button
                onClick={() => handleStart(preset)}
                disabled={activeSector === preset.id}
                className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gold-500 px-4 py-2.5 font-display text-sm font-600 text-ink-900 shadow-gold transition-all hover:bg-gold-400 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Zap className="h-4 w-4" />
                {activeSector === preset.id ? "Starting hunt…" : "Start hunt"}
              </button>
            </motion.div>
          );
        })}
      </div>
    </section>
  );
}
