# Backend koncepcio (ClimateScope)

## Cel
A backend egységes JSON API-t szolgaltat az eves/havi klima adatokhoz (homerseklet, csapadek, CO2), es kezeli az evvalasztast + ev-osszehasonlitast. A frontend csak a sajat backend API-t hivja.

## Architekturak
- Data Source Layer: kulso adatok letoltese es frissitese (OWID, opcionalis NASA/Open-Meteo)
- API Layer: gyors, memoriabol kiszolgalando endpointok

## 1) Kulso adatforrasok
### A) Elsodleges (MVP): Our World in Data (OWID) "grapher" CSV/JSON
- Sajat backend indulaskor letolti: `https://ourworldindata.org/grapher/CHART_NAME.csv`
- Feldolgozas utan memoria indexeles, majd innen API valasz
- A frontend nem hivja kozvetlenul az OWID-t

### B) Opcionalsan emlitheto forrasok
- NASA POWER: koordinata-alapu, kontinens atlaghoz tobb pont kell
- Open-Meteo Historical: reanalizis, szinten koordinata-alapu
- MVP-ben csak OWID, kesobb bovithetoseg

## 2) Adatkezeles (Load once, serve fast)
Indulasakor:
1. CSV letoltes vagy helyi cache olvasasa
2. Feldolgozas (havi -> eves mutatok)
3. Indexeles memoriaba

Javasolt strukturak:
```
monthly[metric][entity][year] -> [12 ertek]
yearly[metric][entity][year]  -> eves atlag
precomputed_overview[metric][year] -> dashboard csomag (opcionalis)
```

Szamitott mutatok:
- `annual_avg = mean(month_values)`
- `annual_range = max(month_values) - min(month_values)`
- `warmest_month = argmax(month_values)`
- `coldest_month = argmin(month_values)`

## 3) API specifikacio
### 3.1 Meta
`GET /api/meta`

Valasz pelda:
```json
{
  "metrics": ["temperature", "precipitation", "co2"],
  "years": [1950, 1951, 1952, 2025],
  "entities": ["World","Europe","Asia","Africa","North America","South America","Oceania"]
}
```

### 3.2 Attekintes (dashboard)
`GET /api/overview?metric=temperature&year=2023&compare=1980`

Valasz pelda:
```json
{
  "metric": "temperature",
  "selected_year": 2023,
  "compare_year": 1980,
  "global": {"selected": 15.6, "compare": 14.2, "delta": 1.4},
  "range": {"value": 6.8, "definition": "max(havi atlag) - min(havi atlag)"},
  "continents": [
    {"name":"Europe","value":10.7},
    {"name":"Asia","value":16.1},
    {"name":"Africa","value":24.3},
    {"name":"North America","value":9.8},
    {"name":"South America","value":22.1},
    {"name":"Oceania","value":18.4}
  ],
  "rank": {
    "warmest": {"name":"Africa","value":24.3},
    "coldest": {"name":"North America","value":9.8}
  }
}
```

### 3.3 Metrika oldalak
`GET /api/metric/year?metric=temperature&year=2023`
- Az adott ev osszes entitasa (World + kontinensek) eves atlagban

`GET /api/metric/entity?metric=temperature&entity=Europe&year=2023`
- Az adott ev 12 havi erteke

Valasz pelda:
```json
{
  "metric":"temperature",
  "entity":"Europe",
  "year":2023,
  "months":[
    {"month":1,"value":2.1},
    {"month":2,"value":3.0}
  ]
}
```

### 3.4 Opcionális frissites
`POST /admin/refresh`
- Ujra letolti a CSV-ket
- Ujraepiti az indexeket

## 4) Metrikak es forrasok mapping
Peldak (OWID chart nevekkel):
- `temperature` -> `average-monthly-surface-temperature` (World + kontinensek)
- `co2` -> `co2-fossil-plus-land-use` (eves, ha havi nincs)
- `precipitation` -> OWID csapadek chart, vagy kesobb NASA/Open-Meteo

A chart nev a grafikon URL-bol jon:
`ourworldindata.org/grapher/CHART_NAME`

## 5) Validacio es hibakezeles
- Ismeretlen `metric` -> 400 ("Unknown metric")
- Nem elerheto `year` -> 404 vagy 400 ("Year not available")
- Hianyzo `compare` -> default pl. 1980

## 6) Teljesitmeny
- Nehezebb resz indulaskor (CSV feldolgozas)
- Keresenkent 1-2 dictionary lookup, gyors JSON valasz
- Frontend grafikon rajzolas a szuk keresztmetszet, de demo-ban jo
