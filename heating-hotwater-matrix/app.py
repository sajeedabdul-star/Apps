import io

import pandas as pd
import streamlit as st

from export_utils import best_match, read_sheet_with_autoheader
from label_maps import IN_SCOPE_SYSTEMS, map_source_label, map_system_label, map_tech_label
from matrix_rules import (
    CATEGORIES_BY_NAME,
    HEATING_CATEGORIES,
    HOTWATER_CATEGORIES,
    NO_CATEGORY_TECHS,
    STATUS_EXPLANATION,
    enum_to_category,
    full_matrix,
    judge,
)

st.set_page_config(page_title="Heating x Hot Water Matrix", layout="wide")

STATUS_COLOR = {
    "Standard": "#C6E0B4",
    "Could be": "#FFE699",
    "Rare": "#F4B183",
    "Practically Impossible": "#E06666",
}
STATUS_TEXT_COLOR = {
    "Standard": "#1C2321", "Could be": "#1C2321", "Rare": "#1C2321", "Practically Impossible": "#FFFFFF",
}

st.title("Heating x Hot Water Combination Matrix")
st.caption(
    "For a given building, is its Heating technology + Hot Water technology combination realistic? "
    "Central/decentral split per fuel, matching Predium's own technology catalog."
)

tab_export, tab_matrix, tab_check, tab_gaps = st.tabs(
    ["📤 Check a Predium export", "🗂️ The Matrix", "🔍 Check a pairing", "⚠️ Catalog gaps"]
)

# =========================================================== TAB 0: check a Predium export
with tab_export:
    st.subheader("Upload a Predium technology export")
    st.write(
        "Upload a real Predium export (the 'Technik' sheet of a *_predium_basic.xlsx file works directly). "
        "For every building, this finds its Heating technology and Hot Water technology and looks up the "
        "pairing in the matrix -- so you can see which real buildings are worth a second look."
    )

    uploaded = st.file_uploader("Predium export (.xlsx or .csv)", type=["xlsx", "csv"], key="export_upload")

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
        st.write(f"Loaded **{len(df)}** rows from `{sheet_name or uploaded.name}`.")
        with st.expander("Preview raw data"):
            st.dataframe(df.head(20), width='stretch')

        st.markdown("#### Map your columns")
        cols = ["(none)"] + list(df.columns)
        c1, c2, c3 = st.columns(3)
        with c1:
            col_bid = st.selectbox("Building ID *", cols, index=cols.index(
                best_match(df.columns, "Predium Referenz", "Building ID")) if best_match(df.columns, "Predium Referenz", "Building ID") in cols else 0)
            col_addr = st.selectbox("Address", cols, index=cols.index(
                best_match(df.columns, "Adresse", "Address")) if best_match(df.columns, "Adresse", "Address") in cols else 0)
        with c2:
            col_sys = st.selectbox("System *", cols, index=cols.index(
                best_match(df.columns, "System")) if best_match(df.columns, "System") in cols else 0)
            col_tech = st.selectbox("Technology *", cols, index=cols.index(
                best_match(df.columns, "Verbraucher", "Technology")) if best_match(df.columns, "Verbraucher", "Technology") in cols else 0)
        with c3:
            col_src = st.selectbox("Energy Source", cols, index=cols.index(
                best_match(df.columns, "Energieträger", "Energy Source")) if best_match(df.columns, "Energieträger", "Energy Source") in cols else 0)
            col_energy = st.selectbox("Final energy (Endenergie)", cols, index=cols.index(
                best_match(df.columns, "Endenergie", "Final Energy")) if best_match(df.columns, "Endenergie", "Final Energy") in cols else 0)

        required_ok = col_bid != "(none)" and col_sys != "(none)" and col_tech != "(none)"
        if not required_ok:
            st.warning("Map at least Building ID, System, and Technology to run the check.")
        elif st.button("Find combinations to check", type="primary"):

            def get(row, colname, default=None):
                if colname in (None, "(none)"):
                    return default
                val = row.get(colname, default)
                return default if pd.isna(val) else val

            # Group rows by (Building, System) so a building's multiple energy paths
            # for the same system (e.g. main boiler + solar supplement) collapse into
            # one representative technology -- the one with the largest final energy,
            # skipping solar/unmapped-only routes when a real alternative exists.
            buildings: dict = {}
            for _, row in df.iterrows():
                bid = get(row, col_bid)
                system_label = get(row, col_sys)
                if bid is None or system_label is None:
                    continue
                system = map_system_label(str(system_label))
                if system not in IN_SCOPE_SYSTEMS:
                    continue

                tech_enum = map_tech_label(get(row, col_tech))
                source_enum = map_source_label(get(row, col_src)) if col_src != "(none)" else None
                try:
                    energy = float(get(row, col_energy, 0) or 0) if col_energy != "(none)" else 0.0
                except (ValueError, TypeError):
                    energy = 0.0

                key = (bid, system)
                candidate = {
                    "tech_enum": tech_enum, "tech_label": get(row, col_tech),
                    "source_enum": source_enum, "energy": energy,
                }
                existing = buildings.setdefault(bid, {}).get(system)
                is_solar = tech_enum in NO_CATEGORY_TECHS
                existing_is_solar = existing and existing["tech_enum"] in NO_CATEGORY_TECHS
                if existing is None:
                    buildings[bid][system] = candidate
                elif is_solar and not existing_is_solar:
                    pass  # keep the existing non-solar route
                elif existing_is_solar and not is_solar:
                    buildings[bid][system] = candidate  # prefer a real route over solar
                elif candidate["energy"] > existing["energy"]:
                    buildings[bid][system] = candidate

            address_by_id = {}
            if col_addr != "(none)":
                for _, row in df.iterrows():
                    bid = get(row, col_bid)
                    addr = get(row, col_addr)
                    if bid is not None and addr and bid not in address_by_id:
                        address_by_id[bid] = addr

            RESULT_COLUMNS = ["Building ID", "Address", "Heating Technology", "Heating Category",
                               "Hot Water Technology", "Hot Water Category", "Verdict"]
            results = []
            heating_only = hotwater_only = 0
            for bid, systems in buildings.items():
                heating = systems.get("HEATING")
                hotwater = systems.get("HOT_WATER")
                if heating is None or hotwater is None:
                    heating_only += heating is not None
                    hotwater_only += hotwater is not None
                    continue  # need both to judge a pairing

                heating_cat = enum_to_category(heating["tech_enum"], heating["source_enum"], "HEATING")
                hotwater_cat = enum_to_category(hotwater["tech_enum"], hotwater["source_enum"], "HOT_WATER")

                if heating["tech_enum"] in NO_CATEGORY_TECHS or hotwater["tech_enum"] in NO_CATEGORY_TECHS:
                    status = "N/A (solar-only route)"
                elif heating_cat is None or hotwater_cat is None:
                    status = "N/A (unrecognized technology)"
                else:
                    status = judge(hotwater_cat, heating_cat)

                results.append({
                    "Building ID": bid,
                    "Address": address_by_id.get(bid, ""),
                    "Heating Technology": heating["tech_label"],
                    "Heating Category": heating_cat or "(unmapped)",
                    "Hot Water Technology": hotwater["tech_label"],
                    "Hot Water Category": hotwater_cat or "(unmapped)",
                    "Verdict": status,
                })

            results_df = pd.DataFrame(results, columns=RESULT_COLUMNS)
            st.session_state["export_results_df"] = results_df
            st.session_state["export_skip_counts"] = (heating_only, hotwater_only, len(buildings))

    if "export_results_df" in st.session_state:
        results_df = st.session_state["export_results_df"]
        st.markdown("#### Results")

        if results_df.empty:
            heating_only, hotwater_only, n_buildings = st.session_state.get("export_skip_counts", (0, 0, 0))
            st.warning(
                f"Found {n_buildings} building(s) in-scope (System = Heating or Hot Water), but none had "
                f"**both** a Heating and a Hot Water row -- {heating_only} had only Heating, {hotwater_only} "
                f"had only Hot Water. Nothing to compare a pairing against. This usually means the System "
                f"column mapping doesn't match this file's labels, or the sheet genuinely only tracks one "
                f"system type. Check the column mapping above and the 'Preview raw data' section."
            )
            st.stop()

        order = ["Practically Impossible", "Rare", "Could be", "Standard", "N/A (unrecognized technology)", "N/A (solar-only route)"]
        counts = results_df["Verdict"].value_counts().reindex(order, fill_value=0)
        cols = st.columns(len(order))
        icons = {"Practically Impossible": "🔴", "Rare": "🟠", "Could be": "🟡", "Standard": "🟢",
                 "N/A (unrecognized technology)": "⚪", "N/A (solar-only route)": "⚪"}
        for c, key in zip(cols, order):
            c.metric(f"{icons[key]} {key}", int(counts[key]))
        st.metric("Total buildings (both systems present)", len(results_df))

        default_filter = ["Practically Impossible", "Rare"]
        severity_filter = st.multiselect("Filter by verdict", order, default=default_filter)
        filtered = results_df[results_df["Verdict"].isin(severity_filter)] if severity_filter else results_df

        def highlight(row):
            color = STATUS_COLOR.get(row["Verdict"], "#E7E6E6")
            fg = STATUS_TEXT_COLOR.get(row["Verdict"], "#1C2321")
            return [f"background-color: {color}; color: {fg}" if col == "Verdict" else "" for col in row.index]

        st.dataframe(filtered.style.apply(highlight, axis=1), width='stretch', height=500)

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            results_df.to_excel(writer, index=False, sheet_name="Heating-HotWater Check")
        st.download_button(
            "⬇️ Download full results (.xlsx)", data=buf.getvalue(),
            file_name="heating_hotwater_check_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

# =========================================================== TAB 1: the matrix
with tab_matrix:
    st.subheader("Full matrix")
    st.write("Rows = Hot Water technology. Columns = Heating technology.")

    matrix = full_matrix()
    df = pd.DataFrame(matrix).T  # rows = hot water, cols = heating
    df = df[HEATING_CATEGORIES]

    def style_cell(val):
        bg = STATUS_COLOR.get(val, "#FFFFFF")
        fg = STATUS_TEXT_COLOR.get(val, "#000000")
        return f"background-color: {bg}; color: {fg}; text-align: center; font-weight: 600;"

    st.dataframe(df.style.map(style_cell), width='stretch', height=460)

    st.markdown("#### Legend")
    legend_cols = st.columns(4)
    for col, (status, color) in zip(legend_cols, STATUS_COLOR.items()):
        with col:
            st.markdown(
                f"<div style='background-color:{color}; color:{STATUS_TEXT_COLOR[status]}; "
                f"padding:10px; border-radius:8px; text-align:center; font-weight:600;'>{status}</div>"
                f"<p style='font-size:12.5px; color:#6B736F; margin-top:6px;'>{STATUS_EXPLANATION[status]}</p>",
                unsafe_allow_html=True,
            )

# =========================================================== TAB 2: check a pairing
with tab_check:
    st.subheader("Check one pairing")
    col_a, col_b = st.columns(2)
    with col_a:
        heating = st.selectbox("Heating technology", HEATING_CATEGORIES)
    with col_b:
        hotwater = st.selectbox("Hot Water technology", HOTWATER_CATEGORIES)

    if st.button("Check this pairing", type="primary"):
        status = judge(hotwater, heating)
        color = STATUS_COLOR[status]
        fg = STATUS_TEXT_COLOR[status]
        st.markdown(
            f"<div style='background-color:{color}; color:{fg}; padding:18px; border-radius:10px;'>"
            f"<h3 style='margin:0'>{status}</h3>"
            f"<p style='margin:8px 0 0; font-size:15px;'>{STATUS_EXPLANATION[status]}</p></div>",
            unsafe_allow_html=True,
        )
        gaps = []
        h_gap = CATEGORIES_BY_NAME[heating].predium_gap_note
        w_gap = CATEGORIES_BY_NAME[hotwater].predium_gap_note
        if h_gap:
            gaps.append(f"**{heating}**: {h_gap}")
        if w_gap:
            gaps.append(f"**{hotwater}**: {w_gap}")
        if gaps:
            st.info("Catalog note:\n\n" + "\n\n".join(gaps))

# =========================================================== TAB 3: catalog gaps
with tab_gaps:
    st.subheader("Where Predium's technology catalog itself has a gap")
    st.write(
        "Raised directly by feedback: 'a few more consumers need central/decentral options, e.g. coal.' "
        "These aren't matrix judgments -- they're places where Predium doesn't offer a technology option "
        "at all yet."
    )
    for c in CATEGORIES_BY_NAME.values():
        if c.predium_gap_note:
            st.markdown(f"**{c.name}**")
            st.write(c.predium_gap_note)
            st.divider()
