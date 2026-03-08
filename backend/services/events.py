"""Servicio de eventos — Open Data BCN + partidos FC Barcelona.

Clasifica eventos por nivel de impacto en el transporte y mapea
venues conocidos a las lineas de metro que saturan.
"""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import TYPE_CHECKING

import httpx
import pandas as pd

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)

_BCN_CKAN_URL = (
    "https://opendata-ajuntament.barcelona.cat"
    "/data/api/3/action/datastore_search"
)
_BCN_CKAN_SQL_URL = (
    "https://opendata-ajuntament.barcelona.cat"
    "/data/api/3/action/datastore_search_sql"
)
_BCN_RESOURCE_ID = "877ccf66-9106-4ae2-be51-95a9f6469e4c"
_BCN_FETCH_LIMIT = 1000
_BCN_TIMEOUT = 20

_FOOTBALL_API_URL = "https://api.football-data.org/v4/teams"
_BARCA_TEAM_ID = 81
_FOOTBALL_TIMEOUT = 10

# ══════════════════════════════════════════════════════════════════════
# Venue → transport impact
# ══════════════════════════════════════════════════════════════════════

_VENUE_TRANSPORT: dict[str, dict] = {
    "fira gran via": {
        "lineas_afectadas": ["L1 (Fira)", "L9 Sud (Europa|Fira)"],
        "capacidad": "masivo",
    },
    "fira barcelona": {
        "lineas_afectadas": ["L1 (Fira/Espanya)", "L3 (Espanya)", "L9 Sud"],
        "capacidad": "masivo",
    },
    "fira montjuïc": {
        "lineas_afectadas": ["L1 (Espanya)", "L3 (Espanya)"],
        "capacidad": "grande",
    },
    "palau sant jordi": {
        "lineas_afectadas": ["L1 (Espanya)", "L3 (Espanya)"],
        "capacidad": "masivo",
    },
    "estadi olímpic": {
        "lineas_afectadas": ["L1 (Espanya)", "L3 (Espanya)"],
        "capacidad": "masivo",
    },
    "estadi olimpic": {
        "lineas_afectadas": ["L1 (Espanya)", "L3 (Espanya)"],
        "capacidad": "masivo",
    },
    "camp nou": {
        "lineas_afectadas": ["L3 (Les Corts/Palau Reial)", "L5 (Collblanc)"],
        "capacidad": "masivo",
    },
    "ccib": {
        "lineas_afectadas": ["L4 (El Maresme-Forum)"],
        "capacidad": "grande",
    },
    "fòrum": {
        "lineas_afectadas": ["L4 (El Maresme-Forum)"],
        "capacidad": "grande",
    },
    "parc del fòrum": {
        "lineas_afectadas": ["L4 (El Maresme-Forum)"],
        "capacidad": "masivo",
    },
    "sant jordi club": {
        "lineas_afectadas": ["L1 (Espanya)", "L3 (Espanya)"],
        "capacidad": "mediano",
    },
    "razzmatazz": {
        "lineas_afectadas": ["L4 (Bogatell)"],
        "capacidad": "mediano",
    },
    "sala apolo": {
        "lineas_afectadas": ["L2 (Paral-lel)", "L3 (Paral-lel)"],
        "capacidad": "mediano",
    },
    "liceu": {
        "lineas_afectadas": ["L3 (Liceu)"],
        "capacidad": "mediano",
    },
    "auditori": {
        "lineas_afectadas": ["L1 (Marina)"],
        "capacidad": "mediano",
    },
    "teatre nacional": {
        "lineas_afectadas": ["L1 (Glories)"],
        "capacidad": "mediano",
    },
}

# ══════════════════════════════════════════════════════════════════════
# Impact classification keywords
# ══════════════════════════════════════════════════════════════════════

_MEGA_KW = [
    "mobile world congress", "mwc", "primavera sound", "sónar", "sonar",
    "cruïlla", "cruilla", "festa major", "festes de la mercè",
    "cavalcada de reis", "nit de cap d'any", "revetlla de sant joan",
    "nit de sant joan", "marató de barcelona", "zurich marató",
]
_LARGE_KW = [
    "festival", "festes de", "macro", "cursa", "piromusical", "nit de",
    "palau sant jordi", "estadi olímpic", "camp nou", "sant jordi club",
    "fira barcelona", "ccib", "fòrum", "congrés", "congres", "congress",
    "razzmatazz", "sala apolo",
]
_LARGE_WORD_BOUNDARY = ["concert", "concerts", "saló", "salon", "expo"]
_MEDIUM_KW = [
    "espectacle", "dansa", "música en viu",
    "mercat", "mostra", "recital",
    "liceu", "auditori", "teatre nacional",
]
_MEDIUM_WORD_BOUNDARY = ["teatre", "fira"]

_PERMANENT_KW = [
    "exposició", "exposicion", "exposición", "exhibition",
    "il·luminació", "iluminació", "iluminacion",
    "casal d'estiu", "casal d'hivern",
    "cicle ", "taller ", "curs ", "curso ",
    "visita guiada", "itinerari", "ruta ",
    "concurs", "concurso",
    "espai per a vianants",
    "experiència", "experiencia",
]

_TIER_ORDER = {"masivo": 0, "grande": 1, "mediano": 2, "pequeno": 3}
_BARCA_LINES = ["L3 (Les Corts/Palau Reial)", "L5 (Collblanc)"]


class EventService:

    def __init__(self, settings: Settings) -> None:
        self._football_key = settings.football_api_key
        self._has_football = settings.has_football

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def get_events_7days(self, start: date | None = None) -> list[dict]:
        """Eventos de 7 dias con clasificacion de impacto."""
        if start is None:
            start = date.today()
        end = start + timedelta(days=6)

        bcn_events = await self._fetch_bcn_events(start, end)
        barca_dates = await self._fetch_barca_matches(start, end)

        return [
            self._build_day(start + timedelta(days=i), bcn_events, barca_dates)
            for i in range(7)
        ]

    # ------------------------------------------------------------------
    # Day assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _build_day(
        d: date,
        all_events: list[dict],
        barca_dates: set[date],
    ) -> dict:
        day_events = [e for e in all_events if e["start"] <= d <= e["end"]]
        day_events.sort(key=lambda e: _TIER_ORDER.get(e.get("tier", "pequeno"), 3))

        has_masivo = any(e["tier"] == "masivo" for e in day_events)
        partido_barca = d in barca_dates
        if partido_barca:
            has_masivo = True

        all_lines: set[str] = set()
        for e in day_events:
            all_lines.update(e.get("lineas_afectadas", []))
        if partido_barca:
            all_lines.update(_BARCA_LINES)

        destacados = _build_highlights(day_events, partido_barca)

        n_masivos = sum(1 for e in day_events if e["tier"] == "masivo")
        if partido_barca:
            n_masivos += 1

        return {
            "fecha": d,
            "n_eventos_dia": len(day_events),
            "evento_masivo": int(has_masivo),
            "partido_barca_casa": int(partido_barca),
            "eventos_destacados": destacados[:10],
            "lineas_afectadas_por_eventos": sorted(all_lines),
            "resumen": {
                "masivos": n_masivos,
                "grandes": sum(1 for e in day_events if e["tier"] == "grande"),
                "medianos": sum(1 for e in day_events if e["tier"] == "mediano"),
                "total": len(day_events),
            },
            "eventos_nombres": [e["name"] for e in day_events[:5]],
        }

    # ------------------------------------------------------------------
    # BCN Open Data
    # ------------------------------------------------------------------

    async def _fetch_bcn_events(self, start: date, end: date) -> list[dict]:
        sql = (
            f'SELECT * FROM "{_BCN_RESOURCE_ID}" '
            f"WHERE \"end_date\" >= '{start.isoformat()}' "
            f"AND \"start_date\" <= '{end.isoformat()}' "
            f'ORDER BY "start_date" DESC LIMIT {_BCN_FETCH_LIMIT}'
        )
        try:
            async with httpx.AsyncClient(timeout=_BCN_TIMEOUT) as client:
                resp = await client.get(_BCN_CKAN_SQL_URL, params={"sql": sql})
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Open Data BCN SQL fallo: %s, probando fallback", exc)
            return await self._fetch_bcn_events_fallback(start, end)

        records = data.get("result", {}).get("records", [])
        logger.info("Open Data BCN: %d eventos encontrados para %s — %s", len(records), start, end)
        events: list[dict] = []
        for rec in records:
            parsed = self._parse_bcn_record(rec, start, end)
            if parsed is not None:
                events.append(parsed)
        return events

    async def _fetch_bcn_events_fallback(self, start: date, end: date) -> list[dict]:
        """Fallback: fetch without SQL if the SQL endpoint fails."""
        params = {"resource_id": _BCN_RESOURCE_ID, "limit": _BCN_FETCH_LIMIT}
        try:
            async with httpx.AsyncClient(timeout=_BCN_TIMEOUT) as client:
                resp = await client.get(_BCN_CKAN_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Open Data BCN fallback fallo: %s", exc)
            return []

        records = data.get("result", {}).get("records", [])
        events: list[dict] = []
        for rec in records:
            parsed = self._parse_bcn_record(rec, start, end)
            if parsed is not None:
                events.append(parsed)
        return events

    @staticmethod
    def _parse_bcn_record(rec: dict, start: date, end: date) -> dict | None:
        name = rec.get("name", "")
        start_str = rec.get("start_date", "")
        end_str = rec.get("end_date", "")
        if not start_str:
            return None

        try:
            s = pd.to_datetime(start_str, utc=True).date()
        except Exception:
            return None

        try:
            e = pd.to_datetime(end_str, utc=True).date() if end_str else s
        except Exception:
            e = s

        if e < start or s > end:
            return None

        duration_days = (e - s).days
        name_lower = name.lower()

        is_permanent = any(kw in name_lower for kw in _PERMANENT_KW)
        if is_permanent and duration_days > 7:
            return None
        if duration_days > 14:
            return None

        address = rec.get("addresses_road_name", "") or ""
        district = rec.get("addresses_district_name", "") or ""
        classification = classify_event(name, f"{address} {district}")

        return {
            "name": name,
            "start": s,
            "end": e,
            "district": district,
            "tier": classification["tier"],
            "lineas_afectadas": classification["lineas_afectadas"],
            "venue": classification["venue"],
        }

    # ------------------------------------------------------------------
    # FC Barcelona
    # ------------------------------------------------------------------

    async def _fetch_barca_matches(self, start: date, end: date) -> set[date]:
        if not self._has_football:
            return set()

        season = start.year if start.month >= 8 else start.year - 1
        url = f"{_FOOTBALL_API_URL}/{_BARCA_TEAM_ID}/matches"
        params = {"season": season, "status": "SCHEDULED,TIMED,IN_PLAY,FINISHED"}
        headers = {"X-Auth-Token": self._football_key}

        try:
            async with httpx.AsyncClient(timeout=_FOOTBALL_TIMEOUT) as client:
                resp = await client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("Football-data.org fallo: %s", exc)
            return set()

        home_dates: set[date] = set()
        for match in data.get("matches", []):
            if match.get("homeTeam", {}).get("id") != _BARCA_TEAM_ID:
                continue
            try:
                match_date = date.fromisoformat(match["utcDate"][:10])
                if start <= match_date <= end:
                    home_dates.add(match_date)
            except (KeyError, ValueError):
                continue
        return home_dates


# ══════════════════════════════════════════════════════════════════════
# Classification (pure functions)
# ══════════════════════════════════════════════════════════════════════

_NON_IMPACT_PREFIX = [
    "exposició", "exposicion", "exposición",
    "cicle ", "taller ", "curs ", "curso ",
    "visita ", "itinerari", "ruta ",
    "sortida ", "concurs", "concurso",
    "espectacle", "espectáculo",
    "obra ", "lectura ",
]


def classify_event(name: str, address: str = "") -> dict:
    """Clasifica un evento por tier de impacto y detecta venue."""
    name_lower = name.lower()
    combined = name_lower + " " + address.lower()

    is_non_impact = any(name_lower.startswith(p) or f" {p}" in name_lower for p in _NON_IMPACT_PREFIX)

    tier = _classify_tier(name_lower)

    if is_non_impact and tier in ("masivo", "grande"):
        tier = "mediano"

    lineas, venue = _detect_venue(combined)

    if venue and not is_non_impact:
        venue_cap = _VENUE_TRANSPORT[venue]["capacidad"]
        if venue_cap == "masivo" and tier in ("pequeno", "mediano"):
            tier = "grande"
        elif venue_cap == "grande" and tier == "pequeno":
            tier = "mediano"

    return {"tier": tier, "lineas_afectadas": lineas, "venue": venue}


def _classify_tier(name_lower: str) -> str:
    if any(kw in name_lower for kw in _MEGA_KW):
        return "masivo"
    if any(kw in name_lower for kw in _LARGE_KW) or _word_match(name_lower, _LARGE_WORD_BOUNDARY):
        return "grande"
    if any(kw in name_lower for kw in _MEDIUM_KW) or _word_match(name_lower, _MEDIUM_WORD_BOUNDARY):
        return "mediano"
    return "pequeno"


def _detect_venue(combined: str) -> tuple[list[str], str | None]:
    for venue_name, venue_info in _VENUE_TRANSPORT.items():
        if venue_name in combined:
            return venue_info["lineas_afectadas"], venue_name
    return [], None


def _word_match(text: str, keywords: list[str]) -> bool:
    for kw in keywords:
        pattern = r'(?:^|[\s"\'\(\[,;:])' + re.escape(kw) + r'(?:$|[\s"\'\)\],;:.])'
        if re.search(pattern, text):
            return True
    return False


def _build_highlights(day_events: list[dict], partido_barca: bool) -> list[dict]:
    highlights: list[dict] = []

    if partido_barca:
        highlights.append({
            "nombre": "FC Barcelona en casa",
            "impacto": "masivo",
            "lineas_afectadas": _BARCA_LINES,
            "venue": "camp nou",
        })

    for e in day_events:
        if e["tier"] not in ("masivo", "grande"):
            continue
        entry: dict = {"nombre": e["name"], "impacto": e["tier"]}
        if e.get("lineas_afectadas"):
            entry["lineas_afectadas"] = e["lineas_afectadas"]
        if e.get("venue"):
            entry["venue"] = e["venue"]
        highlights.append(entry)

    return highlights
