# Meteon-Climate

Interaktív klímaadat-vizualizációs webalkalmazás Flask alapon.

## Elérés
- https://climate.meteon.hu

## Fő funkciók
- Hőmérsékleti trendek év és kontinens szerint
- Csapadék adatok és havi eloszlás
- CO2-kibocsátás összehasonlítása
- Felmelegedési trend és előrejelzés
- Térképes megjelenítés
- CO2 kalkulátor

## Technológiai stack
- Python, Flask
- HTML, CSS, JavaScript
- Chart.js (CDN)
- Our World in Data adatok

## Futtatás lokálisan (opcionális)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Megnyitás: `http://127.0.0.1:5000`

## API végpontok (röviden)
- `GET /api/meta?metric=temperature|precipitation|co2`
- `GET /api/overview?metric=...&year=...&compare=...`
- `GET /api/metric/year?metric=...&year=...`
- `GET /api/metric/entity?metric=...&entity=...&year=...`
- `GET /api/map?metric=...&year=...`
- `GET /api/temperature/continents?year=...`
- `GET /api/temperature/monthly?entity=...&year=...`
- `GET /api/temperature/warmest`
- `GET /api/temperature/forecast`
- `GET /api/precipitation/continents?year=...`
- `GET /api/precipitation/monthly?entity=...&year=...`
- `GET /api/co2/continents?year=...`
- `GET /api/co2/overview?year=...&compare=...&entity=...`
- `POST /admin/refresh`

## Jogi nyilatkozat
`© 2026 climate.meteon.hu – Minden jog fenntartva.`
