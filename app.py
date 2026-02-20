from flask import Flask, jsonify, render_template, request, send_from_directory

import threading

from service.data_service import (
    co2_overview_with_per_capita,
    default_compare_year,
    default_year,
    forecast_response,
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

threading.Thread(target=warm_cache_all, daemon=True).start()

# bejovo ertekbol szamot csinal, ha nem jo akkor alap erteket ad
def parse_int(value, fallback):
    if value in (None, ""):
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


# a kezdo oldalt rendereli
@app.get("/")
def index():
    return render_template("index.html")


# a bongeszo ikon fajlt kuldi vissza
@app.get("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon")


# az attekintes oldalt nyitja meg
@app.get("/attekintes")
def attekintes():
    return render_template("attekintes.html")

# attekintes oldal, url-bol kapott kezdo evekkel
@app.get("/attekintes/<int:initial_year>/<int:initial_compare>")
def attekintes_seo(initial_year, initial_compare):
    return render_template(
        "attekintes.html",
        initial_year=initial_year,
        initial_compare=initial_compare,
    )

# a foldfelmelegedes oldalt nyitja melegedes nezetben
@app.get("/foldfelmelegedes")
def foldfelmelegedes():
    return render_template(
        "foldfelmelegedes.html",
        page_mode="warming",
        seo_base_path="/foldfelmelegedes/felmelegedes",
    )

# a melegedes nezetet rendereli
@app.get("/foldfelmelegedes/felmelegedes")
def foldfelmelegedes_felmelegedes():
    return render_template(
        "foldfelmelegedes.html",
        page_mode="warming",
        seo_base_path="/foldfelmelegedes/felmelegedes",
    )

# az elorejelzes nezetet rendereli
@app.get("/foldfelmelegedes/elorejelzes")
def foldfelmelegedes_elorejelzes():
    return render_template(
        "foldfelmelegedes.html",
        page_mode="forecast",
        seo_base_path="/foldfelmelegedes/elorejelzes",
    )

# regi utvonal, atdob a melegedes oldalra
@app.get("/felmelegedes")
def felmelegedes_alias():
    return render_template(
        "foldfelmelegedes.html",
        page_mode="warming",
        seo_base_path="/foldfelmelegedes/felmelegedes",
    )

# regi utvonal, atdob az elorejelzes oldalra
@app.get("/elorejelzes")
def elorejelzes_alias():
    return render_template(
        "foldfelmelegedes.html",
        page_mode="forecast",
        seo_base_path="/foldfelmelegedes/elorejelzes",
    )

# melegedes oldal url-bol kapott kezdovel
@app.get("/foldfelmelegedes/felmelegedes/<int:initial_start>/<int:initial_end>")
def foldfelmelegedes_felmelegedes_seo(initial_start, initial_end):
    return render_template(
        "foldfelmelegedes.html",
        initial_start=initial_start,
        initial_end=initial_end,
        page_mode="warming",
        seo_base_path="/foldfelmelegedes/felmelegedes",
    )

# regi seo utvonal a melegedes oldalhoz
@app.get("/felmelegedes/<int:initial_start>/<int:initial_end>")
def felmelegedes_alias_seo(initial_start, initial_end):
    return render_template(
        "foldfelmelegedes.html",
        initial_start=initial_start,
        initial_end=initial_end,
        page_mode="warming",
        seo_base_path="/foldfelmelegedes/felmelegedes",
    )


# a homerseklet oldalt nyitja meg
@app.get("/homerseklet")
def homerseklet():
    return render_template("homerseklet.html")

# homerseklet oldal url parameterekkel
@app.get("/homerseklet/<int:initial_year>")
@app.get("/homerseklet/<int:initial_year>/<initial_entity_slug>")
def homerseklet_seo(initial_year, initial_entity_slug=None):
    return render_template(
        "homerseklet.html",
        initial_year=initial_year,
        initial_entity_slug=initial_entity_slug,
    )


# a csapadek oldalt nyitja meg
@app.get("/csapadek")
def csapadek():
    return render_template("csapadek.html")

# csapadek oldal url parameterekkel
@app.get("/csapadek/<int:initial_year>/<initial_entity_slug>")
def csapadek_seo(initial_year, initial_entity_slug):
    return render_template(
        "csapadek.html",
        initial_year=initial_year,
        initial_entity_slug=initial_entity_slug,
    )


# a co2 oldalt nyitja meg
@app.get("/co2")
def co2():
    return render_template("co2.html")

# co2 oldal url parameterekkel
@app.get("/co2/<int:initial_year>/<initial_entity_slug>")
def co2_seo(initial_year, initial_entity_slug):
    return render_template(
        "co2.html",
        initial_year=initial_year,
        initial_entity_slug=initial_entity_slug,
    )

# a co2 kalkulator oldalt nyitja meg
@app.get("/co2-kalkulator")
def co2_kalkulator():
    return render_template("co2_kalkulator.html")


# a terkep oldalt nyitja meg
@app.get("/terkep")
def terkep():
    return render_template("terkep.html")

# terkep oldal url-bol kapott metrikaval es evvel
@app.get("/terkep/<initial_metric>/<int:initial_year>")
def terkep_seo(initial_metric, initial_year):
    return render_template(
        "terkep.html",
        initial_metric=initial_metric,
        initial_year=initial_year,
    )


# az adatok osszefoglalo oldalt nyitja meg
@app.get("/adatok")
def adatok():
    return render_template("overview.html")


# meta adatokat ad vissza a valasztott metrikahoz
@app.get("/api/meta")
def api_meta():
    metric = request.args.get("metric")
    return jsonify(meta_response(metric))


# osszefoglalo adatokat ad vissza ev es osszehasonlitas alapjan
@app.get("/api/overview")
def api_overview():
    metric = request.args.get("metric", "temperature")
    year = parse_int(request.args.get("year"), default_year(metric))
    compare = parse_int(request.args.get("compare"), default_compare_year())
    payload, err = overview_response(metric, year, compare)
    return jsonify(payload), 400 if err else 200


# egy metrika eves listajat adja vissza
@app.get("/api/metric/year")
def api_metric_year():
    metric = request.args.get("metric", "temperature")
    year = parse_int(request.args.get("year"), default_year(metric))
    payload, err = metric_year_response(metric, year)
    return jsonify(payload), 400 if err else 200
  

# egy metrika adatait adja vissza egy helyre
@app.get("/api/metric/entity")
def api_metric_entity():
    metric = request.args.get("metric", "temperature")
    entity = request.args.get("entity", "World")
    year = parse_int(request.args.get("year"), default_year(metric))
    payload, err = metric_entity_response(metric, entity, year)
    return jsonify(payload), 400 if err else 200


# terkephez valo orszag adatokat ad vissza
@app.get("/api/map")
def api_map():
    metric = request.args.get("metric", "temperature")
    year = parse_int(request.args.get("year"), default_year(metric))
    payload, err = map_response(metric, year)
    return jsonify(payload), 400 if err else 200


# homerseklet osszefoglalo adatokat ad
@app.get("/api/temperature/overview")
def api_temperature_overview():
    year = parse_int(request.args.get("year"), default_year("temperature"))
    compare = parse_int(request.args.get("compare"), default_compare_year())
    payload, err = overview_response("temperature", year, compare)
    return jsonify(payload), 400 if err else 200


# homerseklet adatokat ad kontinens bontasban
@app.get("/api/temperature/continents")
def api_temperature_continents():
    year = parse_int(request.args.get("year"), default_year("temperature"))
    payload, err = metric_year_response("temperature", year, continents_only=True)
    return jsonify(payload), 400 if err else 200


# homerseklet havi adatokat ad egy helyre
@app.get("/api/temperature/monthly")
def api_temperature_monthly():
    entity = request.args.get("entity", "World")
    year = parse_int(request.args.get("year"), default_year("temperature"))
    payload, err = metric_entity_response("temperature", entity, year)
    return jsonify(payload), 400 if err else 200


# visszaadja melyik ev volt a legmelegebb globalisan
@app.get("/api/temperature/warmest")
def api_temperature_warmest():
    return jsonify(warmest_year_global())


# homerseklet elorejelzes valaszt ad
@app.get("/api/temperature/forecast")
def api_temperature_forecast():
    payload, err = forecast_response()
    return jsonify(payload), 400 if err else 200


# csapadek osszefoglalo adatokat ad
@app.get("/api/precipitation/overview")
def api_precipitation_overview():
    year = parse_int(request.args.get("year"), default_year("precipitation"))
    compare = parse_int(request.args.get("compare"), default_compare_year())
    payload, err = overview_response("precipitation", year, compare)
    return jsonify(payload), 400 if err else 200


# csapadek adatokat ad kontinens bontasban
@app.get("/api/precipitation/continents")
def api_precipitation_continents():
    year = parse_int(request.args.get("year"), default_year("precipitation"))
    payload, err = metric_year_response("precipitation", year, continents_only=True)
    return jsonify(payload), 400 if err else 200


# csapadek havi adatokat ad egy helyre
@app.get("/api/precipitation/monthly")
def api_precipitation_monthly():
    entity = request.args.get("entity", "World")
    year = parse_int(request.args.get("year"), default_year("precipitation"))
    payload, err = metric_entity_response("precipitation", entity, year)
    return jsonify(payload), 400 if err else 200


# co2 osszefoglalo adatokat ad plusz per capita adattal
@app.get("/api/co2/overview")
def api_co2_overview():
    year = parse_int(request.args.get("year"), default_year("co2"))
    compare = parse_int(request.args.get("compare"), default_compare_year())
    entity = request.args.get("entity", "World")
    payload, err = co2_overview_with_per_capita(year, compare, entity)
    return jsonify(payload), 400 if err else 200


# co2 adatokat ad kontinens bontasban
@app.get("/api/co2/continents")
def api_co2_continents():
    year = parse_int(request.args.get("year"), default_year("co2"))
    payload, err = metric_year_response("co2", year, continents_only=True)
    return jsonify(payload), 400 if err else 200


# co2 havi adatokat ad egy helyre
@app.get("/api/co2/monthly")
def api_co2_monthly():
    entity = request.args.get("entity", "World")
    year = parse_int(request.args.get("year"), default_year("co2"))
    payload, err = metric_entity_response("co2", entity, year)
    return jsonify(payload), 400 if err else 200


# kezileg ujratolti a nyers adatokat
@app.post("/admin/refresh")
def admin_refresh():
    result = refresh_data()
    status = 200 if result.get("status") == "ok" else 207
    return jsonify(result), status


if __name__ == "__main__":
    app.run(debug=True)
