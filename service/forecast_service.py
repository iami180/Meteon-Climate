from __future__ import annotations

import math
import random
from dataclasses import dataclass
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

from .aggregations import aggregate_world
from .loaders import ensure_metric_loaded
from .store import STORE


BASELINE_START = 1850
BASELINE_END = 1900
FALLBACK_BASELINE_START = 1951
FALLBACK_BASELINE_END = 1980
TRAIN_START = 1950
TRAIN_END = 2000
TARGET_YEAR = 2050
F2X = 3.7  # itt egy fix szam, co2 duplazodashoz hasznaljuk
PREINDUSTRIAL_OFFSET_FROM_1951_1980 = 0.32


@dataclass(frozen=True)
class ModelParams:
    ecs: float
    kappa: float
    cs: float
    co: float
    sulfate_scale: float
    bc_scale: float
    enso_amp: float


@dataclass(frozen=True)
class ScenarioConfig:
    key: str
    name: str
    co2_growth: float
    ch4_growth: float
    n2o_growth: float
    sulfate_drift: float
    bc_drift: float
    uncertainty_extra: float


SCENARIOS: Tuple[ScenarioConfig, ...] = (
    ScenarioConfig("low", "Alacsony kibocsatas", 1.1, 1.8, 0.55, -0.012, -0.01, 0.02),
    ScenarioConfig("medium", "Kozepes kibocsatas", 1.9, 4.0, 0.8, -0.008, -0.002, 0.05),
    ScenarioConfig("high", "Magas kibocsatas", 3.6, 9.4, 1.3, -0.011, 0.012, 0.1),
)


# a vilag homerseklet idősorát adja
def _world_temperature_series() -> Dict[int, float]:
    ensure_metric_loaded("temperature")
    yearly = STORE.yearly.get("temperature", {})
    world = yearly.get("World", {})
    if world:
        series = dict(world)
        world_monthly = STORE.monthly.get("temperature", {}).get("World", {})
        for y, months in list(world_monthly.items()):
            valid = [m for m in months if isinstance(m, float) and m == m]
            if len(valid) < 12 and y in series:
                del series[y]
        return series
    series: Dict[int, float] = {}
    for year in STORE.years.get("temperature", []):
        value = aggregate_world("temperature", year)
        if value is not None:
            series[year] = value
    return series


# a vilag co2 idosorat adja egységesitve
def _world_co2_emissions_series() -> Dict[int, float]:
    ensure_metric_loaded("co2")
    yearly = STORE.yearly.get("co2", {})
    world = yearly.get("World", {})
    if world:
        out: Dict[int, float] = {}
        for y, v in world.items():
            val = float(v)
            if abs(val) > 10000:
                val /= 1_000_000_000.0
            out[y] = val
        return out
    series: Dict[int, float] = {}
    for year in STORE.years.get("co2", []):
        value = aggregate_world("co2", year)
        if value is not None:
            val = float(value)
            if abs(val) > 10000:
                val /= 1_000_000_000.0
            series[year] = val
    return series


# kiszamolja az alapidoszak atlagat
def _baseline_value(series: Dict[int, float]) -> Tuple[Optional[float], str, float]:
    vals = [v for y, v in series.items() if BASELINE_START <= y <= BASELINE_END]
    if vals:
        return mean(vals), f"{BASELINE_START}-{BASELINE_END}", 0.0

    vals = [v for y, v in series.items() if FALLBACK_BASELINE_START <= y <= FALLBACK_BASELINE_END]
    if vals:
        return mean(vals), f"{FALLBACK_BASELINE_START}-{FALLBACK_BASELINE_END}", PREINDUSTRIAL_OFFSET_FROM_1951_1980

    years = sorted(series.keys())
    if len(years) >= 30:
        return mean(series[y] for y in years[:30]), f"{years[0]}-{years[29]}", PREINDUSTRIAL_OFFSET_FROM_1951_1980
    if years:
        return mean(series[y] for y in years), f"{years[0]}-{years[-1]}", PREINDUSTRIAL_OFFSET_FROM_1951_1980
    return None, "n/a", 0.0


# kibocsatasbol becsult koncentracios idosort epít
def _build_concentration_history(years: List[int], co2_emissions: Dict[int, float]) -> Dict[str, Dict[int, float]]:
    co2_ppm: Dict[int, float] = {}
    ch4_ppb: Dict[int, float] = {}
    n2o_ppb: Dict[int, float] = {}

    c = 285.0
    m = 820.0
    n = 273.0
    for year in years:
        emissions = float(co2_emissions.get(year, co2_emissions.get(year - 1, 0.0)))
        delta_ppm = (0.46 * emissions / 7.81) - (0.011 * max(0.0, c - 285.0))
        c = max(260.0, c + delta_ppm)

        m += max(0.0, 0.7 + 0.035 * delta_ppm - 0.006 * (m - 1900.0))
        n += max(0.0, 0.12 + 0.0035 * delta_ppm - 0.0018 * (n - 335.0))

        co2_ppm[year] = c
        ch4_ppb[year] = m
        n2o_ppb[year] = n
    return {"co2": co2_ppm, "ch4": ch4_ppb, "n2o": n2o_ppb}


# co2 ch4 es n2o sugarzasi hatasat szamolja
def _forcing_components(co2_ppm: float, ch4_ppb: float, n2o_ppb: float) -> Dict[str, float]:
    co2_forcing = 5.35 * math.log(max(co2_ppm, 1.0) / 278.0)

    ch4_forcing = 0.036 * (math.sqrt(max(ch4_ppb, 1.0)) - math.sqrt(722.0))
    n2o_forcing = 0.12 * (math.sqrt(max(n2o_ppb, 1.0)) - math.sqrt(270.0))
    return {"co2": co2_forcing, "ch4": ch4_forcing, "n2o": n2o_forcing}


# egyszeru enso jellegu oszcillaciot ad
def _enso_proxy(year: int, amp: float) -> float:
    return amp * math.sin((2.0 * math.pi * (year - 1950) / 4.1) + 0.7)


# aeroszol indexeket szamol az adott evre
def _aerosol_indices(year: int, co2_emissions: Dict[int, float]) -> Tuple[float, float]:
    emissions = co2_emissions.get(year, co2_emissions.get(year - 1, 0.0))
    ref = max(co2_emissions.get(1990, 1.0), 1.0)
    industrial = min(2.2, max(0.0, emissions / ref))
    cleanup = max(0.0, (year - 1990) / 70.0)

    sulfate_idx = max(0.2, industrial * (1.0 - 0.45 * cleanup))
    bc_idx = max(0.15, industrial * (0.75 - 0.25 * cleanup))
    return sulfate_idx, bc_idx


# lefuttatja a homerseklet modellt evrol evre
def _run_temperature_model(
    years: List[int],
    conc: Dict[str, Dict[int, float]],
    co2_emissions: Dict[int, float],
    params: ModelParams,
    start_temp: float,
) -> Dict[int, float]:
    lam = F2X / params.ecs
    ts = start_temp
    to = start_temp * 0.7
    out: Dict[int, float] = {}

    for year in years:
        forc = _forcing_components(conc["co2"][year], conc["ch4"][year], conc["n2o"][year])
        sulfate_idx, bc_idx = _aerosol_indices(year, co2_emissions)
        aerosol_forcing = (params.sulfate_scale * sulfate_idx) + (params.bc_scale * bc_idx)
        net_forcing = forc["co2"] + forc["ch4"] + forc["n2o"] + aerosol_forcing

        # ket reteget lepunk egyszerre: felszin (ts) es melyebb ocean (to)
        ts += (net_forcing - lam * ts - params.kappa * (ts - to)) / params.cs + _enso_proxy(year, params.enso_amp)
        to += (params.kappa * (ts - to)) / params.co
        out[year] = ts
    return out


# kiszamolja az rmse hibamerteket
def _rmse(y_true: List[float], y_pred: List[float]) -> float:
    if not y_true:
        return float("inf")
    err = sum((a - b) ** 2 for a, b in zip(y_true, y_pred)) / len(y_true)
    return math.sqrt(err)


# kiszamolja a mae hibamerteket
def _mae(y_true: List[float], y_pred: List[float]) -> float:
    if not y_true:
        return float("inf")
    return sum(abs(a - b) for a, b in zip(y_true, y_pred)) / len(y_true)


# becsult tcr erteket szamol egyszeru kiserlettel
def _simulate_tcr(params: ModelParams) -> float:
    lam = F2X / params.ecs
    ts = 0.0
    to = 0.0
    co2 = 278.0
    for _ in range(70):
        co2 *= 1.01
        forcing = 5.35 * math.log(co2 / 278.0)
        ts += (forcing - lam * ts - params.kappa * (ts - to)) / params.cs
        to += (params.kappa * (ts - to)) / params.co
    return ts


# a modell parametereit hangolja a mult adataihoz
def _calibrate_params(
    years: List[int], anomaly: Dict[int, float], conc: Dict[str, Dict[int, float]], co2_emissions: Dict[int, float]
) -> Tuple[ModelParams, Dict[str, float]]:
    train_years = [y for y in years if TRAIN_START <= y <= TRAIN_END and y in anomaly]
    test_years = [y for y in years if y > TRAIN_END and y in anomaly]

    best: Optional[ModelParams] = None
    best_score = float("inf")
    best_pred: Optional[Dict[int, float]] = None

    ecs_grid = [2.5, 2.8, 3.1, 3.4, 3.7, 4.0]
    kappa_grid = [0.45, 0.6, 0.75]
    cs_grid = [7.0, 8.5, 10.0]
    sulfate_grid = [-0.75, -0.6, -0.45]
    bc_grid = [0.08, 0.12, 0.16]
    enso_grid = [0.04, 0.06, 0.08]

    start_year = years[0]
    start_temp = anomaly.get(start_year, 0.0)
    # brute force: sok parameter kombinaciot vegigprobalunk
    for ecs in ecs_grid:
        for kappa in kappa_grid:
            for cs in cs_grid:
                for sf in sulfate_grid:
                    for bc in bc_grid:
                        for enso in enso_grid:
                            params = ModelParams(
                                ecs=ecs,
                                kappa=kappa,
                                cs=cs,
                                co=110.0,
                                sulfate_scale=sf,
                                bc_scale=bc,
                                enso_amp=enso,
                            )
                            pred = _run_temperature_model(years, conc, co2_emissions, params, start_temp=start_temp)
                            y_train_true = [anomaly[y] for y in train_years]
                            y_train_pred = [pred[y] for y in train_years]
                            train_rmse = _rmse(y_train_true, y_train_pred)

                            tcr = _simulate_tcr(params)
                            tcr_penalty = 0.0
                            # ha a tcr nagyon kilog, buntetest kap a score
                            if tcr < 1.5:
                                tcr_penalty = (1.5 - tcr) * 2.5
                            elif tcr > 2.2:
                                tcr_penalty = (tcr - 2.2) * 2.5

                            score = train_rmse + tcr_penalty
                            if score < best_score:
                                best_score = score
                                best = params
                                best_pred = pred

    if best is None or best_pred is None:
        best = ModelParams(3.0, 0.6, 8.5, 110.0, -0.6, 0.12, 0.06)
        best_pred = _run_temperature_model(years, conc, co2_emissions, best, start_temp=anomaly.get(start_year, 0.0))

    y_test_true = [anomaly[y] for y in test_years]
    y_test_pred = [best_pred[y] for y in test_years]
    metrics = {
        "train_rmse": round(_rmse([anomaly[y] for y in train_years], [best_pred[y] for y in train_years]), 3),
        "test_rmse": round(_rmse(y_test_true, y_test_pred), 3),
        "test_mae": round(_mae(y_test_true, y_test_pred), 3),
        "test_start_year": test_years[0] if test_years else None,
        "test_end_year": test_years[-1] if test_years else None,
        "ecs": round(best.ecs, 3),
        "tcr": round(_simulate_tcr(best), 3),
    }
    return best, metrics


# kategoriat ad az anomalia merteke alapjan
def _classify_anomaly(value: float) -> str:
    if value < 1.5:
        return "mersekelt melegedes"
    if value < 2.0:
        return "jelentos melegedes"
    if value < 3.0:
        return "magas kockazatu melegedes"
    return "kritikus melegedes"


# percentilis erteket szamol rendezett listabol
def _percentile(sorted_values: List[float], p: float) -> float:
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = p * (len(sorted_values) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return sorted_values[lo]
    frac = idx - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


# egy forgatokonyv jovobeli palyajat szamolja
def _project_scenario(
    scenario: ScenarioConfig,
    base_params: ModelParams,
    current_year: int,
    current_temp: float,
    co2_now: float,
    ch4_now: float,
    n2o_now: float,
    co2_emissions_ref: Dict[int, float],
    draws: int = 220,
) -> Dict[str, Any]:
    years = list(range(current_year, TARGET_YEAR + 1))
    rng = random.Random(42 + hash(scenario.key) % 1000)

    all_draws: List[Dict[int, float]] = []
    for _ in range(draws):
        # minden futasban picit randomizaljuk a parametereket (monte carlo)
        ecs = min(4.2, max(2.4, rng.gauss(base_params.ecs, 0.35)))
        kappa = min(0.95, max(0.35, rng.gauss(base_params.kappa, 0.08)))
        cs = min(12.0, max(6.0, rng.gauss(base_params.cs, 0.9)))
        sulfate_scale = rng.uniform(-0.95, -0.3)
        bc_scale = rng.uniform(0.05, 0.2)
        enso_amp = max(0.02, rng.gauss(base_params.enso_amp, 0.02))
        params = ModelParams(ecs, kappa, cs, base_params.co, sulfate_scale, bc_scale, enso_amp)

        co2 = co2_now
        ch4 = ch4_now
        n2o = n2o_now
        ts = current_temp
        to = current_temp * 0.7
        lam = F2X / params.ecs
        path: Dict[int, float] = {}
        for year in years:
            if year > current_year:
                co2 += scenario.co2_growth + rng.uniform(-0.25, 0.25)
                ch4 += scenario.ch4_growth + rng.uniform(-1.0, 1.0)
                n2o += scenario.n2o_growth + rng.uniform(-0.08, 0.08)

            forc = _forcing_components(co2, ch4, n2o)
            sulfate_idx, bc_idx = _aerosol_indices(year, co2_emissions_ref)
            sulfate_idx = max(0.1, sulfate_idx + ((year - current_year) * scenario.sulfate_drift))
            bc_idx = max(0.08, bc_idx + ((year - current_year) * scenario.bc_drift))
            aerosol_forcing = (params.sulfate_scale * sulfate_idx) + (params.bc_scale * bc_idx)
            net_forcing = forc["co2"] + forc["ch4"] + forc["n2o"] + aerosol_forcing
            ts += (net_forcing - lam * ts - params.kappa * (ts - to)) / params.cs + _enso_proxy(year, params.enso_amp)
            to += (params.kappa * (ts - to)) / params.co
            path[year] = ts
        all_draws.append(path)

    series: List[Dict[str, Any]] = []
    for year in years:
        # sok futasbol percentilis savot csinalunk (p10-p50-p90)
        vals = sorted(draw[year] for draw in all_draws)
        p10 = _percentile(vals, 0.1)
        p50 = _percentile(vals, 0.5)
        p90 = _percentile(vals, 0.9)
        spread = scenario.uncertainty_extra
        series.append(
            {
                "year": year,
                "value": round(p50, 3),
                "min": round(p10 - spread, 3),
                "max": round(p90 + spread, 3),
            }
        )

    # segedfuggveny: egy konkret cel-ev sorat adja vissza
    def pick(target: int) -> Dict[str, Any]:
        row = next((r for r in series if r["year"] == target), series[-1])
        return {
            "year": row["year"],
            "value": row["value"],
            "min": row["min"],
            "max": row["max"],
            "category": _classify_anomaly(row["value"]),
        }

    return {
        "id": scenario.key,
        "name": scenario.name,
        "series": series,
        "year_2030": pick(2030),
        "year_2050": pick(2050),
        "aerosol_uncertainty": {
            "sulfate_forcing_wm2": [-0.95, -0.3],
            "black_carbon_forcing_wm2": [0.05, 0.2],
        },
    }


# osszerakja a teljes elorejelzes api valaszt
def forecast_response() -> Tuple[Dict[str, Any], Optional[str]]:
    temp_series = _world_temperature_series()
    if not temp_series:
        return {"error": "Temperature data not available"}, "Temperature data not available"

    emissions_series = _world_co2_emissions_series()
    years = sorted(temp_series.keys())
    baseline, baseline_period, baseline_offset = _baseline_value(temp_series)
    if baseline is None:
        return {"error": "Baseline not available"}, "Baseline not available"

    anomaly = {y: (temp_series[y] - baseline) + baseline_offset for y in years}
    conc = _build_concentration_history(years, emissions_series)
    params, backtest = _calibrate_params(years, anomaly, conc, emissions_series)

    current_year = years[-1]
    current_temp = anomaly[current_year]
    co2_now = conc["co2"][current_year]
    ch4_now = conc["ch4"][current_year]
    n2o_now = conc["n2o"][current_year]

    scenarios = [
        _project_scenario(
            scenario=sc,
            base_params=params,
            current_year=current_year,
            current_temp=current_temp,
            co2_now=co2_now,
            ch4_now=ch4_now,
            n2o_now=n2o_now,
            co2_emissions_ref=emissions_series,
        )
        for sc in SCENARIOS
    ]

    historical = [{"year": y, "value": round(anomaly[y], 3)} for y in years if y >= max(1900, current_year - 80)]
    return (
        {
            "target": "Globalis atlagos felszini homerseklet anomalia (C)",
            "baseline_period": baseline_period,
            "baseline_adjustment_c": round(baseline_offset, 3),
            "time_resolution": "eves atlag",
            "current_year": current_year,
            "current_anomaly": round(current_temp, 3),
            "historical": historical,
            "scenarios": scenarios,
            "inputs": {
                "ghg": ["CO2 (ppm)", "CH4 (ppb)", "N2O (ppb)"],
                "forcing_formula": "CO2: dF = 5.35 * ln(C/C0), CH4/N2O: sqrt alapu kozelites",
                "aerosol_proxy": ["szulfat index", "black carbon index"],
                "ocean_component": "ketrekeszes energiaegyensuly modell (felszin + melyocean)",
                "enso_component": "ENSO jellegu periodikus komponens",
            },
            "calibration": {
                "ecs_c": backtest["ecs"],
                "tcr_c": backtest["tcr"],
                "ecs_target_range_c": [2.5, 4.0],
                "tcr_target_range_c": [1.5, 2.2],
            },
            "backtest": backtest,
            "notes": [
                "Kalibracio: 1950-2000, validacio/backtest: 2001-tol napjainkig.",
                "Aeroszol bizonytalansag Monte Carlo mintazassal kerult a tartomanyba.",
                "Szcenario keszlet: alacsony, kozepes, magas kibocsatasi palya.",
            ],
        },
        None,
    )
