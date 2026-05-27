"""
Law-Mapper Agent (PRD agent #4).

Maps each detected fee to the most relevant FTC Junk Fee Rule clause using the
taxonomy in ftc_taxonomy.py. Matching strategy, in order of preference:

  1. Semantic — embed the fee name/type and the taxonomy entries (384-dim) and
     pick the highest cosine similarity (same vectors that seed Eman's pgvector
     `fee_taxonomy.embedding` column, so DB and agent agree).
  2. Keyword — substring match against each entry's keywords (offline fallback).

Pure in-memory over a small taxonomy, so it's instant and needs no DB at request
time. It enriches each FeeItem with an authoritative ftc_clause and can upgrade
is_junk_fee when the taxonomy says a fee type is typically junk.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.agents import embeddings
from app.agents.ftc_taxonomy import TaxonomyEntry, all_entries
from app.agents.types import FeeItem

logger = logging.getLogger(__name__)


class LawMapperAgent:
    name = "Law-Mapper"

    def __init__(self) -> None:
        self.entries: list[TaxonomyEntry] = all_entries()
        self._entry_vecs: Optional[list[list[float]]] = None
        if embeddings.available():
            self._entry_vecs = embeddings.embed([e.text() for e in self.entries])

    def enrich(self, fees: list[FeeItem]) -> list[FeeItem]:
        """Set ftc_clause (and upgrade is_junk_fee) on each fee from the taxonomy."""
        for fee in fees:
            entry, score = self._match(fee)
            if entry is None:
                if not fee.ftc_clause:
                    fee.ftc_clause = "Requires manual review against FTC 16 CFR Part 464"
                continue
            fee.ftc_clause = entry.ftc_clause
            # Taxonomy is authoritative for junk status when confident.
            if entry.is_junk and score >= 0.45:
                fee.is_junk_fee = True
            logger.debug("[Law-Mapper] '%s' → %s (score=%.2f)", fee.fee_name, entry.fee_type, score)
        return fees

    def _match(self, fee: FeeItem) -> tuple[Optional[TaxonomyEntry], float]:
        query = f"{fee.fee_name} {fee.fee_type}".strip()

        # 1. Semantic
        if self._entry_vecs is not None:
            qv = embeddings.embed([query])
            if qv:
                sims = [embeddings.cosine(qv[0], ev) for ev in self._entry_vecs]
                best = max(range(len(sims)), key=lambda i: sims[i])
                return self.entries[best], float(sims[best])

        # 2. Keyword
        ql = query.lower()
        best_entry, best_hits = None, 0
        for e in self.entries:
            hits = sum(1 for kw in (e.fee_type, *e.keywords) if kw.replace("_", " ") in ql)
            if hits > best_hits:
                best_entry, best_hits = e, hits
        return (best_entry, 1.0 if best_entry else 0.0)
