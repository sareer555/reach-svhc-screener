# REACH SVHC Candidate List & Article Communication Screener

A Streamlit tool that screens substances/ingredients against a curated subset
of ECHA's REACH Candidate List of Substances of Very High Concern (SVHC), and
calculates which Article 33, Article 7(2), and SCIP database duties are
triggered by a given concentration.

## What it does

Once ECHA adds a substance to the Candidate List, anyone placing articles
containing it above **0.1% w/w** on the EU/EEA market can owe:

- An **Article 33 duty to communicate** safe-use information (proactively,
  and within 45 days of any consumer request).
- An **Article 7(2) notification to ECHA**, within 6 months of the
  substance's Candidate List inclusion, if quantity exceeds 1 tonne/year.
- A **SCIP database notification**, within 6 months of the substance's
  Candidate List inclusion, in force since January 5, 2021.

This tool:

- Looks up a single substance or ingredient name against a curated table of
  commonly encountered Candidate List substances (phthalates, PFAS, flame
  retardants, heavy metal compounds, bisphenols, siloxanes, boron compounds,
  and others), showing the reason(s) for its SVHC identification.
- Screens a full substance list at once via CSV upload.
- Calculates which of the three duties above are triggered for a given
  concentration, and (if you supply the substance's Candidate List inclusion
  date and/or annual quantity) the exact 6-month deadlines.
- Tracks verified Candidate List size milestones, as a reminder that ECHA
  updates the list roughly twice a year.

It is a **listing and duty-timing screener**, not a REACH compliance or legal
opinion tool: it does not measure your product's actual composition, does not
verify Article 7(2) exemptions, and its substance table is a curated subset,
not the full 253-substance Candidate List. Always verify against the live
ECHA Candidate List and consult qualified REACH counsel before finalizing a
compliance decision.

## Files

- `app.py` -- Streamlit UI (substance lookup, batch CSV screen, duty
  calculator, Candidate List history, and an About/methodology tab).
- `reach_svhc_screener.py` -- core logic: the curated substance table, lookup
  functions, the Article 33/7(2)/SCIP duty calculator, and verified Candidate
  List milestones.
- `test_reach_svhc_screener.py` -- unit tests covering lookups, batch
  screening, and duty-calculator edge cases including month-end date rollover
  (`python3 test_reach_svhc_screener.py`).
- `requirements.txt` -- Python dependencies (streamlit, pandas).

## Running locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploying

Same flow as the other tools in this account: push to a GitHub repo, then on
[share.streamlit.io](https://share.streamlit.io) choose "Deploy a public app
from GitHub", point it at this repo's `main` branch and `app.py`, and deploy.

## Sources

- ECHA, "Candidate List of substances of very high concern for
  authorisation", https://echa.europa.eu/candidate-list-table
- ECHA, "Summary of obligations resulting from inclusion of SVHCs in the
  Candidate List", https://echa.europa.eu/candidate-list-obligations
- REACH Regulation (EC) No 1907/2006, Articles 7(2), 31, and 33
- SCIP database (Waste Framework Directive 2008/98/EC, as amended), in force
  since January 5, 2021

## v2 extension ideas

- Sync against ECHA's published Candidate List export instead of a curated
  static table, so newly listed substances show up automatically.
- Add the Authorisation List (Annex XIV) and Restriction List (Annex XVII),
  each with their own obligations and sunset/review dates.
- Auto-populate a substance's Candidate List inclusion date from a synced
  ECHA dataset instead of requiring manual entry.
