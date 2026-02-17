# climate.meteon.hu

Interaktív klímaadat-vizualizációs webalkalmazás Flask alapon.

## Elérés
- Éles verzió: `https://climate.meteon.hu`

## Fő funkciók
- Globális és kontinens szintű hőmérsékleti adatok
- Csapadék trendek és havi bontás
- CO2-kibocsátás összehasonlítás
- Felmelegedési trend és előrejelzés
- Térképes megjelenítés
- CO2 kalkulátor

## Technológiai stack
- Backend: `Python`, `Flask`
- Frontend: `HTML`, `CSS`, `JavaScript`
- Diagramok: `Chart.js` (CDN)
- Adatforrás: `Our World in Data`

## Futtatás lokálisan (opcionális)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Majd nyisd meg: `http://127.0.0.1:5000`

## Projektstruktúra
- `app.py` - Flask route-ok és API endpointok
- `templates/` - Jinja2 HTML sablonok
- `static/` - statikus erőforrások
- `service/` - adatbetöltés, aggregáció, előrejelzés, API logika
- `data/` - nyers/cache-elt adatfájlok

## API végpontok (röviden)
- `GET /api/meta?metric=temperature|precipitation|co2` - elérhető évek és entitások
- `GET /api/overview?metric=...&year=...&compare=...` - összesített nézet
- `GET /api/metric/year?metric=...&year=...` - adott év adatai
- `GET /api/metric/entity?metric=...&entity=...&year=...` - adott entitás részletei
- `GET /api/map?metric=...&year=...` - térképes megjelenítéshez szükséges adatok
- `GET /api/temperature/continents?year=...` - hőmérséklet kontinensenként
- `GET /api/temperature/monthly?entity=...&year=...` - hőmérséklet havi bontás
- `GET /api/temperature/warmest` - legmelegebb globális év
- `GET /api/temperature/forecast` - felmelegedési előrejelzés
- `GET /api/precipitation/continents?year=...` - csapadék kontinensenként
- `GET /api/precipitation/monthly?entity=...&year=...` - csapadék havi bontás
- `GET /api/co2/continents?year=...` - CO2 kontinensenként
- `GET /api/co2/overview?year=...&compare=...&entity=...` - CO2 összesítés és per fő érték
- `POST /admin/refresh` - adatcache frissítése

## Licenc és jogok
`© 2026 climate.meteon.hu – Minden jog fenntartva.`
