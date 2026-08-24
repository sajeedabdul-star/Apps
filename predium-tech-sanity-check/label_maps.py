"""
Translates the human-readable labels used in real Predium exports into the enum
codes rules.py / sanity_check.py operate on.

Built from two sources:
  1. Ground truth: actual distinct values observed in a real "predium_basic" export
     (Technik sheet) -- these take priority since the export tool's labels don't
     always match the app UI's i18n strings exactly (e.g. the export says
     "District heating with CHP", the UI says "District heating (from CHP)").
  2. Fallback aliases from the app's own English UI translations
     (libs/i18n/client/locales/en.json), kept for robustness across export
     vintages / other export tools.
"""

SOURCE_LABEL_TO_ENUM = {
    "biogas": "BIO_GAS",
    "coal": "COAL",
    "district heating from chp (coal)": "DISTRICT_HEATING_CHP_FOSSIL_COAL",
    "district heating from chp (gas)": "DISTRICT_HEATING_CHP_FOSSIL_GAS",
    "district heating from chp (renewable)": "DISTRICT_HEATING_CHP_RENEWABLE",
    "district heating from heating plants (coal)": "DISTRICT_HEATING_PLANTS_FOSSIL_COAL",
    "district heating from heating plants (gas)": "DISTRICT_HEATING_PLANTS_FOSSIL_GAS",
    "district heating from heating plants (renewable)": "DISTRICT_HEATING_PLANTS_RENEWABLE",
    "green electricity": "ELECTRICITY_GREEN",
    "electricity mix": "ELECTRICITY_MIX",
    "fuel oil": "FUEL_OIL",
    "lignite": "LIGNITE",
    "lpg": "LPG",
    "natural gas": "NATURAL_GAS",
    "solar energy": "SOLAR",
    "unspecified": "UNSPECIFIED",
    "wood": "WOOD",
    "wooden pellets": "WOODEN_PELLETS",
}

TECH_LABEL_TO_ENUM = {
    # Ground truth -- observed directly in a real export
    "district heating with chp": "DISTRICT_HEATING_WITH_KWK",
    "district heating without chp": "DISTRICT_HEATING_WITHOUT_KWK",
    "miscellaneous electricity": "ELECTRICITY_MISCELLANEOUS",
    "incandescent lamps": "INCANDESCENT_LAMPS",
    "gas condensing boiler": "GAS_CONDENSING_BOILER",
    "gas non-condensing boiler": "GAS_NON_CONDENSING_BOILER",
    "led": "LED",
    "central air conditioning": "CENTRAL_AIR_CONDITIONING",
    "low temperature boiler": "LOW_TEMPERATURE_BOILER",
    "electric flow heater": "ELECTRIC_FLOW_HEATER",
    "room air conditioning": "ROOM_AIR_CONDITIONING",
    "central exhaust": "CENTRAL_EXHAUST",
    "gas floor heating": "GAS_FLOOR_HEATING",
    "central supply exhaust with hru": "CENTRAL_SUPPLY_EXHAUST_WITH_HRU",
    "central supply exhaust without hru": "CENTRAL_SUPPLY_EXHAUST_WITHOUT_HRU",
    "fluorescent lamps": "FLUORESCENT_LAMPS",
    "air water heat pump": "ELECTRIC_HEAT_PUMP_AIR",
    "oil condensing boiler": "CONDENSING_BOILER",
    "electric immersion heater": "ELECTRIC_IMMERSION_HEATER",
    "coal furnace": "COAL_FURNACE",
    "decentral single room ventilation units without hru": "DECENTRAL_SINGLE_ROOM_VENTILATION_UNITS_WITHOUT_HRU",
    "decentral single room ventilation units with hru": "DECENTRAL_SINGLE_ROOM_VENTILATION_UNITS_WITH_HRU",
    "wood furnace": "WOOD_FURNACE",
    # Aliases from the app UI's own translations (en.json) -- other export vintages/tools
    "district heating (from chp)": "DISTRICT_HEATING_WITH_KWK",
    "district heating (from heating plants)": "DISTRICT_HEATING_WITHOUT_KWK",
    "air-source heat pump": "ELECTRIC_HEAT_PUMP_AIR",
    "ground-source heat pump": "ELECTRIC_HEAT_PUMP_GEO",
    "electric instantaneous water heater": "ELECTRIC_FLOW_HEATER",
    "direct electric heating": "DIRECT_ELECTRICITY_HEATING",
    "standard boiler": "STANDARD_BOILER",
    "oil furnace": "OIL_FURNACE",
    "gas room heater": "GAS_ROOM_HEATER",
    "wood boiler": "WOOD_BOILER",
    "small electric storage": "SMALL_ELECTRIC_STORAGE",
    "central electric storage": "CENTRAL_ELECTRIC_STORAGE",
    "solar plant": "SOLAR_PLANT",
    "reversible air water heat pump": "REVERSIBLE_AIR_WATER_HEAT_PUMP",
    "reversible brine water heat pump": "REVERSIBLE_BRINE_WATER_HEAT_PUMP",
    "halogen lamps": "HALOGEN_LAMPS",
}

# energy_system_type -- only HEATING and HOT_WATER are covered by the sanity-check
# rule engine; everything else (Lighting, Electricity/Other, Cooling, Ventilation,
# Photovoltaic, General) is out of scope and should be shown as such, not flagged.
SYSTEM_LABEL_TO_ENUM = {
    "heating": "HEATING",
    "hot water": "HOT_WATER",
    "cooling": "COOLING",
    "electricity": "ELECTRICITY",
    "other": "ELECTRICITY",
    "lighting": "LIGHTING",
    "photovoltaic": "SOLAR",
    "solar": "SOLAR",
    "ventilation": "VENTILATION",
    "general": "GENERAL",
}
IN_SCOPE_SYSTEMS = {"HEATING", "HOT_WATER"}

# "Letzte Anpassung" / "Last adjustment" -- who/what last set this value.
# 'Own' = the user manually entered/edited it.
# 'TABULA' = produced by the TABULA reference-building approximation.
# 'Predium' = produced by Predium's own non-TABULA default logic (e.g. the static
#             new-construction defaults). Both TABULA and Predium are automatic /
#             non-user assignments, so both map to APPROXIMATED for the
#             impossible-via-approximation check.
LAST_ADJUSTMENT_TO_DATASOURCE = {
    "own": "MANUAL",
    "tabula": "APPROXIMATED",
    "predium": "APPROXIMATED",
}


def _normalize(label) -> str:
    if label is None:
        return ""
    return str(label).strip().lower()


def map_source_label(label: str | None) -> str | None:
    if not label:
        return None
    key = _normalize(label)
    if key in SOURCE_LABEL_TO_ENUM:
        return SOURCE_LABEL_TO_ENUM[key]
    # fall back to treating it as already being an enum code
    return str(label).strip().upper().replace(" ", "_")


def map_tech_label(label: str | None) -> str | None:
    if not label:
        return None
    key = _normalize(label)
    if key in TECH_LABEL_TO_ENUM:
        return TECH_LABEL_TO_ENUM[key]
    return str(label).strip().upper().replace(" ", "_").replace("-", "_")


def map_system_label(label: str | None) -> str | None:
    if not label:
        return None
    key = _normalize(label)
    if key in SYSTEM_LABEL_TO_ENUM:
        return SYSTEM_LABEL_TO_ENUM[key]
    return str(label).strip().upper().replace(" ", "_")


def map_data_source_label(label: str | None) -> str | None:
    if not label:
        return None
    key = _normalize(label)
    return LAST_ADJUSTMENT_TO_DATASOURCE.get(key)


COUNTRY_NAME_TO_CODE = {
    "germany": "DE", "austria": "AT", "france": "FR", "poland": "PL",
    "united kingdom": "UK", "czech republic": "CZ", "czechia": "CZ", "belgium": "BE",
}


def map_country_label(label: str | None) -> str:
    """Real Predium exports put the full country name (e.g. 'Germany') in the
    country column, not an ISO code -- naively truncating to the first two
    letters gives 'GE', not 'DE'. Map known names explicitly; fall back to
    truncation only for values that already look like a code."""
    if not label:
        return "DE"
    key = _normalize(label)
    if key in COUNTRY_NAME_TO_CODE:
        return COUNTRY_NAME_TO_CODE[key]
    return str(label).strip().upper()[:2]
