"""
Single source of truth for the sanity-check rule engine.

Derived from Predium's own compatibility code:
  libs/lookup/client-lookup/src/lib/EnergyUnitCompatibility/SourceTypesForTechnologyType.ts
  libs/lookup/client-lookup/src/lib/EnergyUnitCompatibility/TechnologyTypesForSystemType.ts
plus real query results from Predium's local reference-building dataset:
  apps/backend/src/modules/reference-buildings/services/reference_buildings.db
plus live legal research on the GEG -> GModG reform (24 Aug 2026) for the technologies
whose real-world status changed with it.

If Predium changes an enum value or compatibility rule, update TECH_RULES here --
this is the only place the rule set is defined; the app and any lookup exports
are generated from it.

source_tier on each rule is honest about how firm the era claim is:
  "db_verified"      -- both which technologies are impossible/rare AND the numeric year
                         bound come directly from querying reference_buildings.db.
  "db_scope_only"     -- the DB confirms the impossibility/rarity, but the specific
                         numeric year bound is a domain-knowledge estimate (the DB never
                         shows this technology as an "as-found" baseline at all, so it has
                         no opinion on exactly which years are plausible).
  "code_only"         -- no era claim is made at all; only Predium's compatibility code
                         (valid sources/systems) backs this rule.
gmodg_note flags rules whose real-world-status text was corrected by the July 2026
GEG -> GModG reform research.
"""

from dataclasses import dataclass, field


@dataclass
class TechRule:
    tech: str
    sources: list[str]
    systems: list[str]  # subset of {"HEATING", "HOT_WATER"}
    realistic_label: str
    approx_label: str
    as_found_min_year: int | None  # None = never an as-found baseline
    as_found_max_year: int | None
    absent_scope: str | None  # None, "ALL", "DE_RESIDENTIAL", "DE" (country-wide)
    base_severity: str  # "Low" / "Medium" / "High"
    action: str
    source_tier: str = "code_only"  # "db_verified" / "db_scope_only" / "code_only"
    gmodg_note: bool = False
    monument_exception: bool = False  # e.g. COAL_FURNACE on a protected building
    low_capacity_exception: bool = False  # e.g. DIRECT_ELECTRICITY_HEATING auxiliary route


SOURCE_TIER_LABEL = {
    "db_verified": "Predium reference DB (exact)",
    "db_scope_only": "Predium DB (rarity) + domain estimate (era)",
    "code_only": "Predium compatibility code only",
}


TECH_RULES: list[TechRule] = [
    TechRule(
        tech="GAS_CONDENSING_BOILER",
        sources=["NATURAL_GAS", "BIO_GAS", "LPG"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Standard today, freely available for new installs",
        approx_label="As-found baseline, ANY era (Predium's default guess)",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope=None, base_severity="Low",
        source_tier="db_verified", gmodg_note=True,
        action="No action needed on the pairing alone. The GEG's 65%-renewable mandate for new heating systems "
               "was fully repealed by the GModG (Gebaeudemodernisierungsgesetz, in force since 29 July 2026) -- "
               "a brand-new gas-only install needs no hybrid/renewable pairing today. A 'Bio-Treppe' fuel-blend "
               "quota applies to newly installed fossil boilers from 2029 onward (10% rising to 60% by 2040), "
               "but that is a fuel-supply-contract question the technology/source pairing itself can't reveal, "
               "not something to flag from this data alone.",
    ),
    TechRule(
        tech="GAS_NON_CONDENSING_BOILER",
        sources=["NATURAL_GAS", "BIO_GAS", "LPG"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Legacy only (pre-2015 Brennwertpflicht)",
        approx_label="Retrofit-option only (consumption-matched), never as-found",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope=None, base_severity="Medium",
        source_tier="code_only",
        action="Flag if the assumed system year is 2015 or later, or the building is flagged as new construction. "
               "(Note: the 2015 threshold is a documented regulatory fact -- the Brennwertpflicht -- not "
               "something the DB or the code enforces numerically today; the base Medium severity carries this "
               "instead of a hard year check.)",
    ),
    TechRule(
        tech="GAS_ROOM_HEATER",
        sources=["NATURAL_GAS", "BIO_GAS", "LPG"],
        systems=["HEATING"],
        realistic_label="Niche/rare, older apartment stock",
        approx_label="NEVER in Predium's reference dataset (any country/building type)",
        as_found_min_year=1950, as_found_max_year=2005,
        absent_scope="ALL", base_severity="Medium",
        source_tier="db_scope_only",
        action="If the record came from automatic approximation, this is IMPOSSIBLE -- investigate immediately. "
               "If manually entered or imported, verify the system year is plausibly pre-2005.",
    ),
    TechRule(
        tech="GAS_FLOOR_HEATING",
        sources=["NATURAL_GAS", "BIO_GAS", "LPG"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Modeling nuance -- distribution method, not a distinct appliance",
        approx_label="Retrofit-option only, rare",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope=None, base_severity="Medium",
        source_tier="code_only",
        action="Verify the actual underlying boiler generation feeding this distribution system rather than "
               "treating it as a standalone appliance.",
    ),
    TechRule(
        tech="GAS_FLOW_HEATER",
        sources=["NATURAL_GAS", "BIO_GAS", "LPG"],
        systems=["HOT_WATER"],
        realistic_label="Common today, ongoing",
        approx_label="Retrofit-option only (consumption-matched)",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope=None, base_severity="Low",
        source_tier="code_only",
        action="No action needed.",
    ),
    TechRule(
        tech="STANDARD_BOILER",
        sources=["FUEL_OIL"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Legacy only (~1950-1978)",
        approx_label="NEVER in Predium's reference dataset (any country/building type)",
        as_found_min_year=1950, as_found_max_year=1990,
        absent_scope="ALL", base_severity="Medium",
        source_tier="db_scope_only",
        action="If approximated, IMPOSSIBLE -- investigate. If manual/import, verify the system year is "
               "plausibly pre-1990.",
    ),
    TechRule(
        tech="OIL_FURNACE",
        sources=["FUEL_OIL"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Legacy only (~1950-1980)",
        approx_label="NEVER in Predium's reference dataset (any country/building type)",
        as_found_min_year=1950, as_found_max_year=1995,
        absent_scope="ALL", base_severity="Medium",
        source_tier="db_scope_only",
        action="If approximated, IMPOSSIBLE -- investigate. If manual/import, verify the system year is "
               "plausibly pre-1995.",
    ),
    TechRule(
        tech="CONDENSING_BOILER",  # oil condensing
        sources=["FUEL_OIL"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Standard oil-heating technology since the 1990s, freely available again for new installs",
        approx_label="Retrofit-option only (consumption-matched)",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope=None, base_severity="Low",
        source_tier="code_only", gmodg_note=True,
        action="No action needed for years 2026 onward -- the GModG (29 July 2026) repealed the 65%-renewable "
               "mandate, so new oil-only installs are legal again with no hybrid pairing required. There WAS a "
               "genuine ~2-year window (2024 through 28 July 2026, under the prior GEG 2024 'Heizungsgesetz') "
               "where a pure new oil-only install could have been non-compliant -- only flag if the assumed "
               "system year falls specifically in that window AND no hybrid/renewable pairing is documented. "
               "A further fuel-blend quota ('Bio-Treppe') applies to newly installed fossil boilers from 2029 "
               "onward, but that's a fuel-supply-contract question, not a technology/source mismatch.",
    ),
    TechRule(
        tech="LOW_TEMPERATURE_BOILER",
        sources=["FUEL_OIL", "NATURAL_GAS"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Legacy only (~1978-2000)",
        approx_label="As-found baseline through construction period 1984-1994 only; also a retrofit-option any era",
        as_found_min_year=None, as_found_max_year=1994,
        absent_scope=None, base_severity="Medium",
        source_tier="db_verified",
        action="Flag if the assumed system year is 2015 or later, or earlier than 1970.",
    ),
    TechRule(
        tech="COAL_FURNACE",
        sources=["COAL", "LIGNITE"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Rare, legacy-only, actively phased out",
        approx_label="NEVER for RESIDENTIAL buildings (only DE non-residential, era 0-1948)",
        as_found_min_year=None, as_found_max_year=1960,
        absent_scope="DE_RESIDENTIAL", base_severity="Medium",
        source_tier="db_scope_only",
        action="On a residential building: if approximated, IMPOSSIBLE. On any building, check monument-"
               "protection status before treating as an error -- historic buildings occasionally retain "
               "original coal-era heating.",
        monument_exception=True,
    ),
    TechRule(
        tech="WOOD_BOILER",
        sources=["WOOD", "WOODEN_PELLETS"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Common, growing (pellet boilers) -- one of several freely available options under "
                         "GModG's technology-freedom framework, still subsidized via BEG",
        approx_label="Retrofit-option only, any era",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope=None, base_severity="Low",
        source_tier="code_only", gmodg_note=True,
        action="No action needed.",
    ),
    TechRule(
        tech="WOOD_FURNACE",
        sources=["WOOD", "WOODEN_PELLETS"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Traditional, rural single-family",
        approx_label="NEVER for German RESIDENTIAL (only DE non-res. pre-1918, or FR residential 1982-1999)",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope="DE_RESIDENTIAL", base_severity="Medium",
        source_tier="db_verified",
        action="On a German residential building: if approximated, IMPOSSIBLE -- investigate.",
    ),
    TechRule(
        tech="DISTRICT_HEATING_WITH_KWK",
        sources=["DISTRICT_HEATING_CHP_RENEWABLE", "DISTRICT_HEATING_CHP_FOSSIL_GAS", "DISTRICT_HEATING_CHP_FOSSIL_COAL"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Very common, dominant urban Fernwaerme",
        approx_label="As-found baseline mostly seen 2010+ in the (thin) reference sample; also a retrofit-option "
                     "any era. Real-world CHP district heating networks predate this by decades -- not a "
                     "genuine constraint, so no year check is applied.",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope=None, base_severity="Low",
        source_tier="code_only",
        action="Not a construction-year issue -- scrutinize only if the building sits outside a known "
               "Fernwaerme network coverage area, not by year.",
    ),
    TechRule(
        tech="DISTRICT_HEATING_WITHOUT_KWK",
        sources=["DISTRICT_HEATING_PLANTS_FOSSIL_COAL", "DISTRICT_HEATING_PLANTS_FOSSIL_GAS", "DISTRICT_HEATING_PLANTS_RENEWABLE"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Common, Nahwaerme networks",
        approx_label="Retrofit-option only (consumption-matched)",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope=None, base_severity="Low",
        source_tier="code_only",
        action="Same as with-KWK variant -- check grid coverage, not construction year.",
    ),
    TechRule(
        tech="ELECTRIC_HEAT_PUMP_AIR",
        sources=["ELECTRICITY_MIX", "ELECTRICITY_GREEN", "SOLAR"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Dominant new-build technology, rapidly growing",
        approx_label="Retrofit-option only (consumption-matched)",
        as_found_min_year=2010, as_found_max_year=None,
        absent_scope=None, base_severity="Medium",
        source_tier="db_scope_only",
        action="Flag if the assumed system year is before 2010 with no renovation record at or after 2010. "
               "First check whether the system's own construction year is simply unpopulated and defaulting "
               "to the building's construction year.",
    ),
    TechRule(
        tech="ELECTRIC_HEAT_PUMP_GEO",
        sources=["ELECTRICITY_MIX", "ELECTRICITY_GREEN", "SOLAR"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Niche but real, steady growth",
        approx_label="Retrofit-option only (consumption-matched)",
        as_found_min_year=1995, as_found_max_year=None,
        absent_scope=None, base_severity="Medium",
        source_tier="db_scope_only",
        action="Flag if the assumed system year is before 1995 with no renovation record.",
    ),
    TechRule(
        tech="DIRECT_ELECTRICITY_HEATING",
        sources=["ELECTRICITY_MIX", "ELECTRICITY_GREEN", "SOLAR"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Legacy only (~1950-1985)",
        approx_label="NEVER for GERMANY (only modeled for French residential, 1982-2005)",
        as_found_min_year=1950, as_found_max_year=1985,
        absent_scope="DE", base_severity="Medium",
        source_tier="db_scope_only",
        action="On a German building: if approximated, IMPOSSIBLE. Also check whether this is a low-capacity "
               "auxiliary route before flagging it as the main heating system.",
        low_capacity_exception=True,
    ),
    TechRule(
        tech="CENTRAL_ELECTRIC_STORAGE",
        sources=["ELECTRICITY_MIX", "ELECTRICITY_GREEN", "SOLAR"],
        systems=["HEATING"],
        realistic_label="Legacy only, Nachtspeicherheizung (1965-1995 boom)",
        approx_label="Retrofit-option only (consumption-matched)",
        as_found_min_year=1965, as_found_max_year=1995,
        absent_scope=None, base_severity="High",
        source_tier="db_scope_only",
        action="Flag if the assumed system year is after 2000. Even a correctly-dated 1980s unit may be "
               "subject to a state-level operational shutdown deadline today -- check the building's state, "
               "regardless of year accuracy.",
    ),
    TechRule(
        tech="SMALL_ELECTRIC_STORAGE",
        sources=["ELECTRICITY_MIX", "ELECTRICITY_GREEN", "SOLAR"],
        systems=[],  # not tied to HEATING or HOT_WATER in the current Predium UI at all
        realistic_label="Legacy-era technology (same family as Central Electric Storage)",
        approx_label="NEVER in Predium's reference dataset; not offered under ANY system type in the manual UI",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope="ALL", base_severity="High",
        source_tier="db_verified",
        action="ANY occurrence at all is worth investigating -- cannot originate from manual UI entry for "
               "Heating or Hot Water, and is absent from the approximation reference data too. Verify the "
               "record's import/data-source origin.",
    ),
    TechRule(
        tech="ELECTRIC_IMMERSION_HEATER",
        sources=["ELECTRICITY_MIX", "ELECTRICITY_GREEN", "SOLAR"],
        systems=["HEATING", "HOT_WATER"],
        realistic_label="Legacy-era (~1960-2000), gradually superseded since ~2010",
        approx_label="Retrofit-option only (consumption-matched); NOT offered in the current manual UI",
        as_found_min_year=1960, as_found_max_year=2000,
        absent_scope=None, base_severity="Medium",
        source_tier="db_scope_only",
        action="Confirmed real in Predium's own seed data under both Heating and Hot Water, yet cannot be "
               "freshly assigned via the current UI. Any occurrence is worth tracing via building/import "
               "history rather than treating it purely as a year-based check.",
    ),
    TechRule(
        tech="ELECTRIC_FLOW_HEATER",
        sources=["ELECTRICITY_MIX", "ELECTRICITY_GREEN", "SOLAR"],
        systems=["HOT_WATER"],
        realistic_label="Very common today",
        approx_label="Retrofit-option only (consumption-matched)",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope=None, base_severity="Low",
        source_tier="code_only",
        action="No action needed.",
    ),
    TechRule(
        tech="SOLAR_PLANT",
        sources=["SOLAR"],
        systems=["HOT_WATER", "HEATING"],
        realistic_label="Common and growing (solar thermal for hot water preheating is a classic real-world use)",
        approx_label="As-found baseline ANY era for Hot Water; rare as-found 2010+ only for Heating. NOT "
                     "offered in the manual UI for either system type",
        as_found_min_year=None, as_found_max_year=None,
        absent_scope=None, base_severity="Medium",
        source_tier="db_verified",
        action="If found on a manually-created system, this is a data-model inconsistency -- the manual UI "
               "never offers this technology for Heating or Hot Water. If from approximation, this is "
               "expected and valid.",
    ),
]

RULES_BY_TECH: dict[str, TechRule] = {r.tech: r for r in TECH_RULES}

ALL_TECHNOLOGIES = sorted(RULES_BY_TECH.keys())
ALL_SOURCES = sorted({s for r in TECH_RULES for s in r.sources})
ALL_SYSTEMS = ["HEATING", "HOT_WATER"]


def valid_technologies_for(system: str) -> list[str]:
    return sorted(r.tech for r in TECH_RULES if system in r.systems)


def valid_sources_for(tech: str) -> list[str]:
    rule = RULES_BY_TECH.get(tech)
    return sorted(rule.sources) if rule else []
