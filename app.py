"""
EU REACH SVHC Candidate List & Article Communication Screener -- Streamlit app.

Screens substance/ingredient names against a curated subset of ECHA's REACH
Candidate List, and calculates which Article 33 / Article 7(2) / SCIP duties
are triggered for a given concentration.
"""

from datetime import date

import pandas as pd
import streamlit as st

from reach_svhc_screener import (
    CANDIDATE_LIST_MILESTONES,
    HAZARD_LABELS,
    SUBSTANCE_TABLE,
    SVHC_THRESHOLD_PCT,
    assess_duties,
    lookup_substance,
    screen_substances,
)

st.set_page_config(page_title="REACH SVHC Screener", page_icon="🌍", layout="wide")

st.title("🌍 EU REACH SVHC Candidate List & Article Communication Screener")
st.markdown(
    "Once a substance is added to ECHA's REACH **Candidate List of Substances of "
    "Very High Concern (SVHC)**, anyone placing articles containing it above "
    "**0.1% weight-by-weight (w/w)** on the EU/EEA market can owe an Article 33 "
    "communication duty, an Article 7(2) notification to ECHA, and a SCIP database "
    "notification. This tool screens your substances against a curated subset of "
    "the Candidate List and calculates which of those duties apply."
)
st.caption(
    "This is a **listing and duty-timing screener**, not a REACH compliance or legal "
    "opinion tool -- it does not measure your product's actual composition and its "
    "curated substance table is a subset, not the full 253-substance Candidate List. "
    "See the About tab for scope, sources, and why you should verify against the live "
    "ECHA Candidate List before making a compliance decision."
)

tab_lookup, tab_batch, tab_duty, tab_history, tab_about = st.tabs(
    ["Substance lookup", "Batch upload (CSV)", "Article 33 / 7(2) / SCIP duty calculator",
     "Candidate List history", "About / methodology"]
)

with tab_lookup:
    st.subheader("Look up a single substance")
    name = st.text_input("Substance / ingredient name", placeholder="e.g. BPA, DEHP, PFOS, borax")
    if st.button("Look up", type="primary"):
        if not name.strip():
            st.warning("Enter a substance or ingredient name first.")
        else:
            substance = lookup_substance(name)
            st.divider()
            if substance is None:
                st.success(
                    f"✅ '{name}' does not match any substance in this tool's curated "
                    f"Candidate List subset. This does NOT confirm it's off the official "
                    f"ECHA list -- check echa.europa.eu/candidate-list-table for a "
                    f"definitive answer."
                )
            else:
                hazard_text = ", ".join(HAZARD_LABELS[h] for h in substance.hazard_reasons)
                st.error(f"🚩 '{name}' matches a Candidate List substance: **{substance.name}**")
                with st.container(border=True):
                    st.markdown(f"**Category:** {substance.category}")
                    st.markdown(f"**Reason(s) for SVHC identification:** {hazard_text}")
                    st.markdown(f"**Commonly found in:** {substance.common_uses}")
                    if substance.note:
                        st.caption(substance.note)

    with st.expander("See the full curated substance table"):
        df = pd.DataFrame(
            [
                {
                    "Substance": s.name,
                    "Category": s.category,
                    "Reason(s) for listing": ", ".join(HAZARD_LABELS[h] for h in s.hazard_reasons),
                    "Common uses": s.common_uses,
                }
                for s in SUBSTANCE_TABLE
            ]
        )
        st.dataframe(df, width="stretch")

with tab_batch:
    st.subheader("Screen a full substance list at once")
    st.write("Upload a CSV with one substance per row and a column named `substance`.")
    st.download_button(
        "Download a CSV template",
        data="substance\nBPA\nSodium chloride\nPFOS\nDEHP\nCitric acid\n",
        file_name="reach_svhc_screener_template.csv",
        mime="text/csv",
    )

    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded is not None:
        try:
            df_in = pd.read_csv(uploaded)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not read that CSV: {exc}")
            df_in = None

        if df_in is not None:
            df_in.columns = [c.lower().strip() for c in df_in.columns]
            if "substance" not in df_in.columns:
                st.error("CSV is missing the required column: `substance`")
            else:
                st.write(f"Loaded {len(df_in)} substance(s). Preview:")
                st.dataframe(df_in.head(10), width="stretch")

                if st.button("Run batch screen", type="primary"):
                    results = screen_substances(df_in["substance"].astype(str).tolist())
                    out_rows = [
                        {
                            "substance": r.query,
                            "listed": r.is_listed,
                            "matched_substance": r.substance.name if r.substance else "",
                            "category": r.substance.category if r.substance else "",
                            "reason(s)_for_listing": (
                                ", ".join(HAZARD_LABELS[h] for h in r.substance.hazard_reasons)
                                if r.substance else ""
                            ),
                        }
                        for r in results
                    ]
                    df_out = pd.DataFrame(out_rows)

                    n_listed = int(df_out["listed"].sum())
                    c1, c2 = st.columns(2)
                    c1.metric("Substances screened", len(df_out))
                    c2.metric("Matched a Candidate List entry", n_listed)

                    st.dataframe(df_out, width="stretch")
                    st.download_button(
                        "Download full results (CSV)",
                        data=df_out.to_csv(index=False),
                        file_name="reach_svhc_screen_results.csv",
                        mime="text/csv",
                        type="primary",
                    )

with tab_duty:
    st.subheader("Article 33 / Article 7(2) / SCIP duty calculator")
    st.write(
        f"Enter a substance's concentration in your article to see which duties are "
        f"triggered. All three run off the same **{SVHC_THRESHOLD_PCT}% w/w** "
        f"threshold, evaluated per REACH guidance at the level of each individual "
        f"article within a complex product, not the whole product's average "
        f"composition."
    )

    col1, col2 = st.columns(2)
    with col1:
        concentration = st.number_input(
            "Concentration in the article (% w/w)", min_value=0.0, max_value=100.0,
            value=0.5, step=0.01, format="%.3f",
        )
        placed_on_market = st.checkbox("Article is placed on the EU/EEA market", value=True)
    with col2:
        know_date = st.checkbox("I know the substance's Candidate List inclusion date")
        inclusion_date = None
        if know_date:
            inclusion_date = st.date_input(
                "Candidate List inclusion date",
                value=date(2026, 2, 4),
                help="Check echa.europa.eu/candidate-list-table for the exact date.",
            )
        know_quantity = st.checkbox("I know the total annual quantity across my articles")
        quantity = None
        if know_quantity:
            quantity = st.number_input("Quantity (tonnes/year)", min_value=0.0, value=1.5, step=0.1)

    if st.button("Assess duties", type="primary"):
        result = assess_duties(
            concentration_pct=concentration,
            placed_on_eu_market=placed_on_market,
            candidate_list_inclusion_date=inclusion_date,
            quantity_tonnes_per_year=quantity,
        )
        st.divider()

        def _duty_box(title, triggered, note):
            with st.container(border=True):
                if triggered is True:
                    st.error(f"**{title}: TRIGGERED**")
                elif triggered is False:
                    st.success(f"**{title}: Not triggered**")
                else:
                    st.warning(f"**{title}: Cannot assess**")
                st.write(note)

        _duty_box("Article 33 -- duty to communicate", result.article_33_duty, result.article_33_note)
        _duty_box("SCIP database notification", result.scip_duty, result.scip_note)
        _duty_box("Article 7(2) -- notification to ECHA", result.article_7_2_duty, result.article_7_2_note)

with tab_history:
    st.subheader("Candidate List update history (verified milestones)")
    st.write(
        "ECHA has updated the Candidate List roughly twice a year since it was "
        "first published. This tool tracks a few verified milestones -- not "
        "every historical update -- as a reminder to re-screen periodically."
    )
    for m in CANDIDATE_LIST_MILESTONES:
        with st.container(border=True):
            st.markdown(f"**{m.label}** -- {m.total_substances} substances total")
            st.caption(m.note)
    st.info(
        "The Candidate List currently stands at 253 substances as of the February "
        "4, 2026 update. Check "
        "[echa.europa.eu/candidate-list-table](https://echa.europa.eu/candidate-list-table) "
        "for the complete, current, authoritative list."
    )

with tab_about:
    st.markdown(
        """
### What the REACH Candidate List requires

Once ECHA adds a substance to the Candidate List of Substances of Very High
Concern (SVHC) -- for properties such as being carcinogenic, mutagenic, toxic
for reproduction (CMR), persistent/bioaccumulative/toxic (PBT or vPvB), or of
"equivalent concern" (e.g. endocrine-disrupting) -- three duties can apply to
anyone placing articles containing it on the EU/EEA market above **0.1% w/w**:

- **Article 33 duty to communicate**: proactively provide safe-use information
  to professional customers, and respond to any consumer request within
  **45 days**.
- **Article 7(2) notification to ECHA**: required within **6 months** of the
  substance's Candidate List inclusion, if concentration exceeds 0.1% w/w
  *and* total quantity exceeds 1 tonne/year -- unless exposure can be excluded
  or the use is already covered by a REACH registration.
- **SCIP database notification**: required within **6 months** of the
  substance's Candidate List inclusion, for any article above 0.1% w/w placed
  on the EU/EEA market (in force since January 5, 2021).

### Current status

The Candidate List contains **253 substances** as of the February 4, 2026
update, which added n-hexane and Bisphenol AF (BPAF). See the Candidate List
history tab for verified milestones.

### What this tool is (and isn't)

This is a **screener and duty-timing calculator**, not a substitute for a
REACH compliance consultant or legal counsel. It does not:

- Reproduce ECHA's full 253-substance Candidate List -- it covers a curated
  subset of commonly encountered substances (phthalates, PFAS, flame
  retardants, lead and other heavy metal compounds, bisphenols, siloxanes,
  boron compounds, and others).
- Measure or verify your product's actual substance concentration -- you
  supply that figure from your own testing, supplier declarations, or bill of
  materials.
- Determine whether an Article 7(2) exemption (excluded exposure, or an
  already-registered use) applies to your specific case.
- Track the Authorisation List (Annex XIV) or the Restriction List
  (Annex XVII), which carry separate obligations and sunset dates from the
  Candidate List.

Always verify against the current ECHA Candidate List and consult qualified
REACH counsel before finalizing a compliance decision.

### Sources

- ECHA, "Candidate List of substances of very high concern for authorisation",
  echa.europa.eu/candidate-list-table
- ECHA, "Summary of obligations resulting from inclusion of SVHCs in the
  Candidate List", echa.europa.eu/candidate-list-obligations
- REACH Regulation (EC) No 1907/2006, Articles 7(2), 31, and 33
- SCIP database (Waste Framework Directive 2008/98/EC, as amended), in force
  since January 5, 2021
        """
    )
