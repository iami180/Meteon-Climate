from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .aggregations import aggregate_world, aggregate_yearly, co2_per_capita, continent_of
from .config import CONTINENTS, DEFAULT_COMPARE_YEAR, METRICS
from .loaders import ensure_metric_loaded
from .store import STORE


def validate_metric(metric: str) -> Optional[str]:
    if metric not in METRICS:
        return "Unknown metric"
    ensure_metric_loaded(metric)
    if not STORE.years.get(metric):
        return "Metric not loaded"
    return None


def default_year(metric: str) -> int:
    years = STORE.years.get(metric)
    if years:
        return years[-1]
    return DEFAULT_COMPARE_YEAR


def default_compare_year() -> int:
    return DEFAULT_COMPARE_YEAR


def meta_response(metric: Optional[str] = None) -> Dict[str, Any]:
    if metric and metric in METRICS:
        ensure_metric_loaded(metric)
        metrics = [metric] if STORE.years.get(metric) else []
    else:
        ensure_metric_loaded("temperature")
        metrics = [m for m in METRICS if STORE.years.get(m)]
    years = sorted(set(y for m in metrics for y in STORE.years[m]))
    entities = sorted(set(e for m in metrics for e in STORE.entities[m]))
    continents = sorted(set(c for c in CONTINENTS if c in entities and c != "World"))
    if not entities:
        entities = sorted(CONTINENTS)
    if not continents:
        continents = sorted(c for c in CONTINENTS if c != "World")
    return {
        "metrics": metrics,
        "years": years,
        "entities": entities,
        "continents": continents,
        "last_refresh": STORE.last_refresh,
    }


def overview_response(metric: str, year: int, compare: int) -> Tuple[Dict[str, Any], Optional[str]]:
    err = validate_metric(metric)
    if err:
        return {"error": err}, err

    yearly = STORE.yearly[metric]
    monthly = STORE.monthly[metric]

    if year not in STORE.years[metric]:
        return {"error": "Year not available"}, "Year not available"
    if compare not in STORE.years[metric]:
        compare = STORE.years[metric][0]

    world = yearly.get("World", {})
    selected_val = world.get(year) or aggregate_world(metric, year)
    compare_val = world.get(compare) or aggregate_world(metric, compare)
    delta = None
    if selected_val is not None and compare_val is not None:
        delta = selected_val - compare_val

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

    warmest = max(continents, key=lambda x: x["value"], default=None)
    coldest = min(continents, key=lambda x: x["value"], default=None)

    return (
        {
            "metric": metric,
            "selected_year": year,
            "compare_year": compare,
            "global": {"selected": selected_val, "compare": compare_val, "delta": delta},
            "range": {"value": range_value, "definition": "max(havi atlag) - min(havi atlag)"},
            "continents": continents,
            "rank": {"warmest": warmest, "coldest": coldest},
        },
        None,
    )


def metric_year_response(metric: str, year: int, continents_only: bool = False) -> Tuple[Dict[str, Any], Optional[str]]:
    err = validate_metric(metric)
    if err:
        return {"error": err}, err
    if year not in STORE.years[metric]:
        return {"error": "Year not available"}, "Year not available"
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
    return {"metric": metric, "year": year, "data": data}, None


def metric_entity_response(metric: str, entity: str, year: int) -> Tuple[Dict[str, Any], Optional[str]]:
    err = validate_metric(metric)
    if err:
        return {"error": err}, err
    if year not in STORE.years[metric]:
        return {"error": "Year not available"}, "Year not available"
    months = []
    if entity in STORE.monthly[metric] and year in STORE.monthly[metric][entity]:
        values = STORE.monthly[metric][entity][year]
        for idx, val in enumerate(values, start=1):
            if isinstance(val, float) and val == val:
                months.append({"month": idx, "value": val})
    return {"metric": metric, "entity": entity, "year": year, "months": months}, None


def map_response(metric: str, year: int) -> Tuple[Dict[str, Any], Optional[str]]:
    err = validate_metric(metric)
    if err:
        return {"error": err}, err
    if year not in STORE.years[metric]:
        return {"error": "Year not available"}, "Year not available"

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


def co2_overview_with_per_capita(year: int, compare: int, entity: str) -> Tuple[Dict[str, Any], Optional[str]]:
    payload, err = overview_response("co2", year, compare)
    payload["per_capita"] = co2_per_capita(entity, year)
    payload["entity"] = entity
    return payload, err


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
