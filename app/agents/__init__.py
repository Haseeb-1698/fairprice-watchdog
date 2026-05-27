"""FairPrice Watchdog agent pipeline.

Two-geo demo path agents (Day-3 centerpiece):
  Crawler → Journey Simulator → Diff → geo-compare → evidence vault.

Orchestrated by CrewAI (primary) with a deterministic fallback. See pipeline.py
for the entrypoint `run_scan(scan_id, url, states)`.
"""
