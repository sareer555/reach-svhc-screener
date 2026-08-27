"""
Unit tests for the REACH SVHC Candidate List & Article Communication Screener.

Run with:  python3 test_reach_svhc_screener.py
"""

from datetime import date

from reach_svhc_screener import (
    CANDIDATE_LIST_MILESTONES,
    assess_duties,
    lookup_substance,
    screen_substances,
)


def run():
    failures = []

    def check(name, condition):
        status = "PASS" if condition else "FAIL"
        if status == "FAIL":
            failures.append(name)
        print(f"[{status}] {name}")

    # --- exact / alias lookup ---
    s = lookup_substance("Bisphenol A (BPA)")
    check("BPA exact name found", s is not None)

    s = lookup_substance("bpa")
    check("BPA alias (lowercase) found", s is not None and s.name == "Bisphenol A (BPA)")

    s = lookup_substance("PFOA")
    check("PFOA alias found", s is not None and s.category == "PFAS")

    s = lookup_substance("n-hexane")
    check("n-hexane found", s is not None and "equivalent_concern" in s.hazard_reasons)

    # --- loose substring match ---
    s = lookup_substance("borax detergent additive")
    check("Loose match finds borax", s is not None and "borax" in s.name.lower())

    # --- unlisted substance ---
    s = lookup_substance("Sodium chloride")
    check("Sodium chloride not listed -> None", s is None)

    check("Empty string -> None", lookup_substance("") is None)

    # --- batch screening ---
    results = screen_substances(["BPA", "Sodium chloride", "PFOS", "DEHP"])
    check("Batch -> 4 results", len(results) == 4)
    check("Batch -> BPA listed", results[0].is_listed is True)
    check("Batch -> Sodium chloride not listed", results[1].is_listed is False)
    check("Batch -> PFOS listed", results[2].is_listed is True)
    check("Batch -> DEHP listed", results[3].is_listed is True)

    # --- duty calculator: below threshold ---
    d = assess_duties(0.05)
    check("Below threshold: no Art 33 duty", d.article_33_duty is False)
    check("Below threshold: no SCIP duty", d.scip_duty is False)
    check("Below threshold: threshold_exceeded False", d.threshold_exceeded is False)

    # --- duty calculator: exactly at threshold (not exceeded, must be >) ---
    d = assess_duties(0.1)
    check("Exactly 0.1% does not exceed threshold", d.threshold_exceeded is False)

    # --- duty calculator: above threshold, no dates/quantity provided ---
    d = assess_duties(0.5)
    check("Above threshold: Art 33 triggered", d.article_33_duty is True)
    check("Above threshold: SCIP triggered", d.scip_duty is True)
    check("Above threshold, no date: SCIP deadline is None", d.scip_deadline is None)
    check("Above threshold, no quantity: Art 7(2) duty is None (unknown)", d.article_7_2_duty is None)

    # --- duty calculator: above threshold, with inclusion date ---
    d = assess_duties(0.5, candidate_list_inclusion_date=date(2026, 2, 4))
    check("SCIP deadline = inclusion date + 6 months", d.scip_deadline == date(2026, 8, 4))

    # --- duty calculator: quantity above 1 tonne/year ---
    d = assess_duties(0.5, candidate_list_inclusion_date=date(2026, 2, 4), quantity_tonnes_per_year=5.0)
    check("Art 7(2) triggered above 1 tonne/year", d.article_7_2_duty is True)
    check("Art 7(2) deadline = inclusion date + 6 months", d.article_7_2_deadline == date(2026, 8, 4))

    # --- duty calculator: quantity at/below 1 tonne/year ---
    d = assess_duties(0.5, candidate_list_inclusion_date=date(2026, 2, 4), quantity_tonnes_per_year=0.5)
    check("Art 7(2) not triggered at/below 1 tonne/year", d.article_7_2_duty is False)

    # --- duty calculator: not placed on EU market ---
    d = assess_duties(5.0, placed_on_eu_market=False)
    check("Not placed on EU market: Art 33 not triggered", d.article_33_duty is False)
    check("Not placed on EU market: SCIP not triggered", d.scip_duty is False)

    # --- month-rollover edge case for _add_months (via SCIP deadline) ---
    d = assess_duties(0.5, candidate_list_inclusion_date=date(2025, 8, 31))
    check("Month-end rollover handled (Aug 31, 2025 + 6mo -> Feb 28, 2026, non-leap year)",
          d.scip_deadline == date(2026, 2, 28))

    # --- candidate list milestones ---
    check("Milestones has 4 entries", len(CANDIDATE_LIST_MILESTONES) == 4)
    check("Latest milestone is 253 substances", CANDIDATE_LIST_MILESTONES[-1].total_substances == 253)
    check("First milestone is 15 substances (2008)", CANDIDATE_LIST_MILESTONES[0].total_substances == 15)

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S): {failures}")
        raise SystemExit(1)
    else:
        print("All checks passed.")


if __name__ == "__main__":
    run()
