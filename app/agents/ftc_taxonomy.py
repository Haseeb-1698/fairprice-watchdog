"""
ftc_taxonomy.py — v1 FTC Junk Fee Rule taxonomy (Haseeb seed).

Maps common drip/junk fee types to the relevant clause of the FTC Rule on
Unfair or Deceptive Fees (16 CFR Part 464, effective May 12, 2025) and the
general UDAP principle. This is a STARTER seed so the Law-Mapper works today;
when Matas delivers the authoritative taxonomy spreadsheet, re-seed the same
`fee_taxonomy` table / replace this list — the agent contract is unchanged.

Rule summary used here:
  • §464.2(a) — must disclose the TOTAL PRICE (incl. all mandatory fees) clearly
    and prominently, more prominently than any other pricing info.
  • §464.2(b) — must not misrepresent the nature/purpose/amount of any fee.
  • §464.3 — "total price" may exclude government charges and shipping, which
    must still be disclosed before the consumer consents to pay.

Each entry: fee_type, is_junk (typical default), ftc_clause, description, keywords.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxonomyEntry:
    fee_type: str
    is_junk: bool
    ftc_clause: str
    description: str
    keywords: tuple[str, ...]

    def text(self) -> str:
        return f"{self.fee_type}: {self.description} ({' '.join(self.keywords)})"


FTC_TAXONOMY: list[TaxonomyEntry] = [
    TaxonomyEntry("resort_fee", True,
        "16 CFR §464.2(a) — mandatory resort fee omitted from the advertised total price",
        "A mandatory daily/stay fee for amenities, not included in the headline price.",
        ("resort", "destination", "amenity", "facility")),
    TaxonomyEntry("cleaning_fee", True,
        "16 CFR §464.2(a) — mandatory cleaning fee drip-priced after the advertised total",
        "A required cleaning charge added late in the booking funnel.",
        ("cleaning", "housekeeping", "turnover")),
    TaxonomyEntry("service_fee", True,
        "16 CFR §464.2(a) — mandatory service fee excluded from the advertised total price",
        "A blanket mandatory service charge not disclosed up front.",
        ("service", "service charge", "guest service")),
    TaxonomyEntry("admin_fee", True,
        "16 CFR §464.2(a) — undisclosed mandatory administrative fee",
        "Administrative/processing charge presented only at checkout.",
        ("admin", "administrative", "processing", "application")),
    TaxonomyEntry("booking_fee", True,
        "16 CFR §464.2(a) — mandatory booking fee not included in the total price",
        "A per-reservation fee added on top of the advertised rate.",
        ("booking", "reservation", "order")),
    TaxonomyEntry("convenience_fee", True,
        "16 CFR §464.2(b) — convenience fee misrepresenting an unavoidable mandatory charge",
        "A 'convenience' charge that is in fact unavoidable.",
        ("convenience", "online fee", "handling")),
    TaxonomyEntry("facility_fee", True,
        "16 CFR §464.2(a) — venue/facility fee omitted from the advertised total",
        "Mandatory facility or venue charge surfaced at checkout.",
        ("facility", "venue", "building")),
    TaxonomyEntry("amenity_fee", True,
        "16 CFR §464.2(a) — mandatory amenity fee not in the advertised price",
        "Charge for amenities the consumer cannot opt out of.",
        ("amenity", "club", "pool", "gym")),
    TaxonomyEntry("mandatory_gratuity", True,
        "16 CFR §464.2(b) — auto-gratuity misrepresented or not disclosed as mandatory",
        "An automatically applied, non-optional tip/gratuity.",
        ("gratuity", "auto tip", "mandatory tip", "service gratuity")),
    TaxonomyEntry("processing_fee", True,
        "16 CFR §464.2(a) — payment/processing fee excluded from the total price",
        "A processing charge added after the advertised price.",
        ("processing", "payment fee", "transaction")),
    TaxonomyEntry("parking_fee", False,
        "16 CFR §464.2(a) — if mandatory, must be in the total price; if optional, disclose before consent",
        "Parking charge — junk only if mandatory and undisclosed.",
        ("parking", "valet", "garage")),
    TaxonomyEntry("pet_fee", False,
        "16 CFR §464.3 — optional add-on; must be disclosed before the consumer consents to pay",
        "Optional pet charge; permissible if clearly disclosed.",
        ("pet", "animal", "dog", "cat")),
    TaxonomyEntry("delivery_fee", False,
        "16 CFR §464.3 — shipping/delivery may be excluded from total price but must be disclosed",
        "Delivery/shipping charge — excluded from total price if disclosed.",
        ("delivery", "shipping", "freight")),
    TaxonomyEntry("security_deposit", False,
        "Refundable deposit — generally not a fee under §464; must still be disclosed",
        "A refundable security deposit, not a junk fee.",
        ("deposit", "security", "refundable")),
    TaxonomyEntry("tax", False,
        "16 CFR §464.3 — government-imposed charges may be excluded from total price if disclosed",
        "Government tax — permissible if disclosed before consent.",
        ("tax", "sales tax", "occupancy tax", "vat", "government")),
    TaxonomyEntry("early_termination_fee", False,
        "16 CFR §464.2(b) — must not misrepresent its amount or conditions",
        "Penalty for ending a contract early; review for misrepresentation.",
        ("termination", "cancellation", "early exit", "break lease")),
]


def all_entries() -> list[TaxonomyEntry]:
    return list(FTC_TAXONOMY)
