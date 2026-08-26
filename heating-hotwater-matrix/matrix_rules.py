"""
Single source of truth for the Heating x Hot Water plausibility matrix.

Categories come from Predium's own technology catalog (enum + German i18n labels --
"Kessel" = boiler = central, "Ofen" = stove = decentral, "Zentral-"/"Klein-" = explicit).
The Standard/Could be/Rare/Practically Impossible judgment is engineering reasoning about
shared vs. duplicate infrastructure, with two specific overrides confirmed against real
co-occurrence counts queried from Predium's own reference-building database
(reference_buildings.db, TABULA/IWU-sourced) -- see OVERRIDES below and the Excel
workbook's "Source & Methodology" tab for the full writeup.

If a category or judgment needs to change, change it here -- the app renders whatever
this file says.
"""

from dataclasses import dataclass


@dataclass
class Category:
    name: str
    fuel: str
    flexible: bool  # "utility-fed decentral" (gas line / electric wire already present) -> pairs with anything
    heating_eligible: bool
    hotwater_eligible: bool
    predium_gap_note: str | None = None


CATEGORIES: list[Category] = [
    Category("Gas Central", "gas", False, True, True),
    Category("Gas Decentral", "gas", True, True, True),
    Category("Oil Central", "oil", False, True, True),
    Category("Oil Decentral", "oil", False, True, True),
    Category("Coal", "coal", False, True, True,
              "No CENTRAL coal option exists in Predium's catalog -- only the decentral stove "
              "(Kohle-Ofen / COAL_FURNACE)."),
    Category("Wood Central", "wood", False, True, True),
    Category("Wood Decentral", "wood", False, True, True),
    Category("District Heating", "dh", False, True, True),
    Category("Heat Pump (LWP/SWP)", "hp", True, True, True,
              "Predium does NOT distinguish central vs. decentral heat pump installs -- one "
              "technology value covers both."),
    Category("Direct Electric Heating", "de", False, True, True),
    Category("Electric Storage Central", "es", False, True, False,
              "Heating-only in Predium -- no matching central hot-water storage technology exists."),
    Category("Electric Decentral (hot water)", "ed", True, False, True,
              "Hot-water-only in Predium (Durchlauferhitzer / Tauchsieder) -- no equivalent "
              "decentral electric heating-only technology."),
]

CATEGORIES_BY_NAME = {c.name: c for c in CATEGORIES}
HEATING_CATEGORIES = [c.name for c in CATEGORIES if c.heating_eligible]
HOTWATER_CATEGORIES = [c.name for c in CATEGORIES if c.hotwater_eligible]

STATUS_EXPLANATION = {
    "Standard": "The common, expected pairing.",
    "Could be": "Plausible add-on/retrofit -- this hot-water technology piggybacks on wiring/piping "
                "already present for other purposes, so it can coexist with almost any heating choice.",
    "Rare": "Confirmed to occur in Predium's real reference data, just very infrequently (a handful "
            "of times out of hundreds of building records) -- genuinely happens, just uncommon.",
    "Practically Impossible": "Zero occurrences in Predium's real reference data -- would mean "
                               "duplicating central infrastructure, or running two unrelated "
                               "fuel-storage systems, for no benefit.",
}

# Overrides confirmed against real co-occurrence counts in Predium's reference-building database.
# Format: (hotwater_category, heating_category) -> status
OVERRIDES: dict[tuple[str, str], str] = {
    ("Electric Decentral (hot water)", "Electric Storage Central"): "Standard",  # real DB: 38 co-occurrences
    ("Gas Central", "District Heating"): "Rare",       # real DB: 2 co-occurrences
    ("District Heating", "Gas Central"): "Rare",        # real DB: 2 co-occurrences
}


def judge(hotwater_name: str, heating_name: str) -> str:
    if (hotwater_name, heating_name) in OVERRIDES:
        return OVERRIDES[(hotwater_name, heating_name)]
    if hotwater_name == heating_name:
        return "Standard"
    hw = CATEGORIES_BY_NAME[hotwater_name]
    if hw.flexible:
        return "Could be"
    return "Practically Impossible"


def full_matrix() -> dict[str, dict[str, str]]:
    """{hotwater_category: {heating_category: status}}"""
    return {
        hw: {h: judge(hw, h) for h in HEATING_CATEGORIES}
        for hw in HOTWATER_CATEGORIES
    }


# Maps a Predium technology enum code to one of the categories above. A handful of
# enum values don't map cleanly:
#   - LOW_TEMPERATURE_BOILER is gas OR oil depending on its energy source -- pass
#     source_enum to enum_to_category() to disambiguate.
#   - SOLAR_PLANT is treated as a supplement, not a standalone category (see the
#     Excel workbook's methodology notes) -- excluded here; a building's "real"
#     hot-water technology should be picked as whichever non-solar route has the
#     largest reported final energy, with solar-only buildings falling back to
#     the solar route itself (flagged separately, not run through the matrix).
#   - SMALL_ELECTRIC_STORAGE is not offered in Predium's manual UI at all and is
#     absent from its reference data -- if it appears in a real export, that's
#     worth flagging on its own, independent of the matrix.
ENUM_TO_CATEGORY: dict[str, str] = {
    "GAS_CONDENSING_BOILER": "Gas Central",
    "GAS_NON_CONDENSING_BOILER": "Gas Central",
    "GAS_ROOM_HEATER": "Gas Decentral",
    "GAS_FLOOR_HEATING": "Gas Decentral",
    "GAS_FLOW_HEATER": "Gas Decentral",
    "STANDARD_BOILER": "Oil Central",
    "CONDENSING_BOILER": "Oil Central",
    "OIL_FURNACE": "Oil Decentral",
    "COAL_FURNACE": "Coal",
    "WOOD_BOILER": "Wood Central",
    "WOOD_FURNACE": "Wood Decentral",
    "DISTRICT_HEATING_WITH_KWK": "District Heating",
    "DISTRICT_HEATING_WITHOUT_KWK": "District Heating",
    "ELECTRIC_HEAT_PUMP_AIR": "Heat Pump (LWP/SWP)",
    "ELECTRIC_HEAT_PUMP_GEO": "Heat Pump (LWP/SWP)",
    "DIRECT_ELECTRICITY_HEATING": "Direct Electric Heating",
    "CENTRAL_ELECTRIC_STORAGE": "Electric Storage Central",
    "ELECTRIC_IMMERSION_HEATER": "Electric Decentral (hot water)",
    "ELECTRIC_FLOW_HEATER": "Electric Decentral (hot water)",
}

NO_CATEGORY_TECHS = {"SOLAR_PLANT", "SMALL_ELECTRIC_STORAGE"}  # handled specially, see note above


def enum_to_category(tech_enum: str, source_enum: str | None = None) -> str | None:
    tech_enum = (tech_enum or "").strip().upper()
    if tech_enum == "LOW_TEMPERATURE_BOILER":
        return "Oil Central" if (source_enum or "").strip().upper() == "FUEL_OIL" else "Gas Central"
    return ENUM_TO_CATEGORY.get(tech_enum)
