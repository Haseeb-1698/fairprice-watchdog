# FairPrice Watchdog — Demo UI

A live, judge-facing demo for the FairPrice Watchdog pipeline. Paste a target URL,
pick two US states, and watch the 6-agent pipeline run in real time, then see the
two-state price split, junk fees mapped to FTC clauses, and the hash-sealed evidence vault.

Built with **React + Vite + TypeScript + Tailwind + framer-motion**. No WebGPU/Three.js —
optimized for a reliable live demo.

## Quick start

```bash
cd demo
npm install
cp .env.example .env          # optional — set VITE_API_BASE to your API
npm run dev                   # http://localhost:5173
```

## Backend connection

Set `VITE_API_BASE` in `.env`:

| Value | Behavior |
|---|---|
| `http://64.176.221.147:8000` | Live scans against the deployed VM API |
| `http://localhost:8000` | Live against a local backend |
| *(blank)* | **Demo mode** — built-in mock data, no backend or credits needed |

The UI calls: `POST /api/scan {url, geos}`, `GET /api/results/{id}`, `GET /api/evidence/{id}`,
`POST /api/generate-complaint/{id}`.

## Reliability (no hanging)

- **Live mode** polls `GET /api/results/{id}` with a live elapsed timer and a hard
  ~210s ceiling. Each request has its own 12s timeout. Progress is always visible —
  never a frozen spinner.
- If the backend is **slow or unreachable**, the UI automatically **falls back to demo
  data** with a notice, so the flow always lands on the punchline.
- A **Live / Demo** toggle lets the presenter force the instant mock path.

## Three sections

1. **Hero + scan input** — URL, two states, presets, Live/Demo toggle.
2. **Agent pipeline** — Crawler → Journey → Diff → Law-Mapper → Discovery → Filing,
   with per-stage status + elapsed timer.
3. **Results** — two-state price split (advertised vs final + gap %), itemized junk
   fees with FTC clauses, evidence vault (SHA-256), and a one-click evidence bundle.

## Build

```bash
npm run build      # type-checks + bundles to dist/
npm run preview    # serve the production build
```
