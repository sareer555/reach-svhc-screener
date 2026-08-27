"""
EU REACH SVHC Candidate List & Article Communication Screener -- core logic.

Screens substance/ingredient names against a curated subset of ECHA's REACH
Candidate List of Substances of Very High Concern (SVHC), and calculates
which Article 33 (duty to communicate), Article 7(2) (notification to ECHA),
and SCIP database duties are triggered for a given concentration -- based on
the 0.1% weight-by-weight (w/w) threshold that runs through all three.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from typing import Literal, Optional

# ---------------------------------------------------------------------------
# Hazard reasons (REACH Article 57 grounds for SVHC identification)
# ---------------------------------------------------------------------------

HazardReason = Literal[
    "carcinogenic",
    "mutagenic",
    "reproductive_toxicant",
    "pbt",
    "vpvb",
    "endocrine_disrupting",
    "equivalent_concern",
]

HAZARD_LABELS: dict[str, str] = {
    "carcinogenic": "Carcinogenic (Art. 57a)",
    "mutagenic": "Mutagenic (Art. 57b)",
    "reproductive_toxicant": "Toxic for reproduction (Art. 57c)",
    "pbt": "PBT -- persistent, bioaccumulative, toxic (Art. 57d)",
    "vpvb": "vPvB -- very persistent, very bioaccumulative (Art. 57e)",
    "endocrine_disrupting": "Endocrine-disrupting properties, equivalent level of concern (Art. 57f)",
    "equivalent_concern": "Equivalent level of concern to other SVHC criteria (Art. 57f)",
}


# ---------------------------------------------------------------------------
# Curated substance table
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Substance:
    name: str
    aliases: tuple[str, ...]
    category: str
    hazard_reasons: tuple[HazardReason, ...]
    common_uses: str
    note: str = ""


SUBSTANCE_TABLE: tuple[Substance, ...] = (
    # Bisphenols
    Substance("Bisphenol A (BPA)", ("bpa",), "Bisphenols",
              ("reproductive_toxicant", "endocrine_disrupting"),
              "Polycarbonate plastics, epoxy resin can linings, thermal paper"),
    Substance("Bisphenol AF (BPAF)", ("bpaf",), "Bisphenols",
              ("reproductive_toxicant",),
              "Process regulator and cross-linking agent in fluoropolymer production",
              "Added to the Candidate List February 4, 2026."),

    # Solvents
    Substance("N-hexane", ("hexane", "n-hexane"), "Solvents",
              ("equivalent_concern",),
              "Cleaning agents, coatings formulation, polymer processing",
              "Added to the Candidate List February 4, 2026 (STOT-repeated exposure)."),
    Substance("1-Methyl-2-pyrrolidone (NMP)", ("nmp", "n-methylpyrrolidone"), "Solvents",
              ("reproductive_toxicant",),
              "Paint strippers, electronics manufacturing, degreasers"),
    Substance("2-Methoxyethanol", ("methyl cellosolve",), "Solvents",
              ("reproductive_toxicant",),
              "Solvent for resins, dyes, and inks"),

    # Phthalates
    Substance("Di(2-ethylhexyl) phthalate (DEHP)", ("dehp",), "Phthalates",
              ("reproductive_toxicant", "endocrine_disrupting"),
              "PVC plasticizer in cables, flooring, medical tubing"),
    Substance("Dibutyl phthalate (DBP)", ("dbp",), "Phthalates",
              ("reproductive_toxicant",),
              "Plasticizer in coatings, adhesives, printing inks"),
    Substance("Benzyl butyl phthalate (BBP)", ("bbp",), "Phthalates",
              ("reproductive_toxicant",),
              "PVC flooring, foamed plastics, sealants"),
    Substance("Diisobutyl phthalate (DIBP)", ("dibp",), "Phthalates",
              ("reproductive_toxicant",),
              "Plasticizer, substitute for DBP in some formulations"),
    Substance("Di-n-hexyl phthalate (DnHP)", ("dnhp",), "Phthalates",
              ("reproductive_toxicant",),
              "Plasticizer in PVC and rubber products"),
    Substance("Diisohexyl phthalate", ("dihxp",), "Phthalates",
              ("reproductive_toxicant",),
              "Plasticizer, structurally related to DEHP/DnHP"),

    # PFAS
    Substance("Perfluorooctanoic acid (PFOA), its salts and PFOA-related substances",
              ("pfoa",), "PFAS",
              ("pbt", "vpvb", "reproductive_toxicant"),
              "Historic use in non-stick coatings, textile treatments, firefighting foam",
              "Also restricted under Annex XVII and the POPs Regulation, not just Candidate-List-listed."),
    Substance("Perfluorooctane sulfonic acid (PFOS) and its derivatives",
              ("pfos",), "PFAS",
              ("pbt", "vpvb"),
              "Historic use in firefighting foam, textile and leather treatments",
              "Also restricted under the POPs Regulation."),
    Substance("Perfluorohexane-1-sulfonic acid (PFHxS), its salts and related substances",
              ("pfhxs",), "PFAS",
              ("pbt", "vpvb"),
              "Surfactants, historic firefighting foam and textile treatment use"),
    Substance("Perfluorononan-1-oic acid (PFNA) and its salts",
              ("pfna",), "PFAS",
              ("pbt", "vpvb"),
              "Surfactant and processing aid in fluoropolymer manufacture"),
    Substance("HFPO-DA and its ammonium salt (GenX chemicals)",
              ("genx", "hfpo-da"), "PFAS",
              ("equivalent_concern",),
              "PFOA replacement processing aid in fluoropolymer manufacture"),

    # Flame retardants
    Substance("Tris(2-chloroethyl) phosphate (TCEP)", ("tcep",), "Flame retardants",
              ("reproductive_toxicant", "carcinogenic"),
              "Flexible polyurethane foam, textile coatings"),
    Substance("Tris(2-chloro-1-methylethyl) phosphate (TCPP)", ("tcpp",), "Flame retardants",
              ("reproductive_toxicant",),
              "Flexible and rigid polyurethane foam"),
    Substance("Decabromodiphenyl ether (DecaBDE)", ("decabde",), "Flame retardants",
              ("pbt", "vpvb"),
              "Historic flame retardant in plastics and textiles",
              "Also restricted under Annex XVII and the POPs Regulation."),
    Substance("Hexabromocyclododecane (HBCDD)", ("hbcdd",), "Flame retardants",
              ("pbt",),
              "Historic flame retardant in expanded/extruded polystyrene insulation",
              "Also on the Authorisation List (Annex XIV) and POPs-restricted."),

    # Heavy metal / lead compounds
    Substance("Lead chromate", ("",), "Heavy metals",
              ("carcinogenic", "reproductive_toxicant"),
              "Pigments (chrome yellow) in paints and coatings"),
    Substance("Lead monoxide (litharge)", ("",), "Heavy metals",
              ("reproductive_toxicant",),
              "Glass, ceramics, batteries, PVC stabilizers"),
    Substance("Lead titanium trioxide", ("",), "Heavy metals",
              ("reproductive_toxicant",),
              "Pigments in ceramics and coatings"),
    Substance("Trilead diarsenate", ("",), "Heavy metals",
              ("carcinogenic",),
              "Historic pesticide and glass/ceramic use"),
    Substance("Cobalt dichloride", ("",), "Heavy metals",
              ("carcinogenic",),
              "Electroplating, pigments, catalysts, battery components"),
    Substance("Cobalt sulphate", ("",), "Heavy metals",
              ("carcinogenic",),
              "Electroplating, pigments, battery cathode materials"),

    # Boron compounds
    Substance("Boric acid", ("",), "Boron compounds",
              ("reproductive_toxicant",),
              "Glass/fiberglass manufacture, flame retardants, wood preservatives"),
    Substance("Disodium tetraborate, anhydrous (borax)", ("borax",), "Boron compounds",
              ("reproductive_toxicant",),
              "Detergents, glass and ceramic glazes, flame retardants"),

    # Siloxanes
    Substance("Octamethylcyclotetrasiloxane (D4)", ("d4",), "Siloxanes",
              ("pbt", "vpvb"),
              "Personal care products, silicone polymer production"),
    Substance("Decamethylcyclopentasiloxane (D5)", ("d5",), "Siloxanes",
              ("vpvb",),
              "Personal care products, silicone polymer production"),
    Substance("Dodecamethylcyclohexasiloxane (D6)", ("d6",), "Siloxanes",
              ("vpvb",),
              "Personal care products, silicone polymer production"),

    # Musks / UV filters / other persistent substances
    Substance("Musk xylene", ("",), "Fragrance ingredients",
              ("pbt", "vpvb"),
              "Historic fragrance fixative in cosmetics and detergents"),
    Substance("2-Benzotriazol-2-yl-4,6-di-tert-pentylphenol (UV-328)", ("uv-328",), "UV filters",
              ("pbt", "vpvb"),
              "UV stabilizer in plastics, coatings, and rubber"),

    # Alkylphenols
    Substance("4-Nonylphenol, branched and linear, ethoxylated", ("nonylphenol ethoxylate", "npe"),
              "Alkylphenols",
              ("endocrine_disrupting",),
              "Historic surfactant in detergents, textile and leather processing"),
    Substance("4-tert-Octylphenol", ("octylphenol",), "Alkylphenols",
              ("endocrine_disrupting",),
              "Surfactant manufacture, resins, rubber processing"),

    # Others
    Substance("Formaldehyde", ("",), "Other",
              ("carcinogenic",),
              "Resins (urea/phenol-formaldehyde), textile finishing, disinfectants"),
    Substance("Medium-chain chlorinated paraffins (MCCP)", ("mccp",), "Other",
              ("pbt", "vpvb", "equivalent_concern"),
              "Metalworking fluids, PVC plasticizers/flame retardants, sealants"),
    Substance("Disperse Blue 1", ("",), "Dyes",
              ("carcinogenic",),
              "Historic disperse dye for synthetic textile fibers"),
)

_ALIAS_INDEX: dict[str, Substance] = {}
for _s in SUBSTANCE_TABLE:
    _ALIAS_INDEX[_s.name.lower()] = _s
    for _a in _s.aliases:
        if _a:
            _ALIAS_INDEX[_a.lower()] = _s


def lookup_substance(name: str) -> Optional[Substance]:
    """Look up a substance by exact name, alias, or loose substring match."""
    if not name or not name.strip():
        return None
    key = name.strip().lower()
    if key in _ALIAS_INDEX:
        return _ALIAS_INDEX[key]
    for indexed_key, substance in _ALIAS_INDEX.items():
        if indexed_key and (indexed_key in key or key in indexed_key):
            return substance
    return None


@dataclass(frozen=True)
class LookupResult:
    query: str
    substance: Optional[Substance]

    @property
    def is_listed(self) -> bool:
        return self.substance is not None


def screen_substances(names: list[str]) -> list[LookupResult]:
    return [LookupResult(query=n, substance=lookup_substance(n)) for n in names]


# ---------------------------------------------------------------------------
# Article 33 / Article 7(2) / SCIP duty calculator
# ---------------------------------------------------------------------------

SVHC_THRESHOLD_PCT = 0.1  # % w/w -- duties trigger above (not at) this value


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


@dataclass(frozen=True)
class DutyAssessment:
    concentration_pct: float
    threshold_exceeded: bool
    article_33_duty: bool
    article_33_note: str
    scip_duty: bool
    scip_deadline: Optional[date]
    scip_note: str
    article_7_2_duty: Optional[bool]
    article_7_2_deadline: Optional[date]
    article_7_2_note: str


def assess_duties(
    concentration_pct: float,
    placed_on_eu_market: bool = True,
    candidate_list_inclusion_date: Optional[date] = None,
    quantity_tonnes_per_year: Optional[float] = None,
) -> DutyAssessment:
    """Assess which REACH Candidate List duties are triggered.

    concentration_pct: the substance's concentration in the article, as a
        percentage (e.g. 0.5 for 0.5%), evaluated per REACH guidance at the
        level of each "article" within a complex product -- not the whole
        product's average composition.
    """
    threshold_exceeded = concentration_pct > SVHC_THRESHOLD_PCT

    if not threshold_exceeded or not placed_on_eu_market:
        note_suffix = (
            "not placed on the EU/EEA market" if threshold_exceeded else
            f"concentration is at or below the {SVHC_THRESHOLD_PCT}% w/w threshold"
        )
        return DutyAssessment(
            concentration_pct=concentration_pct,
            threshold_exceeded=threshold_exceeded,
            article_33_duty=False,
            article_33_note=f"Not triggered -- {note_suffix}.",
            scip_duty=False,
            scip_deadline=None,
            scip_note=f"Not triggered -- {note_suffix}.",
            article_7_2_duty=False if threshold_exceeded else None,
            article_7_2_deadline=None,
            article_7_2_note=f"Not triggered -- {note_suffix}.",
        )

    # Article 33: proactive communication + 45-day duty on consumer request.
    article_33_note = (
        "Triggered: provide sufficient safe-use information proactively to "
        "professional customers, and to any consumer who asks, within 45 "
        "days of the request (Art. 33(1) and 33(2))."
    )

    # SCIP: same 0.1% w/w threshold, deadline is 6 months after the
    # substance's Candidate List inclusion date (or immediately if it was
    # already on the list before the article was placed on the market).
    scip_deadline = _add_months(candidate_list_inclusion_date, 6) if candidate_list_inclusion_date else None
    if scip_deadline:
        scip_note = (
            f"Triggered: submit a SCIP notification to ECHA no later than "
            f"{scip_deadline.strftime('%B %-d, %Y')} (6 months after the "
            f"substance's Candidate List inclusion date you provided)."
        )
    else:
        scip_note = (
            "Triggered, but the deadline depends on the substance's exact "
            "Candidate List inclusion date -- provide that date to calculate "
            "it, or check echa.europa.eu/candidate-list-table."
        )

    # Article 7(2): only assessable if quantity is known; also depends on the
    # >1 tonne/year threshold, with statutory exemptions this tool cannot
    # verify (exposure can be excluded, or already registered for that use).
    if quantity_tonnes_per_year is None:
        article_7_2_duty: Optional[bool] = None
        article_7_2_note = (
            "Cannot assess -- Art. 7(2) notification to ECHA also depends on "
            "whether the substance exceeds 1 tonne/year across all your "
            "articles. Provide an annual quantity to assess this duty."
        )
        article_7_2_deadline = None
    else:
        article_7_2_duty = quantity_tonnes_per_year > 1.0
        if article_7_2_duty:
            article_7_2_deadline = (
                _add_months(candidate_list_inclusion_date, 6)
                if candidate_list_inclusion_date else None
            )
            if article_7_2_deadline:
                article_7_2_note = (
                    f"Triggered: notify ECHA under Art. 7(2) no later than "
                    f"{article_7_2_deadline.strftime('%B %-d, %Y')} (6 months "
                    f"after Candidate List inclusion), UNLESS you can exclude "
                    f"exposure during use and disposal, or the use is already "
                    f"covered by a REACH registration."
                )
            else:
                article_7_2_note = (
                    "Triggered (subject to the exposure-exclusion and "
                    "already-registered exemptions) -- provide the "
                    "substance's Candidate List inclusion date to calculate "
                    "the 6-month deadline."
                )
        else:
            article_7_2_deadline = None
            article_7_2_note = (
                "Not triggered -- total quantity is at or below 1 tonne/year "
                "across your articles containing this substance."
            )

    return DutyAssessment(
        concentration_pct=concentration_pct,
        threshold_exceeded=True,
        article_33_duty=True,
        article_33_note=article_33_note,
        scip_duty=True,
        scip_deadline=scip_deadline,
        scip_note=scip_note,
        article_7_2_duty=article_7_2_duty,
        article_7_2_deadline=article_7_2_deadline,
        article_7_2_note=article_7_2_note,
    )


# ---------------------------------------------------------------------------
# Candidate List update history (verified milestones only)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ListMilestone:
    label: str
    total_substances: int
    note: str


CANDIDATE_LIST_MILESTONES: tuple[ListMilestone, ...] = (
    ListMilestone("October 28, 2008", 15, "First Candidate List published."),
    ListMilestone("January 2023", 233, "Routine biannual update."),
    ListMilestone("June 2025", 250, "Routine biannual update."),
    ListMilestone("February 4, 2026", 253, "Added n-hexane and Bisphenol AF (BPAF), the two most recent entries."),
)
