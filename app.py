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


@app.get("/")
# a kezdo oldalt rendereli
def index():
    return render_template("index.html")


@app.get("/favicon.ico")
# a bongeszo ikon fajlt kuldi vissza
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon")


@app.get("/attekintes")
# az attekintes oldalt nyitja meg
def attekintes():
    return render_template("attekintes.html")

@app.get("/attekintes/<int:initial_year>/<int:initial_compare>")
# attekintes oldal, url-bol kapott kezdo evekkel
def attekintes_seo(initial_year, initial_compare):
    return render_template(
        "attekintes.html",
        initial_year=initial_year,
        initial_compare=initial_compare,
    )

@app.get("/foldfelmelegedes")
# a foldfelmelegedes oldalt nyitja melegedes nezetben
def foldfelmelegedes():
    return render_template(
        "foldfelmelegedes.html",
        page_mode="warming",
        seo_base_path="/foldfelmelegedes/felmelegedes",
    )

@app.get("/foldfelmelegedes/felmelegedes")
# a melegedes nezetet rendereli
def foldfelmelegedes_felmelegedes():
    return render_template(
        "foldfelmelegedes.html",
        page_mode="warming",
        seo_base_path="/foldfelmelegedes/felmelegedes",
    )

@app.get("/foldfelmelegedes/elorejelzes")
# az elorejelzes nezetet rendereli
def foldfelmelegedes_elorejelzes():
    return render_template(
        "foldfelmelegedes.html",
        page_mode="forecast",
        seo_base_path="/foldfelmelegedes/elorejelzes",
    )

@app.get("/felmelegedes")
# regi utvonal, atdob a melegedes oldalra
def felmelegedes_alias():
    return render_template(
        "foldfelmelegedes.html",
        page_mode="warming",
        seo_base_path="/foldfelmelegedes/felmelegedes",
    )

@app.get("/elorejelzes")
# regi utvonal, atdob az elorejelzes oldalra
def elorejelzes_alias():
    return render_template(
        "foldfelmelegedes.html",
        page_mode="forecast",
        seo_base_path="/foldfelmelegedes/elorejelzes",
    )

@app.get("/foldfelmelegedes/felmelegedes/<int:initial_start>/<int:initial_end>")
# melegedes oldal url-bol kapott kezdovel
def foldfelmelegedes_felmelegedes_seo(initial_start, initial_end):
    return render_template(
        "foldfelmelegedes.html",
        initial_start=initial_start,
        initial_end=initial_end,
        page_mode="warming",
        seo_base_path="/foldfelmelegedes/felmelegedes",
    )

@app.get("/felmelegedes/<int:initial_start>/<int:initial_end>")
# regi seo utvonal a melegedes oldalhoz
def felmelegedes_alias_seo(initial_start, initial_end):
    return render_template(
        "foldfelmelegedes.html",
        initial_start=initial_start,
        initial_end=initial_end,
        page_mode="warming",
        seo_base_path="/foldfelmelegedes/felmelegedes",
    )


@app.get("/homerseklet")
# a homerseklet oldalt nyitja meg
def homerseklet():
    return render_template("homerseklet.html")

@app.get("/homerseklet/<int:initial_year>")
@app.get("/homerseklet/<int:initial_year>/<initial_entity_slug>")
# homerseklet oldal url parameterekkel
def homerseklet_seo(initial_year, initial_entity_slug=None):
    return render_template(
        "homerseklet.html",
        initial_year=initial_year,
        initial_entity_slug=initial_entity_slug,
    )


@app.get("/csapadek")
# a csapadek oldalt nyitja meg
def csapadek():
    return render_template("csapadek.html")

@app.get("/csapadek/<int:initial_year>/<initial_entity_slug>")
# csapadek oldal url parameterekkel
def csapadek_seo(initial_year, initial_entity_slug):
    return render_template(
        "csapadek.html",
        initial_year=initial_year,
        initial_entity_slug=initial_entity_slug,
    )


@app.get("/co2")
# a co2 oldalt nyitja meg
def co2():
    return render_template("co2.html")

@app.get("/co2/<int:initial_year>/<initial_entity_slug>")
# co2 oldal url parameterekkel
def co2_seo(initial_year, initial_entity_slug):
    return render_template(
        "co2.html",
        initial_year=initial_year,
        initial_entity_slug=initial_entity_slug,
    )

@app.get("/co2-kalkulator")
# a co2 kalkulator oldalt nyitja meg
def co2_kalkulator():
    return render_template("co2_kalkulator.html")


@app.get("/terkep")
# a terkep oldalt nyitja meg
def terkep():
    return render_template("terkep.html")

@app.get("/terkep/<initial_metric>/<int:initial_year>")
# terkep oldal url-bol kapott metrikaval es evvel
def terkep_seo(initial_metric, initial_year):
    return render_template(
        "terkep.html",
        initial_metric=initial_metric,
        initial_year=initial_year,
    )


@app.get("/adatok")
# az adatok osszefoglalo oldalt nyitja meg
def adatok():
    return render_template("overview.html")


@app.get("/api/meta")
# meta adatokat ad vissza a valasztott metrikahoz
def api_meta():
    metric = request.args.get("metric")
    return jsonify(meta_response(metric))


@app.get("/api/overview")
# osszefoglalo adatokat ad vissza ev es osszehasonlitas alapjan
def api_overview():
    metric = request.args.get("metric", "temperature")
    year = parse_int(request.args.get("year"), default_year(metric))
    compare = parse_int(request.args.get("compare"), default_compare_year())
    payload, err = overview_response(metric, year, compare)
    return jsonify(payload), 400 if err else 200


@app.get("/api/metric/year")
# egy metrika eves listajat adja vissza
def api_metric_year():
    metric = request.args.get("metric", "temperature")
    year = parse_int(request.args.get("year"), default_year(metric))
    payload, err = metric_year_response(metric, year)
    return jsonify(payload), 400 if err else 200
  

@app.get("/api/metric/entity")
# egy metrika adatait adja vissza egy helyre
def api_metric_entity():
    metric = request.args.get("metric", "temperature")
    entity = request.args.get("entity", "World")
    year = parse_int(request.args.get("year"), default_year(metric))
    payload, err = metric_entity_response(metric, entity, year)
    return jsonify(payload), 400 if err else 200


@app.get("/api/map")
# terkephez valo orszag adatokat ad vissza
def api_map():
    metric = request.args.get("metric", "temperature")
    year = parse_int(request.args.get("year"), default_year(metric))
    payload, err = map_response(metric, year)
    return jsonify(payload), 400 if err else 200


@app.get("/api/temperature/overview")
# homerseklet osszefoglalo adatokat ad
def api_temperature_overview():
    year = parse_int(request.args.get("year"), default_year("temperature"))
    compare = parse_int(request.args.get("compare"), default_compare_year())
    payload, err = overview_response("temperature", year, compare)
    return jsonify(payload), 400 if err else 200


@app.get("/api/temperature/continents")
# homerseklet adatokat ad kontinens bontasban
def api_temperature_continents():
    year = parse_int(request.args.get("year"), default_year("temperature"))
    payload, err = metric_year_response("temperature", year, continents_only=True)
    return jsonify(payload), 400 if err else 200


@app.get("/api/temperature/monthly")
# homerseklet havi adatokat ad egy helyre
def api_temperature_monthly():
    entity = request.args.get("entity", "World")
    year = parse_int(request.args.get("year"), default_year("temperature"))
    payload, err = metric_entity_response("temperature", entity, year)
    return jsonify(payload), 400 if err else 200


@app.get("/api/temperature/warmest")
# visszaadja melyik ev volt a legmelegebb globalisan
def api_temperature_warmest():
    return jsonify(warmest_year_global())


@app.get("/api/temperature/forecast")
# homerseklet elorejelzes valaszt ad
def api_temperature_forecast():
    payload, err = forecast_response()
    return jsonify(payload), 400 if err else 200


@app.get("/api/precipitation/overview")
# csapadek osszefoglalo adatokat ad
def api_precipitation_overview():
    year = parse_int(request.args.get("year"), default_year("precipitation"))
    compare = parse_int(request.args.get("compare"), default_compare_year())
    payload, err = overview_response("precipitation", year, compare)
    return jsonify(payload), 400 if err else 200


@app.get("/api/precipitation/continents")
# csapadek adatokat ad kontinens bontasban
def api_precipitation_continents():
    year = parse_int(request.args.get("year"), default_year("precipitation"))
    payload, err = metric_year_response("precipitation", year, continents_only=True)
    return jsonify(payload), 400 if err else 200


@app.get("/api/precipitation/monthly")
# csapadek havi adatokat ad egy helyre
def api_precipitation_monthly():
    entity = request.args.get("entity", "World")
    year = parse_int(request.args.get("year"), default_year("precipitation"))
    payload, err = metric_entity_response("precipitation", entity, year)
    return jsonify(payload), 400 if err else 200


@app.get("/api/co2/overview")
# co2 osszefoglalo adatokat ad plusz per capita adattal
def api_co2_overview():
    year = parse_int(request.args.get("year"), default_year("co2"))
    compare = parse_int(request.args.get("compare"), default_compare_year())
    entity = request.args.get("entity", "World")
    payload, err = co2_overview_with_per_capita(year, compare, entity)
    return jsonify(payload), 400 if err else 200


@app.get("/api/co2/continents")
# co2 adatokat ad kontinens bontasban
def api_co2_continents():
    year = parse_int(request.args.get("year"), default_year("co2"))
    payload, err = metric_year_response("co2", year, continents_only=True)
    return jsonify(payload), 400 if err else 200


@app.get("/api/co2/monthly")
# co2 havi adatokat ad egy helyre
def api_co2_monthly():
    entity = request.args.get("entity", "World")
    year = parse_int(request.args.get("year"), default_year("co2"))
    payload, err = metric_entity_response("co2", entity, year)
    return jsonify(payload), 400 if err else 200


@app.post("/admin/refresh")
# kezileg ujratolti a nyers adatokat
def admin_refresh():
    result = refresh_data()
    status = 200 if result.get("status") == "ok" else 207
    return jsonify(result), status


if __name__ == "__main__":
    app.run(debug=True)
