from __future__ import annotations

from collections import defaultdict

from .config import CONTINENTS
from .loaders import ensure_population_loaded, load_country_map
from .store import COUNTRY_TO_CONTINENT, POPULATION_YEARLY, STORE

HOW_TO_SUM = {
    "temperature": "mean",
    "precipitation": "mean",
    "co2": "sum",
}


# megadja egy hely melyik kontinenshez tartozik
def continent_of(entity):
    if entity in {"Oceania", "Oceania (NIAID)"}:
        return "Australia and Oceania"
    if entity in CONTINENTS:
        return entity
    load_country_map()
    mapped = COUNTRY_TO_CONTINENT.get(entity)
    if mapped == "Oceania":
        return "Australia and Oceania"
    return mapped


# kontinens szintre osszevonja az eves adatokat
def aggregate_yearly(metric, year):
    yearly = STORE.yearly[metric]
    mode = HOW_TO_SUM.get(metric, "mean")
    sums = defaultdict(float)
    counts = defaultdict(int)
    for entity, vals in yearly.items():
        if year not in vals:
            continue
        continent = continent_of(entity)
        if not continent or continent == "World":
            continue
        sums[continent] += vals[year]
        counts[continent] += 1
    out = {}
    for continent, total in sums.items():
        if mode == "sum":
            out[continent] = total
        else:
            count = counts.get(continent, 1)
            out[continent] = total / count if count else total
    return out


# vilag szintet szamol a kontinens adatokbol
def aggregate_world(metric, year):
    yearly = STORE.yearly[metric]
    mode = HOW_TO_SUM.get(metric, "mean")
    values = []
    for entity, series in yearly.items():
        if year in series:
            if continent_of(entity) in CONTINENTS and entity != "World":
                values.append(series[year])
    if not values:
        return None
    if mode == "sum":
        return sum(values)
    return sum(values) / len(values)


# a kert evhez legkozelebbi korabbi erteket adja
def nearest_year_value(series, year):
    if not series:
        return None
    if year in series:
        return series[year]
    candidates = [y for y in series.keys() if y <= year]
    if not candidates:
        return None
    return series[max(candidates)]


# kontinens nepesseget szamol a kert evre
def aggregate_population_continent(continent, year):
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


# vilag nepesseget szamol a kert evre
def aggregate_population_world(year):
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


# co2 ertekbol egy fore juto erteket szamol
def co2_per_capita(entity, year):
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
