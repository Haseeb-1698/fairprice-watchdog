"""
gen_taxonomy_from_xlsx.py — regenerate app/agents/ftc_taxonomy.py from Matas's
FTC_Fee_Taxonomy.xlsx (the authoritative domain sheet).

Keeps the agent's vocabulary in lockstep with the domain sheet. Re-run whenever
Matas updates the spreadsheet:

    python scripts/gen_taxonomy_from_xlsx.py /path/to/FTC_Fee_Taxonomy.xlsx

Derived columns I add on the agent side (until Matas adds his own):
  • sector            — lodging / ticketing / rental (rule scope context)
  • is_government     — tax / government charges (excluded from junk-fee total)
  • is_junk          — agent-clean & partial → True; na → False
  • real-world labels — famous enforcement labels folded into keywords
"""
import sys
import os

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
# Source of truth lives in the repo at docs/FTC_Fee_Taxonomy.xlsx (owned by Matas).
DEFAULT_XLSX = os.path.join(HERE, "..", "docs", "FTC_Fee_Taxonomy.xlsx")
OUT = os.path.join(HERE, "..", "app", "agents", "ftc_taxonomy.py")

# Sector context (rule covers lodging + ticketing federally; rentals via §5/UDAP).
SECTOR = {
    "resort": "lodging", "cleaning": "lodging", "amenity": "lodging", "facility": "lodging",
    "booking": "lodging,ticketing", "convenience": "ticketing", "processing": "ticketing,lodging",
    "service": "lodging,ticketing", "admin": "rental", "parking": "rental,lodging",
    "pet": "rental", "delivery": "rental", "early_termination": "rental",
    "security_deposit": "rental", "mandatory_gratuity": "lodging", "tax": "all",
}
# Famous real-world enforcement labels to fold into keyword matching.
EXTRA_LABELS = {
    "admin": ["smart home technology", "utility management"],  # Invitation Homes
    "resort": ["urban destination charge"],
}
STATE_UDAP = "Rental-sector fee: enforce via FTC Act §5 + state UDAP statutes (federal Junk Fees Rule covers lodging+ticketing today; rental rule in FTC rulemaking since Dec 2025)."


def norm_detect(v: str) -> str:
    v = (v or "").lower()
    if "agent-clean" in v:
        return "agent-clean"
    if "n/a" in v or "outside" in v:
        return "na"
    return "partial"


def main():
    xlsx = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_XLSX
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    ws = wb["FTC Fee Taxonomy"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h) for h in rows[0]]
    entries = []
    for r in rows[1:]:
        d = dict(zip(hdr, r))
        ft = str(d["fee_type"]).strip()
        if not ft or ft == "None":
            continue
        detect = norm_detect(str(d.get("detectability")))
        kws = [k.strip() for k in str(d.get("keywords") or "").split(",") if k.strip()]
        kws += EXTRA_LABELS.get(ft, [])
        is_gov = ft == "tax" or "outside rule scope" in str(d.get("ftc_clause") or "").lower()
        entries.append({
            "fee_type": ft,
            "ftc_clause": str(d.get("ftc_clause") or "").strip(),
            "clause_plain": str(d.get("clause_plain_language") or "").strip(),
            "description": str(d.get("description") or "").strip(),
            "keywords": tuple(dict.fromkeys(kws)),  # dedupe, keep order
            "detectability": detect,
            "sector": SECTOR.get(ft, "all"),
            "is_junk": detect != "na",
            "is_government": is_gov,
            "state_udap": STATE_UDAP if SECTOR.get(ft, "").startswith("rental") else "",
            "agent_observation": str(d.get("agent_observation") or "").strip(),
            "notes": str(d.get("notes") or "").strip(),
        })

    body = ['"""',
            "ftc_taxonomy.py — FTC Junk Fee Rule taxonomy.",
            "",
            "AUTO-GENERATED from FTC_Fee_Taxonomy.xlsx (Matas, domain owner) by",
            "scripts/gen_taxonomy_from_xlsx.py. Do not edit by hand — edit the sheet and re-run.",
            "Clauses + detectability are Matas's; sector / is_government / real-world labels are",
            "derived on the agent side.",
            '"""',
            "from __future__ import annotations",
            "",
            "from dataclasses import dataclass",
            "",
            "",
            "@dataclass(frozen=True)",
            "class TaxonomyEntry:",
            "    fee_type: str",
            "    ftc_clause: str",
            "    clause_plain: str",
            "    description: str",
            "    keywords: tuple[str, ...]",
            "    detectability: str  # agent-clean | partial | na",
            "    sector: str",
            "    is_junk: bool",
            "    is_government: bool",
            "    state_udap: str = ''",
            "    agent_observation: str = ''",
            "    notes: str = ''",
            "",
            "    def text(self) -> str:",
            "        return f'{self.fee_type}: {self.description} ({\" \".join(self.keywords)})'",
            "",
            "",
            "FTC_TAXONOMY: list[TaxonomyEntry] = ["]
    for e in entries:
        body.append("    TaxonomyEntry(")
        for k in ("fee_type", "ftc_clause", "clause_plain", "description"):
            body.append(f"        {k}={e[k]!r},")
        body.append(f"        keywords={e['keywords']!r},")
        body.append(f"        detectability={e['detectability']!r},")
        body.append(f"        sector={e['sector']!r},")
        body.append(f"        is_junk={e['is_junk']!r},")
        body.append(f"        is_government={e['is_government']!r},")
        body.append(f"        state_udap={e['state_udap']!r},")
        body.append(f"        agent_observation={e['agent_observation']!r},")
        body.append(f"        notes={e['notes']!r},")
        body.append("    ),")
    body.append("]")
    body.append("")
    body.append("")
    body.append("def all_entries() -> list[TaxonomyEntry]:")
    body.append("    return list(FTC_TAXONOMY)")
    body.append("")

    out = os.path.abspath(OUT)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(body))
    print(f"Wrote {len(entries)} entries -> {out}")


if __name__ == "__main__":
    main()
