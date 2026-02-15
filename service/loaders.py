from __future__ import annotations

import csv
import io
import os
from datetime import datetime
from typing import Optional, Tuple

import requests

from .config import CHARTS, CONTINENTS, MAX_YEAR, POPULATION_CHART, RAW_DIR
from .store import (
    COUNTRY_MAP_LOADED,
    COUNTRY_TO_CONTINENT,
    POPULATION_YEARLY,
    POPULATION_YEARS,
    STORE,
    touch_access,
)
from .store import reset_store


def parse_year_month(value: str) -> Tuple[Optional[int], Optional[int]]:
    value = value.strip()
    if not value:
        return None, None
    if value.isdigit() and len(value) == 4:
        return int(value), None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y/%m/%d", "%Y/%m"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.year, dt.month
        except ValueError:
            continue
    try:
        year = int(value[:4])
        month = int(value[5:7]) if len(value) >= 7 and value[4] in "-/" else None
        return year, month
    except Exception:
        return None, None


def download_csv(chart_name: str) -> str:
    url = f"https://ourworldindata.org/grapher/{chart_name}.csv"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def load_csv_text(csv_text: str, metric: str) -> None:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return
    date_col = None
    for candidate in ("Year", "year", "Day", "day", "Date", "date"):
        if candidate in reader.fieldnames:
            date_col = candidate
            break
    if not date_col:
        date_col = reader.fieldnames[2]
    value_col = reader.fieldnames[-1]
    co2_total_col = None
    co2_fossil_col = None
    if metric == "co2":
        if "Total (fossil fuels and land-use change)" in reader.fieldnames:
            co2_total_col = "Total (fossil fuels and land-use change)"
        if "Fossil fuels" in reader.fieldnames:
            co2_fossil_col = "Fossil fuels"
    monthly = STORE.monthly[metric]
    yearly = STORE.yearly[metric]
    for row in reader:
        entity = row.get("Entity") or row.get("entity") or "Unknown"
        code = (row.get("Code") or row.get("code") or "").strip()
        if entity.endswith(" (NIAID)"):
            base = entity.replace(" (NIAID)", "")
            if base in CONTINENTS:
                entity = base
        if len(code) == 3 and code.isalpha():
            STORE.entity_codes.setdefault(entity, code.upper())
        year_raw = row.get(date_col, "") or ""
        if metric == "co2" and co2_total_col:
            value_raw = row.get(co2_total_col, "")
            if value_raw in ("", None) and co2_fossil_col:
                value_raw = row.get(co2_fossil_col, "")
        else:
            value_raw = row.get(value_col, "")
        if value_raw in ("", None):
            continue
        try:
            value = float(value_raw)
        except ValueError:
            continue
        year, month = parse_year_month(str(year_raw))
        if year is None:
            continue
        yearly.setdefault(entity, {})
        monthly.setdefault(entity, {})
        if month is None:
            yearly[entity][year] = value
        else:
            monthly[entity].setdefault(year, [])
            while len(monthly[entity][year]) < month:
                monthly[entity][year].append(float("nan"))
            monthly[entity][year][month - 1] = value


def finalize_yearly_from_monthly(metric: str) -> None:
    monthly = STORE.monthly[metric]
    yearly = STORE.yearly[metric]
    for entity, years in monthly.items():
        for year, values in years.items():
            clean = [v for v in values if isinstance(v, float) and v == v]
            if not clean:
                continue
            yearly.setdefault(entity, {})
            yearly[entity][year] = sum(clean) / len(clean)


def collect_meta(metric: str) -> None:
    yearly = STORE.yearly[metric]
    years = set()
    entities = set()
    for entity, data in yearly.items():
        entities.add(entity)
        years.update(data.keys())
    STORE.years[metric] = sorted(y for y in years if y <= MAX_YEAR)
    STORE.entities[metric] = sorted(entities)


def ensure_metric_loaded(metric: str) -> None:
    touch_access()
    if STORE.years.get(metric):
        return
    raw_path = os.path.join(RAW_DIR, f"{metric}.csv")
    if os.path.exists(raw_path):
        with open(raw_path, "r", encoding="utf-8") as f:
            load_csv_text(f.read(), metric)
        finalize_yearly_from_monthly(metric)
        collect_meta(metric)
        return
    try:
        csv_text = download_csv(CHARTS[metric])
        os.makedirs(RAW_DIR, exist_ok=True)
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(csv_text)
        load_csv_text(csv_text, metric)
        finalize_yearly_from_monthly(metric)
        collect_meta(metric)
    except Exception:
        return


def load_country_map() -> None:
    global COUNTRY_MAP_LOADED
    if COUNTRY_MAP_LOADED:
        return
    try:
        csv_text = download_csv("continents-according-to-our-world-in-data")
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            country = row.get("Entity")
            continent = row.get("World region according to OWID")
            if not country or not continent:
                continue
            COUNTRY_TO_CONTINENT[country] = continent
    except Exception:
        pass
    COUNTRY_MAP_LOADED = True


def ensure_population_loaded() -> None:
    touch_access()
    if POPULATION_YEARS:
        return
    raw_path = os.path.join(RAW_DIR, "population.csv")
    try:
        if os.path.exists(raw_path):
            with open(raw_path, "r", encoding="utf-8") as f:
                csv_text = f.read()
        else:
            csv_text = download_csv(POPULATION_CHART)
            os.makedirs(RAW_DIR, exist_ok=True)
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(csv_text)
        reader = csv.DictReader(io.StringIO(csv_text))
        if not reader.fieldnames:
            return
        value_col = reader.fieldnames[-1]
        for row in reader:
            entity = row.get("Entity") or row.get("entity") or "Unknown"
            year_raw = row.get("Year") or row.get("year") or ""
            value_raw = row.get(value_col, "")
            if value_raw in ("", None):
                continue
            try:
                value = float(value_raw)
            except ValueError:
                continue
            year, _ = parse_year_month(str(year_raw))
            if year is None or year > MAX_YEAR or year < 1800:
                continue
            POPULATION_YEARLY[entity][year] = value
            POPULATION_YEARS.add(year)
    except Exception:
        return


def refresh_data() -> dict:
    os.makedirs(RAW_DIR, exist_ok=True)
    reset_store()
    errors = {}
    for metric, chart in CHARTS.items():
        try:
            csv_text = download_csv(chart)
            raw_path = os.path.join(RAW_DIR, f"{metric}.csv")
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(csv_text)
            load_csv_text(csv_text, metric)
            finalize_yearly_from_monthly(metric)
            collect_meta(metric)
        except Exception as exc:
            errors[metric] = str(exc)
    STORE.last_refresh = datetime.utcnow().timestamp()
    return {"status": "ok" if not errors else "partial", "errors": errors}


def load_from_cache_if_exists() -> None:
    reset_store()
    loaded_any = False
    for metric in CHARTS.keys():
        raw_path = os.path.join(RAW_DIR, f"{metric}.csv")
        if os.path.exists(raw_path):
            with open(raw_path, "r", encoding="utf-8") as f:
                load_csv_text(f.read(), metric)
            finalize_yearly_from_monthly(metric)
            collect_meta(metric)
            loaded_any = True
    if not loaded_any:
        refresh_data()


def warm_cache_all() -> None:
    for metric in CHARTS.keys():
        ensure_metric_loaded(metric)
    ensure_population_loaded()
