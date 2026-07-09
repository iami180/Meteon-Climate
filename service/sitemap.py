"""SEO: dinamikus sitemap.xml es robots.txt generalas.

A kanonikus oldalakat egy statikus listabol, a SEO ev-/kontinens-variansokat
pedig a valos adatbol (meta_response) allitja elo, igy a sitemap mindig a
ténylegesen elerheto evekhez es entitasokhoz igazodik.
"""
import os
import re
from datetime import date
from xml.sax.saxutils import escape

from .api_service import meta_response
from .config import CONTINENTS, DEFAULT_COMPARE_YEAR, MAX_YEAR, METRICS

# Abszolut URL-ekhez: proxy mogott a request host nem megbizhato, ezert konfiggal.
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://climate.meteon.hu").rstrip("/")
# A tul regi evekre nem generalunk kulon SEO oldalt (fokuszalt sitemap).
SITEMAP_MIN_YEAR = int(os.getenv("SITEMAP_MIN_YEAR", "1940"))

_SECTION_BY_METRIC = {
    "temperature": "homerseklet",
    "precipitation": "csapadek",
    "co2": "co2",
}


def entity_to_slug(entity):
    """Ugyanaz a slug, mint a frontend entityToSlug()-ja:
    kisbetu, nem-alfanumerikus futamok '-'-re, majd a szeleken trimmelve."""
    slug = re.sub(r"[^a-z0-9]+", "-", (entity or "").lower())
    return slug.strip("-")


def _static_pages():
    # (path, changefreq, priority)
    return [
        ("/", "weekly", "1.0"),
        ("/attekintes", "weekly", "0.9"),
        ("/homerseklet", "weekly", "0.9"),
        ("/csapadek", "weekly", "0.9"),
        ("/co2", "weekly", "0.9"),
        ("/terkep", "weekly", "0.8"),
        ("/foldfelmelegedes/felmelegedes", "weekly", "0.8"),
        ("/foldfelmelegedes/elorejelzes", "weekly", "0.8"),
        ("/co2-kalkulator", "monthly", "0.7"),
        ("/adatok", "monthly", "0.5"),
    ]


def _dynamic_pages():
    meta = {}
    for metric in METRICS:
        try:
            meta[metric] = meta_response(metric)
        except Exception:
            meta[metric] = {"years": []}

    def years(metric):
        return sorted(y for y in meta.get(metric, {}).get("years", []) if y >= SITEMAP_MIN_YEAR)

    t_years, p_years, c_years = years("temperature"), years("precipitation"), years("co2")
    pages = []

    # Ev-szintu fooldalak (World / ev-only, ahol a route engedi).
    for y in t_years:
        pages.append((f"/attekintes/{y}/{DEFAULT_COMPARE_YEAR}", "monthly", "0.6"))
        pages.append((f"/homerseklet/{y}", "monthly", "0.6"))
    for y in p_years:
        pages.append((f"/csapadek/{y}/world", "monthly", "0.6"))
    for y in c_years:
        pages.append((f"/co2/{y}/world", "monthly", "0.6"))

    # Terkep: metrika x ev.
    for metric, yrs in (("temperature", t_years), ("precipitation", p_years), ("co2", c_years)):
        for y in yrs:
            pages.append((f"/terkep/{metric}/{y}", "monthly", "0.5"))

    # Kontinensek a legfrissebb evre (foldrajzi dimenzio, ev-robbanas nelkul).
    continents = sorted(c for c in CONTINENTS if c != "World")
    for metric, yrs in (("temperature", t_years), ("precipitation", p_years), ("co2", c_years)):
        if not yrs:
            continue
        section, latest = _SECTION_BY_METRIC[metric], max(yrs)
        for c in continents:
            pages.append((f"/{section}/{latest}/{entity_to_slug(c)}", "monthly", "0.5"))

    # Felmelegedes kanonikus intervallumok.
    for start in (1880, 1940, 1980, 2000):
        pages.append((f"/foldfelmelegedes/felmelegedes/{start}/{MAX_YEAR}", "monthly", "0.5"))

    return pages


def _all_pages():
    pages = list(_static_pages())
    try:
        pages.extend(_dynamic_pages())
    except Exception:
        pass  # adat nelkul is legalabb a statikus oldalak menjenek ki
    seen, unique = set(), []
    for path, changefreq, priority in pages:
        if path in seen:
            continue
        seen.add(path)
        unique.append((path, changefreq, priority))
    return unique


def sitemap_xml():
    today = date.today().isoformat()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path, changefreq, priority in _all_pages():
        loc = escape(f"{SITE_BASE_URL}{path}")
        lines.append(
            f"  <url><loc>{loc}</loc><lastmod>{today}</lastmod>"
            f"<changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>"
        )
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def robots_txt():
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Disallow: /admin/\n"
        f"Sitemap: {SITE_BASE_URL}/sitemap.xml\n"
    )
