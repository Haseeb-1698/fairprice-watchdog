"""
Diff Agent (PRD agent #3, with light Law-Mapping for the demo).

Compares advertised vs. final price, then classifies each captured fee:
whether it is a junk/drip fee and which FTC Unfair-or-Deceptive-Fees-Rule
clause it implicates. Uses the LLM JSON path (changedetection.io is the starred
engine for live page-to-page diffing; here the diff is advertised-vs-checkout
within a single capture, which is what the geo demo needs).

The full Law-Mapper agent (PRD #4) will replace `_classify` with a pgvector
lookup over Matas's FTC taxonomy table; this keeps the same FeeItem output
shape so that swap is drop-in.
"""
from __future__ import annotations

import logging

from app.agents.llm import complete_json
from app.agents.types import FeeItem

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a consumer-protection analyst applying the FTC Unfair or Deceptive Fees Rule "
    "(16 CFR Part 464, effective May 12 2025) and state UDAP statutes. Given an advertised "
    "price, a final checkout total, and the fee line-items in between, decide for EACH fee "
    "whether it is a 'junk fee' (a mandatory or drip-priced charge not included in the "
    "advertised price) and cite the most relevant FTC clause or principle."
)


class DiffAgent:
    name = "Diff"

    def analyze(self, advertised: float, final: float, fees: list[FeeItem]) -> dict:
        """
        Classify fees as junk + map to FTC clauses.

        Returns:
            {"fees": [FeeItem (labeled)], "hidden_total": float, "summary": str}
        """
        hidden_total = round((final or 0) - (advertised or 0), 2)

        if not fees:
            return {"fees": [], "hidden_total": hidden_total,
                    "summary": "No itemized fees captured."}

        labeled = self._classify(advertised, final, fees)
        junk = [f for f in labeled if f.is_junk_fee]
        summary = (
            f"Advertised ${advertised:.2f} → final ${final:.2f}: "
            f"${hidden_total:.2f} in add-ons across {len(labeled)} fee(s), "
            f"{len(junk)} flagged as likely junk fees."
        )
        logger.info("[Diff] %s", summary)
        return {"fees": labeled, "hidden_total": hidden_total, "summary": summary}

    def _classify(self, advertised: float, final: float, fees: list[FeeItem]) -> list[FeeItem]:
        fee_payload = [
            {"fee_name": f.fee_name, "fee_amount": f.fee_amount, "fee_type": f.fee_type}
            for f in fees
        ]
        user = (
            f"Advertised price: ${advertised}\nFinal total: ${final}\n"
            f"Fees: {fee_payload}\n\n"
            'Return JSON: {"fees": [{"fee_name": str, "is_junk_fee": bool, '
            '"ftc_clause": str}]}'
        )
        data = complete_json(system=_SYSTEM, user=user, max_tokens=1500)

        verdicts = {f.get("fee_name"): f for f in (data.get("fees") or [])}
        out: list[FeeItem] = []
        for f in fees:
            v = verdicts.get(f.fee_name, {})
            out.append(
                FeeItem(
                    fee_name=f.fee_name,
                    fee_amount=f.fee_amount,
                    fee_type=f.fee_type,
                    is_junk_fee=bool(v.get("is_junk_fee", False)),
                    ftc_clause=v.get("ftc_clause"),
                )
            )
        return out
