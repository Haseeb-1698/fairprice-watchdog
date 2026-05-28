import { useEffect, useRef } from "react";
import { ALL_COUNTRIES, COVERAGE, geoCoord, geoName } from "../lib/coverage";

/**
 * "Golden Earth" — dotted orthographic globe drawn on a 2D canvas (no WebGL).
 *
 * Two modes:
 *   • coverage  — pins every covered jurisdiction (US + UK + EU 27); used in
 *                 the hero to show the global reach.
 *   • focus     — big pulsing pins only on geoA / geoB; used in compact cards.
 *
 * It rotates to center the midpoint of the selected pair and idle-drifts.
 * Accepts either US state codes or country ISO codes via geoA / geoB.
 */
interface Props {
  geoA: string;
  geoB: string;
  size?: number;
  mode?: "coverage" | "focus";
}

const DEG = Math.PI / 180;

function buildDots() {
  const dots: Array<[number, number]> = [];
  for (let lat = -78; lat <= 78; lat += 6) {
    const ring = Math.max(4, Math.round(Math.cos(lat * DEG) * 60));
    for (let i = 0; i < ring; i++) {
      dots.push([lat, -180 + (360 / ring) * i]);
    }
  }
  return dots;
}
const DOTS = buildDots();

export default function Globe({ geoA, geoB, size = 380, mode = "focus" }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rot = useRef({ lng: 80, lat: -10 });
  const target = useRef({ lng: 80, lat: -10 });
  const raf = useRef<number>(0);

  // Update target rotation when the selected geos change.
  useEffect(() => {
    const a = geoCoord(geoA);
    const b = geoCoord(geoB);
    const midLon = (a[0] + b[0]) / 2;
    const midLat = (a[1] + b[1]) / 2;
    target.current = { lng: -midLon, lat: Math.max(-35, Math.min(45, midLat - 6)) };
  }, [geoA, geoB]);

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);
    const R = size / 2 - 14;
    const cx = size / 2;
    const cy = size / 2;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;

    const project = (lat: number, lon: number, rlng: number, rlat: number) => {
      const phi = lat * DEG;
      const lam = (lon + rlng) * DEG;
      const x = Math.cos(phi) * Math.sin(lam);
      const y = Math.sin(phi);
      const z = Math.cos(phi) * Math.cos(lam);
      const rl = rlat * DEG;
      const y2 = y * Math.cos(rl) - z * Math.sin(rl);
      const z2 = y * Math.sin(rl) + z * Math.cos(rl);
      return { sx: cx + R * x, sy: cy - R * y2, z: z2 };
    };

    const draw = () => {
      frame++;
      rot.current.lng += (target.current.lng - rot.current.lng) * 0.06;
      rot.current.lat += (target.current.lat - rot.current.lat) * 0.06;
      if (!reduce) target.current.lng -= 0.05;

      ctx.clearRect(0, 0, size, size);

      // ocean sphere
      const g = ctx.createRadialGradient(cx - R * 0.3, cy - R * 0.3, R * 0.2, cx, cy, R);
      g.addColorStop(0, "#11203a");
      g.addColorStop(1, "#070b16");
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fillStyle = g;
      ctx.fill();
      // gold rim
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = "rgba(212,175,55,0.45)";
      ctx.stroke();

      const { lng, lat } = rot.current;

      // base dot grid
      for (const [dlat, dlon] of DOTS) {
        const p = project(dlat, dlon, lng, lat);
        if (p.z <= 0) continue;
        const a = 0.12 + p.z * 0.42;
        const r = 0.7 + p.z * 0.8;
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(244,199,82,${a.toFixed(3)})`;
        ctx.fill();
      }

      // Coverage pins (small) — every jurisdiction we cover
      if (mode === "coverage") {
        for (const c of COVERAGE) {
          if (c.region === "US" && c.code !== "US") continue; // skip individual US states in coverage view
          const p = project(c.coord[1], c.coord[0], lng, lat);
          if (p.z <= 0.05) continue;
          const a = 0.45 + p.z * 0.4;
          ctx.beginPath();
          ctx.arc(p.sx, p.sy, 2.2 + p.z * 0.8, 0, Math.PI * 2);
          ctx.fillStyle = c.region === "EU"
            ? `rgba(96,165,250,${a.toFixed(3)})`     // EU = blue
            : c.region === "UK"
              ? `rgba(168,85,247,${a.toFixed(3)})`   // UK = violet
              : `rgba(244,199,82,${a.toFixed(3)})`;  // US = gold
          ctx.fill();
        }
      }

      // Big pulsing pins on selected geoA + geoB
      const pulse = reduce ? 0 : (Math.sin(frame * 0.06) + 1) * 0.5;
      for (const code of [geoA, geoB]) {
        const [lon0, lat0] = geoCoord(code);
        const p = project(lat0, lon0, lng, lat);
        if (p.z <= 0.05) continue;
        // halo (pulsing)
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, 8 + pulse * 4, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(239,68,68,${(0.22 - pulse * 0.12).toFixed(3)})`;
        ctx.fill();
        // dot
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, 3.8, 0, Math.PI * 2);
        ctx.fillStyle = "#F4C752";
        ctx.fill();
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 1;
        ctx.stroke();
        // label
        ctx.font = "600 11px 'JetBrains Mono', monospace";
        ctx.fillStyle = "rgba(248,250,252,0.92)";
        ctx.textAlign = "center";
        ctx.fillText(code.toUpperCase(), p.sx, p.sy - 11);
      }

      raf.current = requestAnimationFrame(draw);
    };
    raf.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf.current);
  }, [size, geoA, geoB, mode]);

  return (
    <div className="relative mx-auto" style={{ width: size, height: size }}>
      <div
        className="pointer-events-none absolute inset-0 rounded-full"
        style={{ boxShadow: "0 0 120px -20px rgba(212,175,55,0.4)" }}
        aria-hidden
      />
      <canvas
        ref={canvasRef}
        style={{ width: size, height: size }}
        role="img"
        aria-label={`Globe centered between ${geoName(geoA)} and ${geoName(geoB)}`}
      />
      {mode === "coverage" && (
        <div className="absolute bottom-2 right-2 flex items-center gap-2 rounded-md border border-ink-600 bg-ink-900/80 px-2 py-1 text-[10px] text-slate-400 backdrop-blur">
          <span className="flex items-center gap-1"><i className="h-1.5 w-1.5 rounded-full bg-gold-400 inline-block" /> US</span>
          <span className="flex items-center gap-1"><i className="h-1.5 w-1.5 rounded-full bg-purple-400 inline-block" /> UK</span>
          <span className="flex items-center gap-1"><i className="h-1.5 w-1.5 rounded-full bg-blue-400 inline-block" /> EU 27</span>
        </div>
      )}
    </div>
  );
}

// Keep the small-card consumers (HuntPresets) compiling without changes — they
// use the old `stateA` / `stateB` prop names.
export function FocusGlobe({ stateA, stateB, size = 28 }: { stateA: string; stateB: string; size?: number }) {
  return <Globe geoA={stateA} geoB={stateB} size={size} mode="focus" />;
}
