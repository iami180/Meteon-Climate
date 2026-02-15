from flask import Flask, jsonify, render_template, request

import threading

from service.data_service import (
    co2_overview_with_per_capita,
    default_compare_year,
    default_year,
    map_response,
    meta_response,
    metric_entity_response,
    metric_year_response,
    overview_response,
    refresh_data,
    warm_cache_all,
    warmest_year_global,
)

app = Flask(__name__)

# Warm all datasets in background to reduce first-load latency.
threading.Thread(target=warm_cache_all, daemon=True).start()

def _safe_int(value, fallback):
    if value in (None, ""):
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/attekintes")
def attekintes():
    return render_template("attekintes.html")

@app.get("/foldfelmelegedes")
def foldfelmelegedes():
    return render_template("foldfelmelegedes.html")


@app.get("/homerseklet")
def homerseklet():
    return render_template("homerseklet.html")


@app.get("/csapadek")
def csapadek():
    return render_template("csapadek.html")


@app.get("/co2")
def co2():
    return render_template("co2.html")

@app.get("/co2-kalkulator")
def co2_kalkulator():
    return render_template("co2_kalkulator.html")


@app.get("/terkep")
def terkep():
    return render_template("terkep.html")


@app.get("/adatok")
def adatok():
    return render_template("overview.html")


@app.get("/api/meta")
def api_meta():
    metric = request.args.get("metric")
    return jsonify(meta_response(metric))


@app.get("/api/overview")
def api_overview():
    metric = request.args.get("metric", "temperature")
    year = _safe_int(request.args.get("year"), default_year(metric))
    compare = _safe_int(request.args.get("compare"), default_compare_year())
    payload, err = overview_response(metric, year, compare)
    return jsonify(payload), 400 if err else 200


@app.get("/api/metric/year")
def api_metric_year():
    metric = request.args.get("metric", "temperature")
    year = _safe_int(request.args.get("year"), default_year(metric))
    payload, err = metric_year_response(metric, year)
    return jsonify(payload), 400 if err else 200


@app.get("/api/metric/entity")
def api_metric_entity():
    metric = request.args.get("metric", "temperature")
    entity = request.args.get("entity", "World")
    year = _safe_int(request.args.get("year"), default_year(metric))
    payload, err = metric_entity_response(metric, entity, year)
    return jsonify(payload), 400 if err else 200


@app.get("/api/map")
def api_map():
    metric = request.args.get("metric", "temperature")
    year = _safe_int(request.args.get("year"), default_year(metric))
    payload, err = map_response(metric, year)
    return jsonify(payload), 400 if err else 200


@app.get("/api/temperature/overview")
def api_temperature_overview():
    year = _safe_int(request.args.get("year"), default_year("temperature"))
    compare = _safe_int(request.args.get("compare"), default_compare_year())
    payload, err = overview_response("temperature", year, compare)
    return jsonify(payload), 400 if err else 200


@app.get("/api/temperature/continents")
def api_temperature_continents():
    year = _safe_int(request.args.get("year"), default_year("temperature"))
    payload, err = metric_year_response("temperature", year, continents_only=True)
    return jsonify(payload), 400 if err else 200


@app.get("/api/temperature/monthly")
def api_temperature_monthly():
    entity = request.args.get("entity", "World")
    year = _safe_int(request.args.get("year"), default_year("temperature"))
    payload, err = metric_entity_response("temperature", entity, year)
    return jsonify(payload), 400 if err else 200


@app.get("/api/temperature/warmest")
def api_temperature_warmest():
    return jsonify(warmest_year_global())


@app.get("/api/precipitation/overview")
def api_precipitation_overview():
    year = _safe_int(request.args.get("year"), default_year("precipitation"))
    compare = _safe_int(request.args.get("compare"), default_compare_year())
    payload, err = overview_response("precipitation", year, compare)
    return jsonify(payload), 400 if err else 200


@app.get("/api/precipitation/continents")
def api_precipitation_continents():
    year = _safe_int(request.args.get("year"), default_year("precipitation"))
    payload, err = metric_year_response("precipitation", year, continents_only=True)
    return jsonify(payload), 400 if err else 200


@app.get("/api/precipitation/monthly")
def api_precipitation_monthly():
    entity = request.args.get("entity", "World")
    year = _safe_int(request.args.get("year"), default_year("precipitation"))
    payload, err = metric_entity_response("precipitation", entity, year)
    return jsonify(payload), 400 if err else 200


@app.get("/api/co2/overview")
def api_co2_overview():
    year = _safe_int(request.args.get("year"), default_year("co2"))
    compare = _safe_int(request.args.get("compare"), default_compare_year())
    entity = request.args.get("entity", "World")
    payload, err = co2_overview_with_per_capita(year, compare, entity)
    return jsonify(payload), 400 if err else 200


@app.get("/api/co2/continents")
def api_co2_continents():
    year = _safe_int(request.args.get("year"), default_year("co2"))
    payload, err = metric_year_response("co2", year, continents_only=True)
    return jsonify(payload), 400 if err else 200


@app.get("/api/co2/monthly")
def api_co2_monthly():
    entity = request.args.get("entity", "World")
    year = _safe_int(request.args.get("year"), default_year("co2"))
    payload, err = metric_entity_response("co2", entity, year)
    return jsonify(payload), 400 if err else 200


@app.post("/admin/refresh")
def admin_refresh():
    result = refresh_data()
    status = 200 if result.get("status") == "ok" else 207
    return jsonify(result), status


if __name__ == "__main__":
    app.run(debug=True)
