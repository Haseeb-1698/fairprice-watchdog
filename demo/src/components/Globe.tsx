import { useEffect, useRef } from "react";
import { stateCoord, stateName } from "../lib/states";

/**
 * Lightweight "Golden Earth" — a dotted orthographic globe drawn on a 2D canvas.
 * No WebGL/Three.js (reliable for a live demo). It rotates to center the two
 * selected US states and drops glowing pins, with a slow idle drift.
 */
interface Props {
  stateA: string;
  stateB: string;
  size?: number;
}

const DEG = Math.PI / 180;

// Pre-generate a lat/lon dot grid on the sphere.
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

export default function Globe({ stateA, stateB, size = 380 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rot = useRef({ lng: 100, lat: -10 });
  const target = useRef({ lng: 100, lat: -10 });
  const raf = useRef<number>(0);

  // Update target rotation when the selected states change.
  useEffect(() => {
    const a = stateCoord(stateA);
    const b = stateCoord(stateB);
    const midLon = (a[0] + b[0]) / 2;
    const midLat = (a[1] + b[1]) / 2;
    target.current = { lng: -midLon, lat: Math.max(-35, Math.min(35, midLat - 6)) };
  }, [stateA, stateB]);

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

    const project = (lat: number, lon: number, rlng: number, rlat: number) => {
      const phi = lat * DEG;
      const lam = (lon + rlng) * DEG;
      let x = Math.cos(phi) * Math.sin(lam);
      let y = Math.sin(phi);
      let z = Math.cos(phi) * Math.cos(lam);
      const rl = rlat * DEG;
      const y2 = y * Math.cos(rl) - z * Math.sin(rl);
      const z2 = y * Math.sin(rl) + z * Math.cos(rl);
      return { sx: cx + R * x, sy: cy - R * y2, z: z2 };
    };

    const draw = () => {
      // ease rotation toward target + slow idle drift
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

      // dots
      for (const [dlat, dlon] of DOTS) {
        const p = project(dlat, dlon, lng, lat);
        if (p.z <= 0) continue;
        const a = 0.18 + p.z * 0.55;
        const r = 0.8 + p.z * 0.9;
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(244,199,82,${a.toFixed(3)})`;
        ctx.fill();
      }

      // pins
      for (const code of [stateA, stateB]) {
        const [lon0, lat0] = stateCoord(code);
        const p = project(lat0, lon0, lng, lat);
        if (p.z <= 0.05) continue;
        // halo
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, 7, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(239,68,68,0.18)";
        ctx.fill();
        // dot
        ctx.beginPath();
        ctx.arc(p.sx, p.sy, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = "#F4C752";
        ctx.fill();
        ctx.strokeStyle = "#fff";
        ctx.lineWidth = 1;
        ctx.stroke();
        // label
        ctx.font = "600 11px 'JetBrains Mono', monospace";
        ctx.fillStyle = "rgba(248,250,252,0.92)";
        ctx.textAlign = "center";
        ctx.fillText(code.toUpperCase(), p.sx, p.sy - 10);
      }

      raf.current = requestAnimationFrame(draw);
    };
    raf.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf.current);
  }, [size, stateA, stateB]);

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
        aria-label={`Globe centered between ${stateName(stateA)} and ${stateName(stateB)}`}
      />
    </div>
  );
}
