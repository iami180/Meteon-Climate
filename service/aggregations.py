from __future__ import annotations

from collections import defaultdict
from typing import Dict, Optional

from .config import CONTINENTS
from .loaders import ensure_population_loaded, load_country_map
from .store import COUNTRY_TO_CONTINENT, POPULATION_YEARLY, STORE

AGGREGATION = {
    "temperature": "mean",
    "precipitation": "mean",
    "co2": "sum",
}


def continent_of(entity: str) -> Optional[str]:
    if entity in {"Oceania", "Oceania (NIAID)"}:
        return "Australia and Oceania"
    if entity in CONTINENTS:
        return entity
    load_country_map()
    mapped = COUNTRY_TO_CONTINENT.get(entity)
    if mapped == "Oceania":
        return "Australia and Oceania"
    return mapped


def aggregate_yearly(metric: str, year: int) -> Dict[str, float]:
    yearly = STORE.yearly[metric]
    aggregation = AGGREGATION.get(metric, "mean")
    sums: Dict[str, float] = defaultdict(float)
    counts: Dict[str, int] = defaultdict(int)
    for entity, values in yearly.items():
        if year not in values:
            continue
        continent = continent_of(entity)
        if not continent or continent == "World":
            continue
        value = values[year]
        sums[continent] += value
        counts[continent] += 1
    result = {}
    for continent, total in sums.items():
        if aggregation == "sum":
            result[continent] = total
        else:
            count = counts.get(continent, 1)
            result[continent] = total / count if count else total
    return result


def aggregate_world(metric: str, year: int) -> Optional[float]:
    yearly = STORE.yearly[metric]
    aggregation = AGGREGATION.get(metric, "mean")
    values = []
    for entity, series in yearly.items():
        if year in series:
            if continent_of(entity) in CONTINENTS and entity != "World":
                values.append(series[year])
    if not values:
        return None
    if aggregation == "sum":
        return sum(values)
    return sum(values) / len(values)


def nearest_year_value(series: Dict[int, float], year: int) -> Optional[float]:
    if not series:
        return None
    if year in series:
        return series[year]
    candidates = [y for y in series.keys() if y <= year]
    if not candidates:
        return None
    return series[max(candidates)]


def aggregate_population_continent(continent: str, year: int) -> Optional[float]:
    ensure_population_loaded()
    direct = POPULATION_YEARLY.get(continent)
    if direct:
        value = nearest_year_value(direct, year)
        if value is not None:
            return value
    un_variant = POPULATION_YEARLY.get(f"{continent} (UN)")
    if un_variant:
        value = nearest_year_value(un_variant, year)
        if value is not None:
            return value
    total = 0.0
    found = False
    for entity, series in POPULATION_YEARLY.items():
        value = nearest_year_value(series, year)
        if value is None:
            continue
        if continent_of(entity) == continent:
            total += value
            found = True
    return total if found else None


def aggregate_population_world(year: int) -> Optional[float]:
    ensure_population_loaded()
    world = POPULATION_YEARLY.get("World")
    if world:
        value = nearest_year_value(world, year)
        if value is not None:
            return value
    total = 0.0
    found = False
    for entity, series in POPULATION_YEARLY.items():
        value = nearest_year_value(series, year)
        if value is None:
            continue
        if continent_of(entity) in CONTINENTS and entity != "World":
            total += value
            found = True
    return total if found else None


def co2_per_capita(entity: str, year: int) -> Optional[float]:
    yearly = STORE.yearly["co2"]
    value = None
    if entity in yearly and year in yearly[entity]:
        value = yearly[entity][year]
    elif entity in CONTINENTS:
        value = aggregate_yearly("co2", year).get(entity)
    elif entity == "World":
        value = aggregate_world("co2", year)
    if value is None:
        return None
    if entity == "World":
        population = aggregate_population_world(year)
    elif entity in CONTINENTS:
        population = aggregate_population_continent(entity, year)
    else:
        ensure_population_loaded()
        population = nearest_year_value(POPULATION_YEARLY.get(entity, {}), year)
    if not population:
        return None
    return value / population
