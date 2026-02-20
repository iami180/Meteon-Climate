from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List

from .config import CACHE_TTL_SECONDS


@dataclass
class DataStore:
    monthly: Dict[str, Dict[str, Dict[int, List[float]]]]
    yearly: Dict[str, Dict[str, Dict[int, float]]]
    last_refresh: float
    years: Dict[str, List[int]]
    entities: Dict[str, List[str]]
    entity_codes: Dict[str, str]


STORE = DataStore(
    monthly=defaultdict(lambda: defaultdict(dict)),
    yearly=defaultdict(lambda: defaultdict(dict)),
    last_refresh=0.0,
    years=defaultdict(list),
    entities=defaultdict(list),
    entity_codes={},
)

POPULATION_YEARLY: Dict[str, Dict[int, float]] = defaultdict(dict)
POPULATION_YEARS: set[int] = set()

COUNTRY_TO_CONTINENT: Dict[str, str] = {}
COUNTRY_MAP_LOADED = False

LAST_ACCESS = 0.0


# kiuriti a memoriaban tarolt adatokat
def reset_store() -> None:
    STORE.monthly.clear()
    STORE.yearly.clear()
    STORE.years.clear()
    STORE.entities.clear()
    STORE.entity_codes.clear()
    POPULATION_YEARLY.clear()
    POPULATION_YEARS.clear()


# frissiti az utolso hasznalat idejet es ttl-t nez
def touch_access() -> None:
    global LAST_ACCESS
    now = time.time()
    if LAST_ACCESS and (now - LAST_ACCESS) > CACHE_TTL_SECONDS:
        reset_store()
    LAST_ACCESS = now
