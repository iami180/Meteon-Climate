# Meteon-Climate

Interactive climate data visualization web app built with Flask.

## Live
- https://climate.meteon.hu

## Main features
- Temperature trends by year and continent
- Precipitation overview and monthly distribution
- CO2 emission comparison
- Warming trend and forecast view
- Map-based visualization
- CO2 calculator

## Tech stack
- Python, Flask
- HTML, CSS, JavaScript
- Chart.js (CDN)
- Our World in Data datasets

## Local run (optional)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open: `http://127.0.0.1:5000`

## API endpoints (short)
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

## Rights
`Copyright 2026 climate.meteon.hu. All rights reserved.`
