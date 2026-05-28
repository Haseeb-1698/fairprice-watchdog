import { motion } from "framer-motion";
import { COVERAGE, coverage, geoCoord, geoName, type Coverage } from "../lib/coverage";

/**
 * WorldMap — actual SVG world map (not a dotted globe).
 *
 * Equirectangular projection. Continent paths are simplified Natural Earth
 * outlines (public domain). Coverage countries (US + UK + EU 27) are filled in
 * their region colour; selected geoA/geoB get glowing pulse markers.
 *
 * No WebGL, no Three.js, no external map libraries — bulletproof for a live demo.
 */

// Equirectangular: lon ∈ [-180, 180] → x ∈ [0, W]; lat ∈ [-90, 90] → y ∈ [H, 0].
const W = 1000;
const H = 500;
const project = (lon: number, lat: number) => [
  ((lon + 180) / 360) * W,
  ((90 - lat) / 180) * H,
] as const;

// Hand-built simplified continent paths (Natural Earth 110m, hand-traced).
// Lat/lon coords → projected to viewBox.
const CONTINENTS: Array<{ name: string; pts: Array<[number, number]> }> = [
  // North America (simplified)
  { name: "north-america", pts: [
    [-168,66], [-156,71], [-140,70], [-126,69], [-105,71], [-95,73], [-82,75], [-65,80], [-60,72],
    [-58,65], [-53,53], [-60,46], [-67,44], [-76,38], [-76,34], [-81,32], [-81,25], [-90,28],
    [-97,26], [-117,32], [-124,40], [-130,52], [-152,58], [-168,60], [-168,66],
  ]},
  // Central America + Caribbean
  { name: "central-america", pts: [
    [-105,22], [-95,15], [-86,8], [-77,8], [-79,12], [-92,16], [-102,21], [-105,22],
  ]},
  // South America
  { name: "south-america", pts: [
    [-78,12], [-71,12], [-60,9], [-52,5], [-44,-2], [-36,-7], [-38,-22], [-49,-29],
    [-58,-37], [-66,-43], [-72,-53], [-71,-56], [-66,-55], [-65,-43], [-72,-39],
    [-72,-30], [-71,-19], [-78,-10], [-81,-3], [-79,2], [-78,8], [-78,12],
  ]},
  // Africa
  { name: "africa", pts: [
    [-17,21], [-10,33], [0,37], [11,37], [22,32], [33,31], [33,21], [43,12], [51,12],
    [42,0], [42,-12], [35,-23], [25,-34], [18,-35], [11,-17], [9,3], [-5,5], [-13,11],
    [-17,14], [-17,21],
  ]},
  // Europe
  { name: "europe", pts: [
    [-10,36], [-10,43], [-5,43], [0,48], [-5,50], [-2,53], [0,58], [9,58], [13,68],
    [25,71], [30,70], [40,67], [40,55], [37,46], [28,41], [20,40], [9,38], [-1,37], [-10,36],
  ]},
  // Asia (rough)
  { name: "asia", pts: [
    [30,40], [45,42], [60,42], [75,38], [80,30], [97,28], [110,22], [120,30], [135,35],
    [140,45], [150,55], [165,65], [175,70], [165,73], [140,70], [115,72], [80,73],
    [60,70], [35,67], [30,55], [30,40],
  ]},
  // Australia
  { name: "australia", pts: [
    [114,-22], [122,-18], [132,-12], [140,-15], [146,-19], [150,-25], [148,-37], [142,-39],
    [136,-35], [125,-32], [115,-32], [114,-22],
  ]},
];

function pathFromCoords(pts: Array<[number, number]>): string {
  const proj = pts.map(([lon, lat]) => project(lon, lat));
  return "M" + proj.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" L") + " Z";
}

const CONTINENT_PATHS = CONTINENTS.map((c) => ({ name: c.name, d: pathFromCoords(c.pts) }));

const REGION_COLOR: Record<Coverage["region"], string> = {
  US: "#F4C752",   // gold
  UK: "#C084FC",   // violet
  EU: "#60A5FA",   // blue
};

interface Props {
  geoA: string;
  geoB: string;
  className?: string;
}

export default function WorldMap({ geoA, geoB, className = "" }: Props) {
  const a = coverage(geoA);
  const b = coverage(geoB);
  const [ax, ay] = a ? project(...a.coord) : project(...geoCoord(geoA));
  const [bx, by] = b ? project(...b.coord) : project(...geoCoord(geoB));

  // Country circles for every covered jurisdiction. Selected ones get a halo.
  const selectedCodes = new Set([geoA?.toUpperCase(), geoB?.toUpperCase()]);

  return (
    <div className={`relative w-full ${className}`}>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="World map of FairPrice Watchdog coverage" className="block w-full h-auto">
        {/* Ocean background */}
        <defs>
          <radialGradient id="ocean" cx="50%" cy="40%" r="60%">
            <stop offset="0%" stopColor="#0E1A30" />
            <stop offset="100%" stopColor="#050912" />
          </radialGradient>
          <linearGradient id="gridFade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(255,255,255,0.04)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0.02)" />
          </linearGradient>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        <rect x="0" y="0" width={W} height={H} fill="url(#ocean)" rx="14" />

        {/* Latitude gridlines */}
        {[-60, -30, 0, 30, 60].map((lat) => {
          const [, y] = project(0, lat);
          return <line key={lat} x1="0" y1={y} x2={W} y2={y} stroke="url(#gridFade)" strokeWidth="0.5" />;
        })}
        {[-120, -60, 0, 60, 120].map((lon) => {
          const [x] = project(lon, 0);
          return <line key={lon} x1={x} y1="0" x2={x} y2={H} stroke="url(#gridFade)" strokeWidth="0.5" />;
        })}

        {/* Continent landmasses */}
        {CONTINENT_PATHS.map(({ name, d }) => (
          <path
            key={name}
            d={d}
            fill="#1A2235"
            stroke="rgba(212,175,55,0.25)"
            strokeWidth="0.8"
          />
        ))}

        {/* Coverage country markers */}
        {COVERAGE.filter((c) => c.region !== "US" || c.code === "US").map((c) => {
          const [cx, cy] = project(...c.coord);
          const isSelected = selectedCodes.has(c.code);
          const color = REGION_COLOR[c.region];
          return (
            <g key={c.code}>
              {isSelected && (
                <circle cx={cx} cy={cy} r="18" fill={color} opacity="0.12" />
              )}
              <circle
                cx={cx}
                cy={cy}
                r={isSelected ? 5 : 3}
                fill={color}
                opacity={isSelected ? 1 : 0.65}
                stroke={isSelected ? "#fff" : "none"}
                strokeWidth={isSelected ? 1.2 : 0}
              />
            </g>
          );
        })}

        {/* US state pins if either selected geo is a state code */}
        {[geoA, geoB].map((code) => {
          const c = coverage(code);
          if (!c || c.region !== "US" || c.code === "US") return null;
          const [cx, cy] = project(...c.coord);
          return (
            <g key={`pin-${code}`}>
              <motion.circle
                cx={cx}
                cy={cy}
                r="14"
                fill="#EF4444"
                opacity="0.25"
                initial={{ scale: 0.6, opacity: 0.5 }}
                animate={{ scale: [0.8, 1.4, 0.8], opacity: [0.4, 0, 0.4] }}
                transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
              />
              <circle cx={cx} cy={cy} r="4.5" fill="#F4C752" stroke="#fff" strokeWidth="1.5" filter="url(#glow)" />
              <text
                x={cx}
                y={cy - 8}
                textAnchor="middle"
                fontFamily="JetBrains Mono, monospace"
                fontWeight="700"
                fontSize="11"
                fill="#F8FAFC"
              >
                {code.toUpperCase()}
              </text>
            </g>
          );
        })}

        {/* Selected geo labels (countries) */}
        {[a, b].filter((c): c is Coverage => !!c && c.region !== "US").map((c) => {
          const [cx, cy] = project(...c.coord);
          return (
            <text
              key={`lbl-${c.code}`}
              x={cx}
              y={cy - 10}
              textAnchor="middle"
              fontFamily="JetBrains Mono, monospace"
              fontWeight="700"
              fontSize="11"
              fill="#F8FAFC"
            >
              {c.code}
            </text>
          );
        })}

        {/* Connection arc between selected geos */}
        {(() => {
          const cx = (ax + bx) / 2;
          const cy = (ay + by) / 2 - Math.abs(ax - bx) * 0.18 - 30;
          return (
            <path
              d={`M ${ax} ${ay} Q ${cx} ${cy} ${bx} ${by}`}
              stroke="rgba(244,199,82,0.55)"
              strokeWidth="1.5"
              strokeDasharray="4 4"
              fill="none"
              filter="url(#glow)"
            />
          );
        })()}
      </svg>

      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex flex-wrap items-center gap-2 rounded-lg border border-ink-600 bg-ink-900/80 px-2.5 py-1.5 text-[10px] font-mono text-slate-400 backdrop-blur">
        <span className="flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-gold-400 inline-block" /> US — FTC §464</span>
        <span className="flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-purple-400 inline-block" /> UK — DMCCA</span>
        <span className="flex items-center gap-1.5"><i className="h-1.5 w-1.5 rounded-full bg-blue-400 inline-block" /> EU 27 — UCPD</span>
      </div>
      <div className="absolute bottom-3 right-3 rounded-lg border border-gold-600/40 bg-gold-500/10 px-2.5 py-1.5 text-[10px] font-mono text-gold-400 backdrop-blur">
        {geoName(geoA)} ↔ {geoName(geoB)}
      </div>
    </div>
  );
}
