"""
Predium export parsing -- mirrors predium-tech-sanity-check/app.py's approach, kept
as a separate small copy here so this app stays independently runnable/deployable.
"""

import io

import pandas as pd

HEADER_MARKERS = {
    "system", "verbraucher", "energieträger", "predium referenz", "technology", "energy source",
    "baujahr", "wirtschaftseinheit", "nutzungsart", "interne referenz", "building id", "adresse",
}


def find_header_row(raw_df: pd.DataFrame, max_scan: int = 20) -> int:
    """Real Predium exports have a few title/metadata rows before the real header."""
    for i in range(min(max_scan, len(raw_df))):
        row_values = {str(v).strip().lower() for v in raw_df.iloc[i].tolist() if pd.notna(v)}
        if len(row_values & HEADER_MARKERS) >= 2:
            return i
    return 0


def read_sheet_with_autoheader(file_bytes: bytes, filename: str, sheet_name=None) -> pd.DataFrame:
    if filename.endswith(".csv"):
        raw = pd.read_csv(io.BytesIO(file_bytes), header=None, nrows=20)
        header_row = find_header_row(raw)
        return pd.read_csv(io.BytesIO(file_bytes), header=header_row)
    else:
        raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=None, nrows=20)
        header_row = find_header_row(raw)
        return pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, header=header_row)


def best_match(columns, *candidates) -> str:
    lookup = {c.strip().lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in lookup:
            return lookup[cand.lower()]
    return "(none)"
