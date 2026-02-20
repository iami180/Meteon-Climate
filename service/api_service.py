from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .aggregations import aggregate_world, aggregate_yearly, co2_per_capita, continent_of
from .config import CONTINENTS, DEFAULT_COMPARE_YEAR, METRICS
from .loaders import ensure_metric_loaded
from .store import STORE

PRECIP_MONTHLY_PROFILE = {
    "Europe": [0.07, 0.06, 0.07, 0.08, 0.09, 0.10, 0.10, 0.09, 0.09, 0.09, 0.08, 0.08],
    "Asia": [0.05, 0.05, 0.06, 0.07, 0.09, 0.11, 0.14, 0.13, 0.11, 0.08, 0.06, 0.05],
    "Africa": [0.08, 0.08, 0.09, 0.10, 0.10, 0.09, 0.08, 0.08, 0.08, 0.08, 0.07, 0.07],
    "North America": [0.07, 0.06, 0.07, 0.08, 0.09, 0.10, 0.10, 0.10, 0.09, 0.09, 0.08, 0.07],
    "South America": [0.10, 0.10, 0.10, 0.09, 0.08, 0.07, 0.06, 0.06, 0.07, 0.08, 0.09, 0.10],
    "Australia and Oceania": [0.08, 0.08, 0.09, 0.09, 0.08, 0.08, 0.07, 0.07, 0.08, 0.09, 0.10, 0.09],
    "Antarctica": [0.08, 0.08, 0.09, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.09, 0.08],
}

PRECIP_FALLBACK_ANNUAL_MM = {
    "Antarctica": 166.0,
}

CO2_FALLBACK_ANNUAL_TONS = {
    "Antarctica": 0.0,
}


# ellenorzi hogy a kert metrika ervenyes es be van toltve
def validate_metric(metric: str) -> Optional[str]:
    if metric not in METRICS:
        return "Unknown metric"
    ensure_metric_loaded(metric)
    if not STORE.years.get(metric):
        return "Metric not loaded"
    return None


# a metrika utolso elerheto evet adja vissza
def default_year(metric: str) -> int:
    years = STORE.years.get(metric)
    if years:
        return years[-1]
    return DEFAULT_COMPARE_YEAR


# az alap osszehasonlitasi evet adja
def default_compare_year() -> int:
    return DEFAULT_COMPARE_YEAR


# kivalaszt egy ervenyes evet, ha lehet fallbackgel
def _pick_year(metric: str, year: int) -> Optional[int]:
    years = STORE.years.get(metric, [])
    if not years:
        return None
    if year in years:
        return year
    if metric in {"precipitation", "co2"} and year > years[-1]:
        return years[-1]
    return None


# osszerakja a meta valaszt evekkel es helyekkel
def meta_response(metric: Optional[str] = None) -> Dict[str, Any]:
    if metric and metric in METRICS:
        ensure_metric_loaded(metric)
        metrics = [metric] if STORE.years.get(metric) else []
    else:
        ensure_metric_loaded("temperature")
        metrics = [m for m in METRICS if STORE.years.get(m)]
    years = sorted(set(y for m in metrics for y in STORE.years[m]))
    if metric in {"precipitation", "co2"} and years and years[-1] < 2025:
        years.append(2025)
    entities = sorted(set(e for m in metrics for e in STORE.entities[m]))
    continents = sorted(set(c for c in CONTINENTS if c in entities and c != "World"))
    if not entities:
        entities = sorted(CONTINENTS)
    if not continents:
        continents = sorted(c for c in CONTINENTS if c != "World")
    if metric == "co2" and "Antarctica" not in continents:
        continents.append("Antarctica")
    return {
        "metrics": metrics,
        "years": years,
        "entities": entities,
        "continents": continents,
        "last_refresh": STORE.last_refresh,
    }


# osszefoglalo valaszt epit a metrika adataibol
def overview_response(metric: str, year: int, compare: int) -> Tuple[Dict[str, Any], Optional[str]]:
    err = validate_metric(metric)
    if err:
        return {"error": err}, err

    yearly = STORE.yearly[metric]
    monthly = STORE.monthly[metric]

    ok_year = _pick_year(metric, year)
    if ok_year is None:
        return {"error": "Year not available"}, "Year not available"
    ok_compare = _pick_year(metric, compare)
    if ok_compare is None:
        compare = STORE.years[metric][0]
        ok_compare = compare
    year = ok_year
    compare = ok_compare

    world = yearly.get("World", {})
    now_val = world.get(year) or aggregate_world(metric, year)
    compare_val = world.get(compare) or aggregate_world(metric, compare)
    delta = None
    if now_val is not None and compare_val is not None:
        delta = now_val - compare_val

    range_value = None
    if "World" in monthly and year in monthly["World"]:
        values = [v for v in monthly["World"][year] if isinstance(v, float) and v == v]
        if values:
            range_value = max(values) - min(values)

    continents = []
    for entity in sorted(CONTINENTS):
        if entity == "World":
            continue
        if entity in yearly and year in yearly[entity]:
            continents.append({"name": entity, "value": yearly[entity][year]})
    if not continents:
        aggregated = aggregate_yearly(metric, year)
        continents = [{"name": k, "value": v} for k, v in sorted(aggregated.items())]
    if metric == "precipitation":
        present = {item["name"] for item in continents}
        for entity, fallback in PRECIP_FALLBACK_ANNUAL_MM.items():
            if entity not in present:
                continents.append({"name": entity, "value": fallback})
    if metric == "co2":
        present = {item["name"] for item in continents}
        for entity, fallback in CO2_FALLBACK_ANNUAL_TONS.items():
            if entity not in present:
                continents.append({"name": entity, "value": fallback})

    warmest = max(continents, key=lambda x: x["value"], default=None)
    coldest = min(continents, key=lambda x: x["value"], default=None)

    return (
        {
            "metric": metric,
            "selected_year": year,
            "compare_year": compare,
            "global": {"selected": now_val, "compare": compare_val, "delta": delta},
            "range": {"value": range_value, "definition": "max(havi Ä‚Ë‡tlag) - min(havi Ä‚Ë‡tlag)"},
            "continents": continents,
            "rank": {"warmest": warmest, "coldest": coldest},
        },
        None,
    )


# egy evre ad vissza metrika adatlistat
def metric_year_response(metric: str, year: int, continents_only: bool = False) -> Tuple[Dict[str, Any], Optional[str]]:
    err = validate_metric(metric)
    if err:
        return {"error": err}, err
    ok_year = _pick_year(metric, year)
    if ok_year is None:
        return {"error": "Year not available"}, "Year not available"
    year = ok_year
    yearly = STORE.yearly[metric]
    data = []
    for entity, values in yearly.items():
        if year in values:
            if continents_only and (entity == "World" or entity not in CONTINENTS):
                continue
            data.append({"entity": entity, "value": values[year]})
    if continents_only and not data:
        aggregated = aggregate_yearly(metric, year)
        data = [{"entity": k, "value": v} for k, v in sorted(aggregated.items())]
    if continents_only and metric == "precipitation":
        present = {item["entity"] for item in data}
        for entity, fallback in PRECIP_FALLBACK_ANNUAL_MM.items():
            if entity not in present:
                data.append({"entity": entity, "value": fallback})
    if continents_only and metric == "co2":
        present = {item["entity"] for item in data}
        for entity, fallback in CO2_FALLBACK_ANNUAL_TONS.items():
            if entity not in present:
                data.append({"entity": entity, "value": fallback})
    return {"metric": metric, "year": year, "data": data}, None


# egy hely havi adatait adja vissza
def metric_entity_response(metric: str, entity: str, year: int) -> Tuple[Dict[str, Any], Optional[str]]:
    err = validate_metric(metric)
    if err:
        return {"error": err}, err
    ok_year = _pick_year(metric, year)
    if ok_year is None:
        return {"error": "Year not available"}, "Year not available"
    year = ok_year
    months = []
    estimated = False
    if entity in STORE.monthly[metric] and year in STORE.monthly[metric][entity]:
        values = STORE.monthly[metric][entity][year]
        for idx, val in enumerate(values, start=1):
            if isinstance(val, float) and val == val:
                months.append({"month": idx, "value": val})
    if not months and metric == "precipitation":
        yearly_value = STORE.yearly.get(metric, {}).get(entity, {}).get(year)
        if yearly_value is None:
            yearly_value = aggregate_yearly(metric, year).get(entity)
        if yearly_value is None:
            yearly_value = PRECIP_FALLBACK_ANNUAL_MM.get(entity)
        profile = PRECIP_MONTHLY_PROFILE.get(entity, [1 / 12.0] * 12)
        if yearly_value is not None:
            months = [{"month": i + 1, "value": yearly_value * profile[i]} for i in range(12)]
            estimated = True
    return {"metric": metric, "entity": entity, "year": year, "months": months, "estimated_monthly": estimated}, None


# terkephez valo orszag listat es ertekeket ad
def map_response(metric: str, year: int) -> Tuple[Dict[str, Any], Optional[str]]:
    err = validate_metric(metric)
    if err:
        return {"error": err}, err
    ok_year = _pick_year(metric, year)
    if ok_year is None:
        return {"error": "Year not available"}, "Year not available"
    year = ok_year

    countries = []
    yearly = STORE.yearly[metric]
    for entity, values in yearly.items():
        if entity in CONTINENTS and entity != "Antarctica":
            continue
        if year not in values:
            continue
        code = STORE.entity_codes.get(entity)
        if not code and entity == "Antarctica":
            code = "ATA"
        if not code:
            continue
        region = continent_of(entity)
        countries.append({"name": entity, "code": code, "region": region, "value": values[year]})

    if metric == "co2" and not any(c.get("name") == "Antarctica" for c in countries):
        countries.append({"name": "Antarctica", "code": "ATA", "region": "Antarctica", "value": 0.0})
    if metric == "precipitation" and not any(c.get("name") == "Antarctica" for c in countries):
        countries.append(
            {
                "name": "Antarctica",
                "code": "ATA",
                "region": "Antarctica",
                "value": PRECIP_FALLBACK_ANNUAL_MM.get("Antarctica", 166.0),
            }
        )

    values = [c["value"] for c in countries if c.get("value") is not None]
    non_antarctica = [c["value"] for c in countries if c.get("value") is not None and c.get("region") != "Antarctica"]
    if non_antarctica:
        values = non_antarctica
    min_val = min(values) if values else None
    max_val = max(values) if values else None

    return {
        "metric": metric,
        "year": year,
        "countries": countries,
        "range": {"min": min_val, "max": max_val},
    }, None


# co2 overview valaszhoz hozzaadja az egy fore jutot
def co2_overview_with_per_capita(year: int, compare: int, entity: str) -> Tuple[Dict[str, Any], Optional[str]]:
    payload, err = overview_response("co2", year, compare)
    resolved_year = payload.get("selected_year", year)
    payload["per_capita"] = co2_per_capita(entity, resolved_year)
    payload["entity"] = entity
    return payload, err


# megkeresi a legmelegebb globalis evet
def warmest_year_global() -> Dict[str, Any]:
    ensure_metric_loaded("temperature")
    years = STORE.years.get("temperature", [])
    best_year = None
    best_value = None
    for year in years:
        value = STORE.yearly.get("temperature", {}).get("World", {}).get(year)
        if value is None:
            value = aggregate_world("temperature", year)
        if value is None:
            continue
        if best_value is None or value > best_value:
            best_value = value
            best_year = year
    return {"year": best_year, "value": best_value}
