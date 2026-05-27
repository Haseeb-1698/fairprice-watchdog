"""
ftc_taxonomy.py — FTC Junk Fee Rule taxonomy.

AUTO-GENERATED from FTC_Fee_Taxonomy.xlsx (Matas, domain owner) by
scripts/gen_taxonomy_from_xlsx.py. Do not edit by hand — edit the sheet and re-run.
Clauses + detectability are Matas's; sector / is_government / real-world labels are
derived on the agent side.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaxonomyEntry:
    fee_type: str
    ftc_clause: str
    clause_plain: str
    description: str
    keywords: tuple[str, ...]
    detectability: str  # agent-clean | partial | na
    sector: str
    is_junk: bool
    is_government: bool
    state_udap: str = ''
    agent_observation: str = ''
    notes: str = ''

    def text(self) -> str:
        return f'{self.fee_type}: {self.description} ({" ".join(self.keywords)})'


FTC_TAXONOMY: list[TaxonomyEntry] = [
    TaxonomyEntry(
        fee_type='resort',
        ftc_clause='§ 464.2(a); § 464.2(c)(1)',
        clause_plain='Cannot advertise any price without disclosing Total Price; must disclose excluded fees before payment.',
        description='A mandatory fee charged for general hotel amenities (pool, gym, wifi) not included in the advertised room rate. Classic drip-pricing pattern.',
        keywords=('resort fee', 'destination fee', 'amenity fee', 'property fee', 'urban fee', 'facility charge', 'urban destination charge'),
        detectability='agent-clean',
        sector='lodging',
        is_junk=True,
        is_government=False,
        state_udap='',
        agent_observation='Mandatory line item in final checkout total absent from advertised room rate. Delta between advertised and final price.',
        notes='Most common junk fee in hotel sector. High-confidence detection. Strong demo candidate.',
    ),
    TaxonomyEntry(
        fee_type='cleaning',
        ftc_clause='§ 464.2(a); § 464.2(c)(1)',
        clause_plain='Cannot advertise any price without disclosing Total Price; must disclose excluded fees before payment.',
        description='A mandatory cleaning charge added at checkout on short-term rental platforms (Airbnb, Vrbo). Often exceeds nightly rate on short stays.',
        keywords=('cleaning fee', 'clean fee', 'housekeeping fee', 'sanitation fee', 'end-of-stay cleaning'),
        detectability='agent-clean',
        sector='lodging',
        is_junk=True,
        is_government=False,
        state_udap='',
        agent_observation='Named line item in final checkout not included in advertised nightly/total price shown on listing page.',
        notes='Very common on Vrbo, Airbnb. Strong demo candidate for short-term lodging track.',
    ),
    TaxonomyEntry(
        fee_type='service',
        ftc_clause='§ 464.2(a); § 464.3',
        clause_plain='Cannot advertise any price without disclosing Total Price; cannot misrepresent the nature or purpose of a fee.',
        description="A broad mandatory fee labelled 'service' with vague purpose. May violate both hidden-fee and misrepresentation rules if purpose is unclear.",
        keywords=('service fee', 'service charge', 'platform fee', 'guest service fee', 'host service fee'),
        detectability='partial',
        sector='lodging,ticketing',
        is_junk=True,
        is_government=False,
        state_udap='',
        agent_observation='Agent detects fee name and amount cleanly (§464.2a). Purpose-misrepresentation element (§464.3) requires human judgment.',
        notes='Split detectability. Agent handles the disclosure violation; human handles the misrepresentation angle.',
    ),
    TaxonomyEntry(
        fee_type='admin',
        ftc_clause='§ 464.2(a); § 464.3',
        clause_plain='Cannot advertise any price without disclosing Total Price; cannot misrepresent the nature or purpose of a fee.',
        description="A mandatory administrative charge with no clear consumer benefit. 'Admin fee' is a common obfuscation label for revenue padding.",
        keywords=('admin fee', 'administration fee', 'administrative charge', 'management fee', 'processing and admin', 'smart home technology', 'utility management'),
        detectability='partial',
        sector='rental',
        is_junk=True,
        is_government=False,
        state_udap='Rental-sector fee: enforce via FTC Act §5 + state UDAP statutes (federal Junk Fees Rule covers lodging+ticketing today; rental rule in FTC rulemaking since Dec 2025).',
        agent_observation="Agent detects presence and amount cleanly. Whether 'admin' label misrepresents the fee's true nature requires human judgment.",
        notes='High misrepresentation risk given vague label. Human review recommended for §464.3 element.',
    ),
    TaxonomyEntry(
        fee_type='booking',
        ftc_clause='§ 464.2(a); § 464.2(c)(1)',
        clause_plain='Cannot advertise any price without disclosing Total Price; must disclose excluded fees before payment.',
        description='A mandatory fee charged for the act of booking, separate from the room/ticket price. Consumer cannot avoid it.',
        keywords=('booking fee', 'reservation fee', 'booking charge', 'reservation charge', 'order fee'),
        detectability='agent-clean',
        sector='lodging,ticketing',
        is_junk=True,
        is_government=False,
        state_udap='',
        agent_observation='Mandatory line item appearing in final total absent from advertised price. Unavoidable = mandatory under §464.1 Total Price definition.',
        notes='Clean detection. Confirm it is non-optional to establish mandatory status.',
    ),
    TaxonomyEntry(
        fee_type='convenience',
        ftc_clause='§ 464.2(a); § 464.3',
        clause_plain='Cannot advertise any price without disclosing Total Price; cannot misrepresent the nature or purpose of a fee.',
        description="A fee labelled as compensation for 'convenience' — typically mandatory and of no clear benefit to the consumer. Common in ticketing.",
        keywords=('convenience fee', 'order processing fee', 'fulfillment fee', 'ticket convenience charge'),
        detectability='partial',
        sector='ticketing',
        is_junk=True,
        is_government=False,
        state_udap='',
        agent_observation="Agent detects fee name and amount. 'Convenience' framing may misrepresent purpose — that element needs human judgment.",
        notes='High relevance for ticketing sector. StubHub DC lawsuit (2024) cited this fee type directly. Strong legal precedent.',
    ),
    TaxonomyEntry(
        fee_type='facility',
        ftc_clause='§ 464.2(a); § 464.2(c)(1)',
        clause_plain='Cannot advertise any price without disclosing Total Price; must disclose excluded fees before payment.',
        description='A mandatory charge for use of the venue or property facilities. Effectively a resort fee under a different name.',
        keywords=('facility fee', 'venue fee', 'facility charge', 'building fee', 'infrastructure fee'),
        detectability='agent-clean',
        sector='lodging',
        is_junk=True,
        is_government=False,
        state_udap='',
        agent_observation='Mandatory line item in final total absent from initial advertised price. Same detection pattern as resort fee.',
        notes='Functionally equivalent to resort fee. Often used as an alternative label.',
    ),
    TaxonomyEntry(
        fee_type='amenity',
        ftc_clause='§ 464.2(a); § 464.2(c)(1)',
        clause_plain='Cannot advertise any price without disclosing Total Price; must disclose excluded fees before payment.',
        description='A mandatory charge for hotel or rental amenities (gym, pool, wifi, parking) bundled and hidden from the advertised rate.',
        keywords=('amenity fee', 'amenities fee', 'amenity charge', 'amenities surcharge', 'resort amenities'),
        detectability='agent-clean',
        sector='lodging',
        is_junk=True,
        is_government=False,
        state_udap='',
        agent_observation='Mandatory line item in final checkout total not present in advertised price. High overlap with resort and facility fee types.',
        notes='Often appears alongside resort fee. Watch for double-charging of same service under two labels.',
    ),
    TaxonomyEntry(
        fee_type='mandatory_gratuity',
        ftc_clause='§ 464.2(a); § 464.3',
        clause_plain='Cannot advertise any price without disclosing Total Price; cannot misrepresent the nature or purpose of a fee.',
        description='A compulsory gratuity that consumers cannot opt out of. Violates §464.2(a) if hidden; may violate §464.3 if labelled as voluntary.',
        keywords=('mandatory gratuity', 'automatic gratuity', 'service charge', 'mandatory tip', 'auto-gratuity', 'staff gratuity'),
        detectability='partial',
        sector='lodging',
        is_junk=True,
        is_government=False,
        state_udap='',
        agent_observation='Agent detects fee name and amount. Whether gratuity is truly mandatory vs. optional requires page interaction check (Tier 3).',
        notes='IMPORTANT: A gratuity is only in Total Price if mandatory. Mandatory status is the key variable — requires human verification.',
    ),
    TaxonomyEntry(
        fee_type='processing',
        ftc_clause='§ 464.2(a); § 464.2(c)(1)',
        clause_plain='Cannot advertise any price without disclosing Total Price; must disclose excluded fees before payment.',
        description='A mandatory payment processing fee added at checkout. Distinct from optional credit card surcharges which may be legally excluded.',
        keywords=('processing fee', 'order processing', 'payment processing fee', 'transaction fee', 'order fee', 'checkout fee'),
        detectability='partial',
        sector='ticketing,lodging',
        is_junk=True,
        is_government=False,
        state_udap='',
        agent_observation='Agent detects fee name and amount cleanly. Key judgment: mandatory processing fee (covered) vs. optional card surcharge (may be excluded per §464.1).',
        notes='IMPORTANT: Optional credit card surcharges MAY be excluded from Total Price. Agent must distinguish mandatory processing from optional card surcharge.',
    ),
    TaxonomyEntry(
        fee_type='parking',
        ftc_clause='§ 464.2(a); § 464.2(c)(1)',
        clause_plain='Cannot advertise any price without disclosing Total Price; must disclose excluded fees before payment.',
        description='A mandatory parking charge bundled into a hotel stay without disclosure in the advertised rate.',
        keywords=('parking fee', 'valet fee', 'valet parking', 'parking charge', 'self-parking fee', 'parking surcharge'),
        detectability='partial',
        sector='rental,lodging',
        is_junk=True,
        is_government=False,
        state_udap='Rental-sector fee: enforce via FTC Act §5 + state UDAP statutes (federal Junk Fees Rule covers lodging+ticketing today; rental rule in FTC rulemaking since Dec 2025).',
        agent_observation='Agent detects fee name and amount. Mandatory vs. optional is key — if consumer can decline parking, it is an optional ancillary excluded from Total Price.',
        notes='Only a violation if parking is mandatory/unavoidable. Flag for human review on mandatory status.',
    ),
    TaxonomyEntry(
        fee_type='pet',
        ftc_clause='§ 464.2(a); § 464.2(c)(1)',
        clause_plain='Cannot advertise any price without disclosing Total Price; must disclose excluded fees before payment.',
        description='A mandatory pet fee charged to guests travelling with pets, not disclosed in the advertised rate.',
        keywords=('pet fee', 'pet charge', 'pet deposit', 'animal fee', 'pet cleaning fee', 'pet surcharge'),
        detectability='partial',
        sector='rental',
        is_junk=True,
        is_government=False,
        state_udap='Rental-sector fee: enforce via FTC Act §5 + state UDAP statutes (federal Junk Fees Rule covers lodging+ticketing today; rental rule in FTC rulemaking since Dec 2025).',
        agent_observation='Agent detects fee name and amount. Mandatory status depends on whether consumer selected travelling with pet — a contingent fee.',
        notes='Contingent fee (only applies if consumer has a pet). The rule addresses contingent fees — if applicable, must be in Total Price. Lower detection reliability.',
    ),
    TaxonomyEntry(
        fee_type='delivery',
        ftc_clause='§ 464.2(a); § 464.2(c)(1)',
        clause_plain='Cannot advertise any price without disclosing Total Price; must disclose excluded fees before payment.',
        description='A mandatory ticket delivery fee that is unavoidable and hidden from the advertised ticket price. Ticketing sector specific.',
        keywords=('delivery fee', 'e-ticket fee', 'will call fee', 'print at home fee', 'mobile delivery fee', 'ticket delivery'),
        detectability='partial',
        sector='rental',
        is_junk=True,
        is_government=False,
        state_udap='Rental-sector fee: enforce via FTC Act §5 + state UDAP statutes (federal Junk Fees Rule covers lodging+ticketing today; rental rule in FTC rulemaking since Dec 2025).',
        agent_observation='Agent detects fee name and amount. Mandatory vs. optional depends on whether consumer can choose a no-fee delivery method.',
        notes='Key question: does the platform offer any free delivery option? If yes, fee is avoidable and excluded from Total Price.',
    ),
    TaxonomyEntry(
        fee_type='security_deposit',
        ftc_clause='§ 464.2(c)(1) — disclosure only; likely outside §464.2(a) scope',
        clause_plain='Must disclose fees excluded from Total Price before consumer consents to pay.',
        description='A refundable security deposit required before check-in. Not a junk fee per se — but must be disclosed clearly before payment consent.',
        keywords=('security deposit', 'damage deposit', 'refundable deposit', 'damage waiver', 'security hold'),
        detectability='partial',
        sector='rental',
        is_junk=True,
        is_government=False,
        state_udap='Rental-sector fee: enforce via FTC Act §5 + state UDAP statutes (federal Junk Fees Rule covers lodging+ticketing today; rental rule in FTC rulemaking since Dec 2025).',
        agent_observation='Agent detects presence and amount. Refundable deposits are arguably outside Total Price definition (not a fee consumer ultimately pays).',
        notes='EDGE CASE: Security deposits are refundable — likely not part of Total Price under §464.1. Violation is failure to disclose before payment, not omission from advertised price. Lower priority.',
    ),
    TaxonomyEntry(
        fee_type='tax',
        ftc_clause='OUTSIDE RULE SCOPE — Government Charges exemption §464.1',
        clause_plain="Government charges are explicitly excluded from Total Price under the rule's definitions.",
        description='Federal, state, tribal, or local taxes imposed on the transaction. Explicitly exempt from Total Price requirement under §464.1.',
        keywords=('tax', 'occupancy tax', 'city tax', 'state tax', 'local tax', 'tourism tax', 'VAT', 'sales tax', 'lodging tax'),
        detectability='na',
        sector='all',
        is_junk=False,
        is_government=True,
        state_udap='',
        agent_observation='Agent should detect and label tax line items but NOT flag as violations. Government charges are legally excludable from Total Price.',
        notes='IMPORTANT: Tax is EXEMPT. Do not flag as violation. Agent should strip tax from price comparison to avoid false positives.',
    ),
    TaxonomyEntry(
        fee_type='early_termination',
        ftc_clause='§ 464.3; § 464.2(c)(1)',
        clause_plain='Cannot misrepresent any fee including its refundability; must disclose fees excluded from Total Price before consumer consents to pay.',
        description='A penalty fee charged if consumer cancels or terminates early. Must be clearly disclosed before payment; misrepresenting conditions violates §464.3.',
        keywords=('early termination fee', 'cancellation fee', 'cancellation penalty', 'early checkout fee', 'no-show fee', 'cancellation charge'),
        detectability='partial',
        sector='rental',
        is_junk=True,
        is_government=False,
        state_udap='Rental-sector fee: enforce via FTC Act §5 + state UDAP statutes (federal Junk Fees Rule covers lodging+ticketing today; rental rule in FTC rulemaking since Dec 2025).',
        agent_observation='Agent can detect presence and amount if shown during checkout. Conditions may only appear in fine print — requires full page text extraction.',
        notes='Refundability is explicitly covered by §464.3. Agent should flag if cancellation terms are buried or contradicted elsewhere on the page.',
    ),
]


def all_entries() -> list[TaxonomyEntry]:
    return list(FTC_TAXONOMY)
