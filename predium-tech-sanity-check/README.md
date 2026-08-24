# Predium Technology Sanity Check

A small Streamlit app that flags energy source / consumer technology combinations
worth a second look, built from Predium's own compatibility rules and real internal
reference data (not manual re-review each time).

## What it does

- **Check a Predium export**: upload an Excel/CSV technology export, map your
  columns, and get a per-row severity (High/Medium/Low) with plain-English reasons
  -- plus a downloadable results file.
- **Check one combination**: pick a system/source/technology and any known building
  details, get an instant verdict.

## Files

- `rules.py` -- the single source of truth: one `TechRule` per technology, derived
  from Predium's `SourceTypesForTechnologyType.ts` / `TechnologyTypesForSystemType.ts`
  and real query results from `reference_buildings.db`. Update this file if Predium's
  enums or compatibility rules change -- don't hand-edit results elsewhere.
- `sanity_check.py` -- the verdict engine (`check_combination(...)`): validity check
  → impossibility-via-approximation check → era check → severity + reasons.
- `app.py` -- the Streamlit UI.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Notes for future development

- If you edit `rules.py` or `sanity_check.py` while Streamlit is running, restart
  the process (`streamlit run app.py` again) rather than relying on hot-reload --
  Streamlit doesn't reliably re-import sibling modules on file change.
- `absent_scope` on a rule ("ALL" / "DE_RESIDENTIAL" / "DE") only escalates to
  **High** when the record's `data_source` is `APPROXIMATED` -- a manually-entered
  or imported record with the same technology and a plausible year is expected
  and should not be flagged hard.
