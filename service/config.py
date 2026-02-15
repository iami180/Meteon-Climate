import os

DATA_DIR = os.getenv("DATA_DIR", "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")

# Default OWID grapher chart names. Override via env vars if needed.
# Example: TEMPERATURE_CHART=average-monthly-surface-temperature
CHARTS = {
    "temperature": os.getenv("TEMPERATURE_CHART", "average-monthly-surface-temperature"),
    "precipitation": os.getenv("PRECIPITATION_CHART", "average-precipitation-per-year"),
    "co2": os.getenv("CO2_CHART", "co2-fossil-plus-land-use"),
}

METRICS = ["temperature", "precipitation", "co2"]
DEFAULT_COMPARE_YEAR = int(os.getenv("DEFAULT_COMPARE_YEAR", "1980"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "600"))
MAX_YEAR = int(os.getenv("MAX_YEAR", "2025"))
POPULATION_CHART = os.getenv("POPULATION_CHART", "population")

CONTINENTS = {
    "World",
    "Europe",
    "Asia",
    "Africa",
    "North America",
    "South America",
    "Australia and Oceania",
    "Antarctica",
}
