import io

import pandas as pd
import streamlit as st

from label_maps import (
    IN_SCOPE_SYSTEMS,
    map_country_label,
    map_data_source_label,
    map_source_label,
    map_system_label,
    map_tech_label,
)
from rules import ALL_SOURCES, ALL_SYSTEMS, valid_sources_for, valid_technologies_for
from sanity_check import check_combination

st.set_page_config(page_title="Predium Tech Sanity Check", layout="wide")

SEVERITY_COLOR = {"None": "#C6E0B4", "Low": "#C6E0B4", "Medium": "#FFE699", "High": "#F8CBAD", "N/A": "#E7E6E6"}
SEVERITY_ORDER = ["High", "Medium", "Low", "None", "N/A"]

HEADER_MARKERS = {
    "system", "verbraucher", "energieträger", "predium referenz", "technology", "energy source",
    "baujahr", "wirtschaftseinheit", "nutzungsart", "interne referenz", "building id", "adresse",
}


def find_header_row(raw_df: pd.DataFrame, max_scan: int = 20) -> int:
    """Scan the first rows of a headerless read for the real header row --
    real Predium exports have a few title/metadata rows before it."""
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
    """Return the first column name matching any candidate (case-insensitive,
    trimmed), else '(none)'."""
    lookup = {c.strip().lower(): c for c in columns}
    for cand in candidates:
        if cand.lower() in lookup:
            return lookup[cand.lower()]
    return "(none)"


st.title("Predium Technology Sanity Check")
st.caption(
    "Flags energy source / consumer technology combinations worth a second look -- built from Predium's own "
    "compatibility rules and real internal reference data."
)

tab_bulk, tab_single = st.tabs(["📂 Check a Predium export", "🔍 Check one combination"])

# =========================================================== TAB 1: bulk export
with tab_bulk:
    st.subheader("Upload a Predium technology export")
    st.write(
        "Upload a real Predium export (the 'Technik' sheet of a *_predium_basic.xlsx file works directly) or "
        "any Excel/CSV with one row per building technology record."
    )

    col_up, col_tpl = st.columns([3, 1])
    with col_up:
        uploaded = st.file_uploader("Predium export (.xlsx or .csv)", type=["xlsx", "csv"])
    with col_tpl:
        st.write("")
        st.write("")
        template_df = pd.DataFrame([
            {
                "Building ID": 12345, "Address": "Musterstrasse 1", "Postal Code": "10115", "City": "Berlin",
                "System": "HEATING", "Energy Source": "NATURAL_GAS", "Technology": "GAS_CONDENSING_BOILER",
                "Building Year Constructed": 1965, "System Construction Year": 2019, "Year Renovated": "",
                "Country": "DE", "Building Type": "RESIDENTIAL", "Monument Protection": False,
                "Is New Construction": False, "Data Source": "MANUAL",
            },
            {
                "Building ID": 12346, "Address": "Beispielweg 5", "Postal Code": "80331", "City": "Munich",
                "System": "HOT_WATER", "Energy Source": "ELECTRICITY_MIX", "Technology": "ELECTRIC_HEAT_PUMP_AIR",
                "Building Year Constructed": 1958, "System Construction Year": "", "Year Renovated": "",
                "Country": "DE", "Building Type": "RESIDENTIAL", "Monument Protection": False,
                "Is New Construction": False, "Data Source": "APPROXIMATED",
            },
        ])
        tpl_buf = io.BytesIO()
        with pd.ExcelWriter(tpl_buf, engine="openpyxl") as writer:
            template_df.to_excel(writer, index=False, sheet_name="Template")
        st.download_button(
            "⬇️ Empty template",
            data=tpl_buf.getvalue(),
            file_name="predium_sanity_check_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Download a starter template with the columns the sanity check understands, if you don't have "
                 "a real Predium export handy.",
        )

    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        sheet_name = None

        if uploaded.name.endswith(".xlsx"):
            xls = pd.ExcelFile(io.BytesIO(file_bytes))
            default_sheet = "Technik" if "Technik" in xls.sheet_names else xls.sheet_names[0]
            sheet_name = st.selectbox(
                "Which sheet has the technology data?", xls.sheet_names,
                index=xls.sheet_names.index(default_sheet),
            )

        df = read_sheet_with_autoheader(file_bytes, uploaded.name, sheet_name)
        df = df.dropna(how="all")

        st.write(f"Loaded **{len(df)}** rows, **{len(df.columns)}** columns from `{sheet_name or uploaded.name}`.")
        with st.expander("Preview raw data"):
            st.dataframe(df.head(20), width='stretch')

        # ---- Optional: join building master data (Baujahr / construction year) from a Stammdaten sheet
        stammdaten_df = None
        if uploaded.name.endswith(".xlsx") and "Stammdaten" in xls.sheet_names and sheet_name != "Stammdaten":
            join_master = st.checkbox(
                "Join building master data from the 'Stammdaten' sheet (adds construction year / Baujahr)",
                value=True,
            )
            if join_master:
                stammdaten_df = read_sheet_with_autoheader(file_bytes, uploaded.name, "Stammdaten")
                stammdaten_df = stammdaten_df.dropna(how="all")

        st.markdown("#### Map your columns")
        cols = ["(none)"] + list(df.columns)

        c1, c2, c3 = st.columns(3)
        with c1:
            col_building_id = st.selectbox("Building ID *", cols, index=cols.index(
                best_match(df.columns, "Predium Referenz", "Building ID")) if best_match(df.columns, "Predium Referenz", "Building ID") in cols else 0, key="col_bid")
            col_system = st.selectbox("System (Heating / Hot Water) *", cols, index=cols.index(
                best_match(df.columns, "System")) if best_match(df.columns, "System") in cols else 0, key="col_sys")
            col_source = st.selectbox("Energy Source *", cols, index=cols.index(
                best_match(df.columns, "Energieträger", "Energy Source")) if best_match(df.columns, "Energieträger", "Energy Source") in cols else 0, key="col_src")
            col_tech = st.selectbox("Technology *", cols, index=cols.index(
                best_match(df.columns, "Verbraucher", "Technology")) if best_match(df.columns, "Verbraucher", "Technology") in cols else 0, key="col_tech")
        with c2:
            col_address = st.selectbox("Address", cols, index=cols.index(
                best_match(df.columns, "Adresse", "Address")) if best_match(df.columns, "Adresse", "Address") in cols else 0, key="col_addr")
            col_postal = st.selectbox("Postal code", cols, index=cols.index(
                best_match(df.columns, "Postleitzahl", "Postal Code")) if best_match(df.columns, "Postleitzahl", "Postal Code") in cols else 0, key="col_plz")
            col_city = st.selectbox("City", cols, index=cols.index(
                best_match(df.columns, "Ort", "City")) if best_match(df.columns, "Ort", "City") in cols else 0, key="col_city")
            col_country = st.selectbox("Country", cols, index=cols.index(
                best_match(df.columns, "Land", "Country")) if best_match(df.columns, "Land", "Country") in cols else 0, key="col_country")
        with c3:
            col_consumer_year = st.selectbox("System's own construction year", cols, index=cols.index(
                best_match(df.columns, "Verbraucher Einbaujahr", "System Construction Year")) if best_match(df.columns, "Verbraucher Einbaujahr", "System Construction Year") in cols else 0, key="col_cyear")
            col_data_source = st.selectbox("Data source (Letzte Anpassung / manual-approximated)", cols, index=cols.index(
                best_match(df.columns, "Letzte Anpassung", "Data Source")) if best_match(df.columns, "Letzte Anpassung", "Data Source") in cols else 0, key="col_dsrc")
            col_building_type = st.selectbox("Building type (residential/non-res.)", cols, key="col_btype")
            col_monument = st.selectbox("Monument protection (bool)", cols, key="col_mon")
        col_building_year = st.selectbox(
            "Building construction year (from Stammdaten if joined, else map manually)",
            (["(from Stammdaten join)"] if stammdaten_df is not None else []) + cols,
            key="col_byear",
        )
        col_new_constr = st.selectbox("Is new construction (bool)", cols, key="col_newc")

        required_ok = col_system != "(none)" and col_source != "(none)" and col_tech != "(none)"

        if not required_ok:
            st.warning("Map at least System, Energy Source, and Technology to run the check.")
        else:
            if st.button("Run sanity check", type="primary"):

                def get(row, colname, default=None):
                    if colname in (None, "(none)", "(from Stammdaten join)"):
                        return default
                    val = row.get(colname, default)
                    return default if pd.isna(val) else val

                def to_int(val):
                    try:
                        return int(val) if val not in (None, "") else None
                    except (ValueError, TypeError):
                        return None

                # Build a building_id -> Baujahr / link lookup from Stammdaten, if joined
                master_by_id = {}
                if stammdaten_df is not None:
                    id_col = best_match(stammdaten_df.columns, "Predium Referenz", "Building ID")
                    year_col = best_match(stammdaten_df.columns, "Baujahr", "Building Year Constructed")
                    link_col = best_match(stammdaten_df.columns, "Übersicht in Predium", "Predium Link")
                    if id_col != "(none)":
                        for _, mrow in stammdaten_df.iterrows():
                            bid = get(mrow, id_col)
                            if bid is None:
                                continue
                            master_by_id[bid] = {
                                "year": to_int(get(mrow, year_col)) if year_col != "(none)" else None,
                                "link": get(mrow, link_col) if link_col != "(none)" else None,
                            }

                results = []
                for _, row in df.iterrows():
                    building_id = get(row, col_building_id, "—")
                    system_label = get(row, col_system)
                    if system_label is None:
                        continue  # blank row (e.g. a spacer / subtotal row in the export)

                    system = map_system_label(str(system_label))

                    address_parts = [
                        str(get(row, col_address, "")) or "",
                        str(get(row, col_postal, "")) or "",
                        str(get(row, col_city, "")) or "",
                    ]
                    address = ", ".join(p for p in address_parts if p)

                    master = master_by_id.get(building_id, {})
                    building_year = master.get("year") if master else None
                    if col_building_year not in (None, "(none)", "(from Stammdaten join)"):
                        building_year = to_int(get(row, col_building_year)) or building_year
                    predium_link = master.get("link")

                    if system not in IN_SCOPE_SYSTEMS:
                        results.append({
                            "Building ID": building_id, "Address": address, "System": system_label,
                            "Source": get(row, col_source), "Technology": get(row, col_tech),
                            "Severity": "N/A", "Assumed System Year": None,
                            "Reasons": "Out of scope -- the sanity check only covers Heating and Hot Water.",
                            "Predium Link": predium_link,
                        })
                        continue

                    source_enum = map_source_label(get(row, col_source))
                    tech_enum = map_tech_label(get(row, col_tech))
                    data_source_enum = map_data_source_label(get(row, col_data_source))
                    consumer_year = to_int(get(row, col_consumer_year))
                    monument = bool(get(row, col_monument, False))
                    new_constr = bool(get(row, col_new_constr, False))

                    verdict = check_combination(
                        system=system,
                        source=source_enum,
                        technology=tech_enum,
                        country=map_country_label(get(row, col_country, "DE")),
                        building_type=str(get(row, col_building_type, "RESIDENTIAL")).upper() or "RESIDENTIAL",
                        building_year_constructed=building_year,
                        consumer_construction_year=consumer_year,
                        year_renovated=None,
                        monument_protection=monument,
                        is_new_construction=new_constr,
                        data_source=data_source_enum,
                    )
                    results.append({
                        "Building ID": building_id,
                        "Address": address,
                        "System": system_label,
                        "Source": get(row, col_source),
                        "Technology": get(row, col_tech),
                        "Severity": verdict.severity,
                        "Assumed System Year": verdict.assumed_system_year,
                        "Reasons": " | ".join(verdict.reasons),
                        "Predium Link": predium_link,
                    })

                results_df = pd.DataFrame(results)
                results_df["Severity"] = pd.Categorical(results_df["Severity"], categories=SEVERITY_ORDER, ordered=True)
                results_df = results_df.sort_values("Severity")
                st.session_state["results_df"] = results_df

    if "results_df" in st.session_state:
        results_df = st.session_state["results_df"]

        st.markdown("#### Results")
        counts = results_df["Severity"].value_counts().reindex(SEVERITY_ORDER, fill_value=0)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("🔴 High", int(counts["High"]))
        m2.metric("🟡 Medium", int(counts["Medium"]))
        m3.metric("🟢 Low", int(counts["Low"]))
        m4.metric("⚪ N/A (out of scope)", int(counts["N/A"]))
        m5.metric("Total rows", len(results_df))

        severity_filter = st.multiselect("Filter by severity", SEVERITY_ORDER, default=["High", "Medium"])
        filtered = results_df[results_df["Severity"].isin(severity_filter)] if severity_filter else results_df

        def highlight_severity(row):
            color = SEVERITY_COLOR.get(row["Severity"], "#FFFFFF")
            return [f"background-color: {color}" if col == "Severity" else "" for col in row.index]

        st.dataframe(
            filtered.style.apply(highlight_severity, axis=1),
            width='stretch', height=500,
            column_config={"Predium Link": st.column_config.LinkColumn("Predium Link")},
        )

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            results_df.to_excel(writer, index=False, sheet_name="Sanity Check Results")
        st.download_button(
            "⬇️ Download full results (.xlsx)",
            data=buf.getvalue(),
            file_name="predium_sanity_check_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# =========================================================== TAB 2: single combination
with tab_single:
    st.subheader("Check one combination")
    st.write("Pick a system, technology, and source, add whatever else you know, and get an instant verdict.")

    col_a, col_b = st.columns([1, 1])

    with col_a:
        system = st.selectbox("System", ALL_SYSTEMS)
        tech_options = valid_technologies_for(system)
        technology = st.selectbox("Technology", tech_options if tech_options else ["(no valid technology for this system)"])
        source_options = valid_sources_for(technology) if tech_options else []
        source = st.selectbox("Energy Source", source_options if source_options else ["(none)"])

        st.markdown("**Building / system details** (optional, improves accuracy)")
        building_year = st.number_input("Building construction year", min_value=0, max_value=2100, value=0, step=1)
        consumer_year = st.number_input("System's own construction year (if known)", min_value=0, max_value=2100, value=0, step=1)
        year_renovated = st.number_input("Year renovated, per Energy Certificate (if known)", min_value=0, max_value=2100, value=0, step=1)

    with col_b:
        country = st.selectbox("Country", ["DE", "AT", "FR", "PL", "UK", "CZ", "BE"])
        building_type = st.selectbox("Building type", ["RESIDENTIAL", "NON_RESIDENTIAL"])
        monument = st.checkbox("Monument-protected building (Denkmalschutz)")
        new_constr = st.checkbox("Building is new construction")
        data_source = st.selectbox("How was this technology assigned?", ["UNKNOWN", "MANUAL", "APPROXIMATED", "IMPORT"])
        route_energy_final = st.number_input("Route energy_final (kWh/m2a), if known", min_value=0.0, value=0.0, step=0.5)

    if st.button("Check this combination", type="primary"):
        verdict = check_combination(
            system=system,
            source=None if source == "(none)" else source,
            technology=technology,
            country=country,
            building_type=building_type,
            building_year_constructed=building_year or None,
            consumer_construction_year=consumer_year or None,
            year_renovated=year_renovated or None,
            monument_protection=monument,
            is_new_construction=new_constr,
            data_source=None if data_source == "UNKNOWN" else data_source,
            route_energy_final=route_energy_final or None,
        )

        color = SEVERITY_COLOR.get(verdict.severity, "#FFFFFF")
        st.markdown(
            f"<div style='background-color:{color}; padding:16px; border-radius:8px;'>"
            f"<h3 style='margin:0'>Verdict: {verdict.severity}</h3></div>",
            unsafe_allow_html=True,
        )
        st.markdown("**Reasons:**")
        for reason in verdict.reasons:
            st.write(f"- {reason}")
        if verdict.assumed_system_year:
            st.caption(f"Assumed system year used for the era check: {verdict.assumed_system_year}")
