# Heating x Hot Water Matrix

A simple visual showcase of which Heating + Hot Water technology combinations are
realistic in a real building, for a given Predium account. Separate from
`predium-tech-sanity-check` -- that app checks one technology against its energy
source; this one checks Heating against Hot Water for the same building.

## Files

- `matrix_rules.py` -- the single source of truth: category definitions and the
  Standard/Could be/Rare/Practically Impossible judgment per pairing. Update this
  file if the judgment needs to change; the app and the Excel export both derive
  from the same logic.
- `app.py` -- the Streamlit UI: full matrix view, single-pairing checker, and a
  catalog-gaps tab (technologies Predium doesn't offer a central or decentral
  version of yet).

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Status

- 11 Heating categories x 11 Hot Water categories, central/decentral split per fuel
  (matching Predium's own "Kessel" = central / "Ofen" = decentral naming).
- Two judgments are confirmed against real co-occurrence counts in Predium's
  reference-building database; the rest rest on engineering reasoning about shared
  vs. duplicate infrastructure. See the Excel workbook's "Source & Methodology" tab
  (`~/Downloads/Heizung_Warmwasser_Matrix.xlsx`) for the full writeup and the
  specific counts.
- Next possible step: verify the newly-split Oil/Wood/Coal central-vs-decentral
  cells against real per-pair co-occurrence counts at this finer grain (not yet done).
