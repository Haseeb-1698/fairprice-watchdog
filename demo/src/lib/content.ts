// Sourced regulatory content for the demo's "Why now" + personas + references.
// Every figure traces to a primary source in CITATIONS.

export const STATS = [
  { value: "$51,744", label: "Max civil penalty / violation", sub: "FTC, inflation-adjusted" },
  { value: "May 12 2025", label: "Junk Fees Rule in effect", sub: "16 CFR Part 464" },
  { value: "$71M+", label: "Recovered in 14 months", sub: "Greystar + Invitation Homes" },
  { value: "50 states", label: "Federal coverage", sub: "+ UK DMCCA, EU DFA incoming" },
];

export interface CaseItem {
  org: string;
  amount: string;
  date: string;
  authority: string;
  detail: string;
  href: string;
}

export const CASES: CaseItem[] = [
  {
    org: "Greystar",
    amount: "$23M + $1M",
    date: "Dec 2, 2025",
    authority: "FTC Act §5 + Colorado CPA",
    detail: "Nation's largest multi-family manager — misled renters by tacking hidden fees onto advertised rent. Same day, the FTC began rulemaking for a dedicated rental-housing fee rule.",
    href: "https://www.ftc.gov/news-events/news/press-releases/2025/12/greystar-agrees-pay-24-million-stop-deceptive-advertising-practices-result-ftc-colorado-lawsuit",
  },
  {
    org: "Invitation Homes",
    amount: "$48M",
    date: "Sep 27, 2024",
    authority: "FTC Act §5",
    detail: "Largest single-family landlord — undisclosed 'smart home technology' and 'utility management' fees renters couldn't opt out of. Refund checks mailed March 2026.",
    href: "https://www.ftc.gov/news-events/news/press-releases/2024/09/ftc-takes-action-against-invitation-homes-deceiving-renters-charging-junk-fees-withholding-security",
  },
  {
    org: "DOJ v. RealPage",
    amount: "Antitrust",
    date: "Filed Aug 2024",
    authority: "DOJ — algorithmic price-fixing",
    detail: "Separate legal theory (algorithmic rent collusion, not junk fees) — but the same regulatory wave driving demand for automated pricing evidence.",
    href: "https://www.justice.gov/opa/pr/justice-department-sues-realpage-algorithmic-pricing-scheme-harms-millions-american-renters",
  },
];

export interface Persona {
  title: string;
  who: string;
  need: string;
  value: string;
  price: string;
}

export const PERSONAS: Persona[] = [
  {
    title: "Consumer",
    who: "Anyone about to book",
    need: "Know the real total before paying",
    value: "Instant fee breakdown + plain-English junk-fee warning",
    price: "Freemium · $9/mo",
  },
  {
    title: "Regulator / State AG",
    who: "CO, NY, CA, MA, IL AGs…",
    need: "Scalable evidence across operators & ZIPs",
    value: "Heatmap of violations, exportable structured reports",
    price: "$50K–$100K / yr per office",
  },
  {
    title: "Class-Action Counsel",
    who: "Hagens Berman, Lieff Cabraser…",
    need: "Timestamped, hashed evidence packets",
    value: "Court-ready PDF exhibits + SHA-256 chain of custody",
    price: "Revenue-share on settlement",
  },
];

export interface Citation { claim: string; href: string }

export const CITATIONS: Citation[] = [
  { claim: "FTC Junk Fees Rule — announcement", href: "https://www.ftc.gov/news-events/news/press-releases/2024/12/federal-trade-commission-announces-bipartisan-rule-banning-junk-ticket-hotel-fees" },
  { claim: "16 CFR Part 464 — Federal Register text", href: "https://www.federalregister.gov/documents/2025/01/10/2024-30293/trade-regulation-rule-on-unfair-or-deceptive-fees" },
  { claim: "Greystar $23M settlement (FTC)", href: "https://www.ftc.gov/news-events/news/press-releases/2025/12/greystar-agrees-pay-24-million-stop-deceptive-advertising-practices-result-ftc-colorado-lawsuit" },
  { claim: "Invitation Homes $48M (FTC)", href: "https://www.ftc.gov/news-events/news/press-releases/2024/09/ftc-takes-action-against-invitation-homes-deceiving-renters-charging-junk-fees-withholding-security" },
  { claim: "Colorado AG — Greystar", href: "https://coag.gov/press-releases/weiser-ftc-announce-24m-settlement-with-greystar/" },
  { claim: "EU Unfair Commercial Practices Directive", href: "https://commission.europa.eu/law/law-topic/consumer-protection-law/unfair-commercial-practices-and-price-indication/unfair-commercial-practices-directive_en" },
];

// Honesty note kept visible so the pitch is defensible in Q&A.
export const SCOPE_NOTE =
  "Scope, stated honestly: the Junk Fees Rule (16 CFR Part 464) covers short-term lodging and live-event ticketing across all 50 states. Rental housing is enforced via FTC Act §5 + state UDAP law today — with a dedicated rental-fee rule in active FTC rulemaking since Dec 2025. The detection pattern (advertised price ≠ checkout total) is identical across all of them.";
