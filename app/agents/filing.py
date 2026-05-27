"""
Filing Agent (PRD agent #6).

Turns a completed scan into a structured, court-ready complaint / evidence
bundle: factual allegations per location, itemized junk fees mapped to FTC
clauses, geo-price-discrimination finding, and a hashed evidence exhibit list.

This produces the STRUCTURED JSON contract — Eman's `/generate-complaint`
endpoint and Eman Bashir's PDF generator (ReportLab/WeasyPrint) render it. The
bundle is also stored in the evidence vault.

Templates: 'ftc' (FTC complaint), 'state_ag' (state AG), 'class_action' (exhibit).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.agents.types import ScanBrief
from app.services import storage

logger = logging.getLogger(__name__)

_TEMPLATES = {
    "ftc": {
        "title": "Complaint for Violation of the FTC Unfair or Deceptive Fees Rule",
        "authority": "Federal Trade Commission — 16 CFR Part 464 (eff. May 12, 2025); FTC Act §5",
        "forum": "Federal Trade Commission",
    },
    "state_ag": {
        "title": "Consumer Protection Complaint (State UDAP / Junk Fee Statutes)",
        "authority": "State Unfair and Deceptive Acts and Practices (UDAP) statutes",
        "forum": "State Attorney General",
    },
    "class_action": {
        "title": "Class-Action Evidence Exhibit — Deceptive Pricing",
        "authority": "FTC 16 CFR Part 464; state UDAP statutes; common-law unjust enrichment",
        "forum": "U.S. District Court",
    },
}


class FilingAgent:
    name = "Filing"

    def build_complaint(self, brief: ScanBrief, complaint_type: str = "ftc", persist: bool = True) -> dict:
        tmpl = _TEMPLATES.get(complaint_type, _TEMPLATES["ftc"])

        allegations, exhibits, total_junk = [], [], 0.0
        for i, l in enumerate(brief.listings, start=1):
            junk = [f for f in l.fees if f.is_junk_fee]
            total_junk += sum(f.fee_amount for f in junk)
            allegations.append({
                "count": i,
                "location_state": l.state,
                "advertised_price": l.advertised_price,
                "final_price": l.final_price,
                "hidden_total": round(l.final_price - l.advertised_price, 2),
                "junk_fees": [
                    {"fee_name": f.fee_name, "amount": f.fee_amount,
                     "fee_type": f.fee_type, "ftc_clause": f.ftc_clause}
                    for f in junk
                ],
                "allegation": (
                    f"The listing was advertised at ${l.advertised_price:.2f} but the "
                    f"checkout total from {l.state} reached ${l.final_price:.2f}, adding "
                    f"${l.final_price - l.advertised_price:.2f} in fees not included in the "
                    f"advertised price, in violation of 16 CFR §464.2(a)."
                ),
            })
            if l.snapshot_sha256:
                exhibits.append({
                    "exhibit": f"{chr(64 + i)}",      # A, B, ...
                    "location_state": l.state,
                    "sha256": l.snapshot_sha256,
                    "storage_path": l.snapshot_path,
                    "download_url": l.snapshot_url,
                    "description": f"Timestamped HTML capture of the checkout funnel from {l.state}.",
                })

        geo = None
        c = brief.comparison
        if c and c.discrimination_detected:
            geo = {
                "finding": "GEOGRAPHIC PRICE DISCRIMINATION",
                "statement": (
                    f"The identical listing, captured at the same time, totaled "
                    f"${max(c.price_a, c.price_b):.2f} from {c.higher_state} versus "
                    f"${min(c.price_a, c.price_b):.2f} from the other state — a "
                    f"${c.delta:.2f} ({c.pct}%) difference based solely on the consumer's location."
                ),
                "delta": c.delta, "pct": c.pct, "higher_state": c.higher_state,
            }

        complaint = {
            "complaint_type": complaint_type,
            "title": tmpl["title"],
            "legal_authority": tmpl["authority"],
            "forum": tmpl["forum"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "subject_url": brief.url,
            "scan_id": brief.scan_id,
            "summary": brief.summary,
            "geo_discrimination": geo,
            "counts": allegations,
            "total_junk_fees_usd": round(total_junk, 2),
            "evidence_exhibits": exhibits,
            "prayer_for_relief": [
                "Order disgorgement of all undisclosed mandatory fees collected from consumers.",
                "Enjoin the practice of advertising prices that exclude mandatory fees (16 CFR §464.2(a)).",
                "Require clear and conspicuous total-price disclosure prior to checkout.",
                "Impose civil penalties as authorized under the FTC Act and applicable state UDAP statutes.",
            ],
            "disclaimer": (
                "Auto-generated by FairPrice Watchdog from automated evidence capture. "
                "Pricing captured up to (but never including) payment submission. "
                "Attorney review required before filing."
            ),
        }

        receipt = None
        if persist:
            receipt = storage.store_json(brief.scan_id, f"complaint-{complaint_type}.json", complaint)
            complaint["_bundle_path"] = receipt.storage_path
            complaint["_bundle_sha256"] = receipt.sha256
            logger.info("[Filing] %s complaint stored → %s", complaint_type, receipt.storage_path)

        return complaint
