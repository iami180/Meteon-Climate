# Meteon Climate

Klímaadat-vizualizációs webalkalmazás Flask alapon. A projekt célja, hogy közérthető felületen mutassa meg a hőmérséklet, a csapadék, a CO2-kibocsátás és a globális felmelegedés fő trendjeit, grafikonos és térképes nézetekkel.

## Miről szól a projekt?

Az alkalmazás egy többoldalas klíma dashboard, ahol a felhasználó:

- kiválaszthat éveket és régiókat,
- összehasonlíthat eltérő időszakokat,
- megnézheti a kontinensek közötti különbségeket,
- térképen vizsgálhatja az országos értékeket,
- és egy egyszerűsített klímamodell alapján hőmérsékleti előrejelzést is kaphat 2050-ig.

A frontend kizárólag a saját Flask API-t használja. A külső adatforrásokat a backend tölti le, dolgozza fel, cache-eli és egységes JSON formában szolgálja ki.

## Fő funkciók

- Áttekintő dashboard év-összehasonlítással
- Hőmérséklet oldal kontinens- és havi bontással
- Csapadék oldal éves és havi eloszlással
- CO2 oldal összkibocsátással és egy főre jutó mutatóval
- Föld felmelegedése oldal történeti trenddel és előrejelzéssel
- Világtérkép országos szintű rétegekkel
- CO2 kalkulátor oldal
- SEO-barát route-ok előtöltött év/régió paraméterekkel

## Alkalmazott technológiák

### Backend

- Python
- Flask
- requests
- saját service-réteg (`service/`)

### Frontend

- Jinja2 sablonok
- HTML, CSS, vanilla JavaScript
- Chart.js grafikonokhoz
- Leaflet térképes megjelenítéshez

### Adatforrás

- Our World in Data grapher CSV-k
- helyi nyersadat-cache a `data/raw/` mappában

## Projekt felépítése

```text
app.py                      Flask route-ok és API végpontok
service/
  api_service.py            API payloadok összeállítása
  forecast_service.py       felmelegedési előrejelzés
  loaders.py                CSV letöltés, cache, betöltés
  aggregations.py           világ/kontinens aggregációk, per capita számítás
  config.py                 chart nevek, limitek, alapbeállítások
  store.py                  memóriabeli adattár és TTL-alapú cache
templates/                  oldalak és kliensoldali adatlekérés
static/                     stílusok, ikonok
data/raw/                   nyers OWID CSV-k
```

## Oldalak röviden

- `/` kezdőoldal
- `/attekintes` gyors összefoglaló a kiválasztott év globális és kontinentális adatairól
- `/homerseklet` éves és havi hőmérsékleti bontás
- `/csapadek` éves és havi csapadékeloszlás
- `/co2` kontinensenkénti CO2-kibocsátás és per capita mutató
- `/foldfelmelegedes/felmelegedes` történeti trendnézet
- `/foldfelmelegedes/elorejelzes` jövőbeli forgatókönyvek
- `/terkep` országos szintű térképes vizualizáció
- `/co2-kalkulator` külön kalkulátor oldal

## Hogyan működik az adatfeldolgozás?

### 1. Adatbetöltés

A backend a `service/loaders.py` modulon keresztül dolgozik:

- először megnézi, hogy van-e helyi CSV a `data/raw/` mappában,
- ha van, abból tölt,
- ha nincs, letölti az OWID megfelelő grapher CSV-jét,
- majd eltárolja helyben, hogy a következő indulás gyorsabb legyen.

A használt fő chartok:

- `temperature` -> `average-monthly-surface-temperature`
- `precipitation` -> `average-precipitation-per-year`
- `co2` -> `co2-fossil-plus-land-use`
- `population` -> `population`

Ezek environment változóval felülírhatók a `service/config.py` alapján.

### 2. Egységesítés

Betöltéskor a rendszer:

- normalizálja az entitásneveket,
- eltárolja az országkódokat,
- felismeri a dátum oszlopot,
- havi és éves adatokat külön indexel,
- szükség esetén havi adatokból éves átlagot számol.

A belső memóriamodell:

- `STORE.monthly[metric][entity][year] -> [12 havi érték]`
- `STORE.yearly[metric][entity][year] -> éves érték`
- `STORE.years[metric] -> elérhető évek`
- `STORE.entities[metric] -> elérhető entitások`

### 3. Aggregáció

A `service/aggregations.py` végzi az összesítéseket:

- hőmérsékletnél és csapadéknál átlagol,
- CO2-nél összead,
- országokat kontinensekhez rendel,
- világértéket kontinensekből számol, ha nincs közvetlen adat,
- CO2 esetén népességadattal egy főre jutó mutatót is számol.

### 4. Cache és frissítés

A memóriabeli store TTL-alapú. Ha a beállított időn túl nincs használat, a store ürül, majd újratöltődik. Induláskor egy háttérszál előmelegíti a gyakori adatokat (`warm_cache_all()`).

Manuális frissítés:

- `POST /admin/refresh`

Ez újratölti a külső CSV-ket és felülírja a helyi cache fájlokat.

## API működése

Az API réteg a `service/api_service.py` fájlban építi fel a JSON válaszokat.

Főbb végpontok:

- `GET /api/meta`
- `GET /api/overview`
- `GET /api/metric/year`
- `GET /api/metric/entity`
- `GET /api/map`
- `GET /api/temperature/warmest`
- `GET /api/temperature/forecast`
- `GET /api/co2/overview`
- `POST /admin/refresh`

### Mit csinál az API a háttérben?

- validálja a metrikát,
- ellenőrzi, hogy az adott év elérhető-e,
- fallback évet választ, ha kell,
- kiszámolja a világértéket és az összehasonlítási deltát,
- felépíti a kontinenslistákat és rangsorokat,
- térképhez ISO3 országkódos listát ad vissza,
- CO2 esetén per capita mutatót ad hozzá,
- csapadéknál havi bontást becsül, ha csak éves adat áll rendelkezésre.

## Hogyan működik a csapadék havi becslése?

A csapadékforrás nem minden esetben tartalmaz teljes havi bontást. Ilyenkor a rendszer:

- megkeresi az éves csapadékértéket,
- kontinensenként előre definiált havi arányprofilt használ,
- ebből 12 havi becsült értéket képez,
- és a válaszban jelzi, hogy ez becsült adat (`estimated_monthly: true`).

Antarktiszra külön fallback éves érték is szerepel.

## Hogyan működik az előrejelzés?

Az előrejelzés nem sima lineáris trendvonal. A `service/forecast_service.py` egy egyszerűsített, fizikailag motivált modellt használ.

### 1. Történeti idősor előkészítése

- betölti a globális éves hőmérséklet idősorát,
- betölti a globális CO2 kibocsátási idősorát,
- bázisidőszakot képez,
- ebből hőmérsékleti anomáliát számol.

Elsődleges bázisidőszak:

- `1850-1900`

Fallback bázis:

- `1951-1980`

Ehhez egy korrekciós offset is tartozik, hogy a preindusztriális referencia közelíthető legyen.

### 2. Koncentráció-becslés

A modell a kibocsátási adatokból becsült koncentrációs idősorokat állít elő:

- CO2 ppm
- CH4 ppb
- N2O ppb

Ez nem közvetlen méréssor, hanem egyszerűsített becslés a történeti kibocsátásokból.

### 3. Sugárzási kényszer

A modell számol:

- CO2 forcinggal logaritmikus képlettel
- CH4 és N2O forcinggal négyzetgyök-alapú közelítéssel
- aeroszol proxyval

A CO2 forcing képlete:

`dF = 5.35 * ln(C / C0)`

### 4. Kétrekeszes hőmérsékleti modell

A hőmérsékletet egy kétkomponensű energiamérleg-modell szimulálja:

- felszíni réteg
- mélyóceáni réteg

Ez azért fontos, mert az óceán hőtehetetlensége késlelteti a rendszer reakcióját.

### 5. Kalibráció

A modell több paraméterkombinációt próbál ki rácskereséssel:

- ECS
- hőcsere paraméter
- felszíni hőkapacitás
- aeroszol skálák
- ENSO amplitúdó

A cél, hogy a modell jól kövesse a múltbeli anomáliasort. A score alapja:

- train RMSE
- TCR tartománybüntetés

Kalibrációs szakasz:

- `1950-2000`

Backtest:

- `2001-től a jelenig`

### 6. Jövőbeli szcenáriók

Három forgatókönyv készül:

- alacsony kibocsátás
- közepes kibocsátás
- magas kibocsátás

Mindegyikhez Monte Carlo mintavételezés fut, amely:

- kis mértékben szórja a modellparamétereket,
- módosítja a jövőbeli gázkoncentrációkat,
- aeroszol bizonytalanságot is beépít.

Az eredmény nem egyetlen szám, hanem sávos előrejelzés:

- medián érték
- alsó tartomány
- felső tartomány

A frontend ezekből rajzolja meg a 2030-as és 2050-es várható pályákat.

## Fontosabb számított mutatók

- globális éves átlag
- összehasonlított évek közötti delta
- éves hőingás: `max(havi átlag) - min(havi átlag)`
- legmelegebb / leghűvösebb kontinens
- legmelegebb globális év
- CO2 per capita
- országos térképi értéktartományok

## Futtatás lokálisan

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Alapértelmezett cím:

`http://127.0.0.1:5000`

## Konfiguráció

A projekt több beállítást environment változókból olvas:

- `DATA_DIR`
- `TEMPERATURE_CHART`
- `PRECIPITATION_CHART`
- `CO2_CHART`
- `POPULATION_CHART`
- `DEFAULT_COMPARE_YEAR`
- `CACHE_TTL_SECONDS`
- `MAX_YEAR`

## Megjegyzések és korlátok

- A projekt alapvetően OWID adatokra épül.
- Egyes csapadék havi bontások becsültek, nem közvetlen megfigyelések.
- Az előrejelzés demonstrációs célú, egyszerűsített klímamodell, nem hivatalos tudományos előrejelző rendszer.
- A térképes nézet külső GeoJSON állománnyal dolgozik.

## Rövid összefoglaló

Ez a projekt egy teljes klíma dashboard:

- backend oldalon adatletöltéssel, cache-sel, aggregációval és előrejelző modellel,
- frontend oldalon interaktív grafikonokkal és térképpel,
- egységes API-val, amelyből minden oldal dolgozik.
