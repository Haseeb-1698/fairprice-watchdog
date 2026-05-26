"""
crew.py — CrewAI orchestration layer (PRD primary orchestrator).

Wraps the same Crawler / Journey / Diff agents as a CrewAI crew so the system is
genuinely agentic: a role-based investigator decides to scan each location via a
tool. The tool does the deterministic real work (pipeline.scan_state) and pushes
structured GeoListings into a collector, so we never depend on the LLM to
faithfully serialize pricing data back through free text.

CrewAI gives us role/goal/backstory framing, planning, and max_rpm rate-limiting
(PRD recommendation). If CrewAI or an LLM provider isn't configured, callers
fall back to the deterministic path in pipeline.py.
"""
from __future__ import annotations

import logging
import threading

from app.agents import pipeline
from app.agents.types import GeoListing
from app.core.config import settings

logger = logging.getLogger(__name__)

# Per-run collector (thread-local so concurrent scans don't bleed into each other).
_ctx = threading.local()


def _build_llm():
    """Configure a CrewAI LLM from the first available provider. Raises if none."""
    from crewai import LLM
    if settings.ANTHROPIC_API_KEY:
        return LLM(model=f"anthropic/{settings.ANTHROPIC_MODEL}", api_key=settings.ANTHROPIC_API_KEY)
    if settings.KIMI_API_KEY:
        return LLM(model=f"openai/{settings.KIMI_MODEL}", base_url=settings.KIMI_ENDPOINT,
                   api_key=settings.KIMI_API_KEY, temperature=1.0)
    if settings.AZURE_KIMI_ENDPOINT and settings.AZURE_KIMI_KEY:
        return LLM(model=f"openai/{settings.AZURE_KIMI_MODEL}", base_url=settings.AZURE_KIMI_ENDPOINT,
                   api_key=settings.AZURE_KIMI_KEY, temperature=1.0)
    if settings.OPENAI_API_KEY:
        return LLM(model=f"openai/{settings.OPENAI_MODEL}", api_key=settings.OPENAI_API_KEY)
    raise RuntimeError("no LLM provider configured for CrewAI")


def run_crew_scan(scan_id: str, url: str, states: list[str]) -> list[GeoListing]:
    """
    Orchestrate the two-geo scan via CrewAI. Returns structured GeoListings
    collected from the tool calls, or [] to signal the caller to fall back.
    """
    from crewai import Agent, Crew, Process, Task
    from crewai.tools import tool

    _ctx.scan_id = scan_id
    _ctx.url = url
    _ctx.results = {}

    @tool("scan_location")
    def scan_location(state: str) -> str:
        """Load the listing from the given US state, walk its checkout, and analyze fees.
        Argument: state — a two-letter US state code (e.g. CA, TX)."""
        gl = pipeline.scan_state(_ctx.scan_id, _ctx.url, state)
        _ctx.results[state.upper()] = gl
        return (f"{state}: advertised ${gl.advertised_price}, final ${gl.final_price}, "
                f"{len(gl.fees)} fees, {sum(f.is_junk_fee for f in gl.fees)} junk.")

    llm = _build_llm()

    investigator = Agent(
        role="Geo-Pricing Investigator",
        goal="Detect hidden fees and location-based price discrimination across US states.",
        backstory=(
            "A regulatory-tech analyst who walks checkout funnels from different US "
            "locations to prove the same listing is priced differently by geography, "
            "stopping before any payment is submitted."
        ),
        tools=[scan_location],
        llm=llm,
        max_rpm=settings.__dict__.get("MAX_RPM", 18),
        verbose=False,
        allow_delegation=False,
    )

    tasks = [
        Task(
            description=(
                f"Use the scan_location tool to scan the listing from state '{st}'. "
                f"Report the advertised price, final total, and any junk fees."
            ),
            expected_output="A one-line pricing summary for the state.",
            agent=investigator,
        )
        for st in states
    ]

    crew = Crew(agents=[investigator], tasks=tasks, process=Process.sequential, verbose=False)
    crew.kickoff()

    # Return in the requested state order; skip any the tool didn't fill.
    ordered = [_ctx.results[s.upper()] for s in states if s.upper() in _ctx.results]
    logger.info("[CrewAI] collected %d/%d location results", len(ordered), len(states))
    return ordered
