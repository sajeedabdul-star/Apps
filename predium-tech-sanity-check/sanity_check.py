"""
The verdict engine: given one building's technology record (system, source, technology,
plus whatever year/flag data is available), returns a severity and a list of plain-
English reasons -- the same logic whether called once from the single-combination form
or thousands of times over an uploaded export.
"""

from dataclasses import dataclass, field

from rules import RULES_BY_TECH


@dataclass
class Verdict:
    severity: str  # "None" / "Low" / "Medium" / "High"
    reasons: list[str] = field(default_factory=list)
    assumed_system_year: int | None = None
    matched_rule: str | None = None


SEVERITY_ORDER = {"None": 0, "Low": 1, "Medium": 2, "High": 3}


def _bump(current: str, new: str) -> str:
    return new if SEVERITY_ORDER[new] > SEVERITY_ORDER[current] else current


def check_combination(
    system: str,
    source: str,
    technology: str,
    country: str = "DE",
    building_type: str = "RESIDENTIAL",
    building_year_constructed: int | None = None,
    consumer_construction_year: int | None = None,
    year_renovated: int | None = None,
    monument_protection: bool = False,
    is_new_construction: bool = False,
    data_source: str | None = None,  # e.g. "MANUAL", "APPROXIMATED", "IMPORT"
    route_energy_final: float | None = None,  # kWh/m2a, for the low-capacity-auxiliary check
) -> Verdict:
    system = (system or "").strip().upper()
    source = (source or "").strip().upper()
    technology = (technology or "").strip().upper()

    rule = RULES_BY_TECH.get(technology)

    # ---- Unknown technology entirely
    if rule is None:
        return Verdict(
            severity="High",
            reasons=[f"'{technology}' is not a technology Predium's rules recognize at all -- check for a typo "
                     f"or an unmapped enum value."],
        )

    reasons: list[str] = []
    severity = "None"

    # ---- Invalid pairing: system not valid for this technology
    if rule.systems and system not in rule.systems:
        return Verdict(
            severity="High",
            reasons=[f"'{technology}' is not a valid technology for system '{system}' per Predium's own "
                     f"compatibility rules (valid systems: {', '.join(rule.systems) or 'none'})."],
            matched_rule=rule.tech,
        )
    if not rule.systems:
        reasons.append(
            "This technology is not tied to Heating or Hot Water in Predium's current UI at all -- its mere "
            "presence under any system type is anomalous."
        )
        severity = _bump(severity, "High")

    # ---- Invalid pairing: source not valid for this technology
    if source and source not in rule.sources:
        return Verdict(
            severity="High",
            reasons=[f"'{source}' is not a valid energy source for '{technology}' per Predium's own "
                     f"compatibility rules (valid sources: {', '.join(rule.sources)})."],
            matched_rule=rule.tech,
        )

    reasons.append(f"Realistic in practice: {rule.realistic_label}.")
    reasons.append(f"Predium approximation behavior: {rule.approx_label}.")
    severity = _bump(severity, rule.base_severity)

    # ---- Impossibility via approximation, scoped by country/building type
    is_approximated = (data_source or "").strip().upper() in {"APPROXIMATED", "APPROXIMATION", "AUTO"}
    scope = rule.absent_scope
    impossible_here = False
    if scope == "ALL":
        impossible_here = True
    elif scope == "DE_RESIDENTIAL" and country == "DE" and building_type == "RESIDENTIAL":
        impossible_here = True
    elif scope == "DE" and country == "DE":
        impossible_here = True

    if impossible_here:
        if is_approximated:
            reasons.append(
                "IMPOSSIBLE: this combination cannot be produced by Predium's automatic approximation for this "
                "country/building type -- yet the record is flagged as approximated. This points to a bug or a "
                "bad import, not a legacy building."
            )
            severity = "High"
        else:
            reasons.append(
                "This combination never occurs in Predium's own approximation reference data for this "
                "country/building type -- if the source is manual entry or import, that's expected, but the "
                "technology/era pairing is still worth a closer look."
            )
            severity = _bump(severity, "Medium")

    # ---- Monument-protection exception (e.g. coal furnace surviving in a historic building)
    if rule.monument_exception and impossible_here and monument_protection:
        reasons.append(
            "Monument-protection flag is set -- historic/protected buildings are legally exempt from many GEG "
            "modernization mandates, so a surviving legacy system here is less suspicious than the base rule "
            "suggests. Downgrading."
        )
        severity = "Medium" if severity == "High" else severity

    # ---- Low-capacity auxiliary exception (e.g. small supplementary direct-electric route)
    if rule.low_capacity_exception and route_energy_final is not None and route_energy_final <= 5.0:
        reasons.append(
            "route_energy_final is <= 5 kWh/m2a -- this looks like a small auxiliary/supplementary route rather "
            "than the building's main heating system, which is a legitimate, still-installed-today use case. "
            "Downgrading."
        )
        severity = "Low"

    # ---- New-construction sanity check for legacy technologies
    if is_new_construction and rule.base_severity in ("Medium", "High") and rule.as_found_max_year is not None:
        reasons.append(
            "Building is flagged as new construction, but this technology is a legacy-era technology -- this "
            "pairing is very unlikely and worth checking."
        )
        severity = "High"

    # ---- Year-based era check
    assumed_year = consumer_construction_year or year_renovated or building_year_constructed
    year_is_fallback_to_building_year = (
        assumed_year is not None
        and consumer_construction_year is None
        and year_renovated is None
        and building_year_constructed is not None
    )
    if assumed_year is not None and (rule.as_found_min_year is not None or rule.as_found_max_year is not None):
        too_early = rule.as_found_min_year is not None and assumed_year < rule.as_found_min_year
        too_late = rule.as_found_max_year is not None and assumed_year > rule.as_found_max_year
        if too_early:
            reasons.append(
                f"Assumed system year {assumed_year} is before this technology's real-world era started "
                f"(~{rule.as_found_min_year}) -- this predates when the technology existed."
            )
            if year_is_fallback_to_building_year:
                reasons.append(
                    "Note: no system-specific install year was on file, so this falls back to the building's "
                    "construction year -- if the real system was installed later (e.g. a retrofit), this flag "
                    "is a data-gap artifact, not necessarily a real error. Check whether 'Verbraucher Einbaujahr' "
                    "/ the system's own construction year is simply missing before treating this as confirmed."
                )
            severity = "High"
        elif too_late:
            renovation_covers_it = (
                (consumer_construction_year is not None and consumer_construction_year <= (rule.as_found_max_year or 9999))
                or (year_renovated is not None and year_renovated <= (rule.as_found_max_year or 9999))
            )
            if not renovation_covers_it:
                reasons.append(
                    f"Assumed system year {assumed_year} is after this technology's typical era "
                    f"(~{rule.as_found_max_year}), and no renovation/system-replacement record explains it."
                )
                severity = _bump(severity, "Medium" if severity != "High" else "High")

    return Verdict(severity=severity, reasons=reasons, assumed_system_year=assumed_year, matched_rule=rule.tech)
