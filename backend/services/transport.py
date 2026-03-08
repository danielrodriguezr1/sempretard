"""Servicio de transporte público — Metro + Bus (TMB) y Rodalies (Renfe GTFS-RT).

Consulta incidencias activas AHORA en cada modo de transporte público.
Todas las fuentes son APIs públicas con datos en tiempo real.
"""
from __future__ import annotations

import asyncio
from i18n import _t
import logging
import re
from typing import TYPE_CHECKING

import aiohttp

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=8)
_TIMEOUT_RENFE = aiohttp.ClientTimeout(total=10)

_TOTAL_LINES = {"metro": 12, "bus": 102, "rodalies": 6}
_OPERATORS = {"metro": "TMB", "bus": "TMB", "rodalies": "Renfe Rodalies"}

_BCN_RODALIES_PREFIX = "51"
_BCN_RODALIES_SUFFIXES = re.compile(r"R[1-8]$")
_BCN_KEYWORDS = [
    "rodalies", "#rod", "barcelona", "sants", "passeig de gràcia",
    "arc de triomf", "plaça catalunya",
]


class TransportService:

    def __init__(self, settings: Settings) -> None:
        self._tmb_app_id = settings.tmb_app_id
        self._tmb_app_key = settings.tmb_app_key
        self._has_tmb = settings.has_tmb

    async def get_all_status(self) -> dict[str, dict]:
        metro, bus, rodalies = await asyncio.gather(
            self._get_metro_status(),
            self._get_bus_status(),
            self._get_rodalies_status(),
        )
        return {"metro": metro, "bus": bus, "tren": rodalies}

    async def get_line_frequency(self, line_code: str) -> dict | None:
        """Obtiene frecuencia actual de una línea de metro si TMB está disponible."""
        if not self._has_tmb:
            return None
        try:
            url = (
                f"https://api.tmb.cat/v1/transit/linies/metro/{line_code}/estacions"
                f"?app_id={self._tmb_app_id}&app_key={self._tmb_app_key}"
            )
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=_TIMEOUT) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
            features = data.get("features", [])
            return {"linea": line_code, "estaciones": len(features)}
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Metro (TMB)
    # ------------------------------------------------------------------

    async def _get_metro_status(self) -> dict:
        if not self._has_tmb:
            return self._fallback("metro")
        try:
            url = (
                "https://api.tmb.cat/v1/transit/linies/metro"
                f"?app_id={self._tmb_app_id}&app_key={self._tmb_app_key}"
            )
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=_TIMEOUT) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            features = data.get("features", [])
            total = len(features)
            affected = []
            details = []
            all_lines = []

            for f in features:
                props = f.get("properties", {})
                nom = props.get("NOM_LINIA", "?")
                color = props.get("COLOR_LINIA", "")
                has_incident = props.get("INCIDENCIES", 0) > 0
                desc = props.get("DESC_INCIDENCIA", "")

                line_info = {
                    "linea": nom,
                    "color": color,
                    "estado": "incidencia" if has_incident else "normal",
                }
                if has_incident:
                    line_info["causa"] = desc or "Incidencia activa"
                    affected.append(nom)
                    details.append({"linea": nom, "causa": desc or "Incidencia activa"})
                all_lines.append(line_info)

            n_affected = len(affected)
            nivel = (
                "critico" if n_affected >= 4
                else "elevado" if n_affected >= 1
                else "normal"
            )
            score = max(0, 100 - n_affected * 15)

            razones = []
            if n_affected == 0:
                razones = [_t("transport.metro_ok", total=total)]
                resumen = _t("transport.metro_ok_detail")
            else:
                resumen = _t("transport.metro_incidents", count=n_affected)
                razones = [_t("transport.line_incident", linea=d['linea'], causa=d['causa']) for d in details]

            return {
                "modo": "metro",
                "nivel": nivel,
                "score": score,
                "resumen": resumen,
                "analisis": {
                    "lineas_total": total or _TOTAL_LINES["metro"],
                    "lineas_afectadas": affected,
                    "detalle": details,
                    "todas_lineas": all_lines,
                },
                "razones": razones,
                "fuente": "TMB API",
                "datos_reales": True,
            }

        except Exception as exc:
            logger.warning("TMB Metro fallo: %s", exc)
            return self._fallback("metro")

    # ------------------------------------------------------------------
    # Bus (TMB)
    # ------------------------------------------------------------------

    async def _get_bus_status(self) -> dict:
        if not self._has_tmb:
            return self._fallback("bus")
        try:
            url = (
                "https://api.tmb.cat/v1/transit/linies/bus"
                f"?app_id={self._tmb_app_id}&app_key={self._tmb_app_key}"
            )
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=_TIMEOUT) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            features = data.get("features", [])
            total = len(features)
            affected = []
            details = []
            ok_lines = 0

            for f in features:
                props = f.get("properties", {})
                if props.get("INCIDENCIES", 0) > 0:
                    nom = props.get("NOM_LINIA", "?")
                    desc = props.get("DESC_INCIDENCIA", "Incidencia activa")
                    affected.append(nom)
                    details.append({"linea": nom, "causa": desc})
                else:
                    ok_lines += 1

            n_affected = len(affected)
            nivel = (
                "critico" if n_affected >= 10
                else "elevado" if n_affected >= 3
                else "normal"
            )
            score = max(0, 100 - n_affected * 5)

            razones = []
            if n_affected == 0:
                razones = [_t("transport.bus_ok", total=total)]
                resumen = _t("transport.bus_ok_detail")
            else:
                resumen = _t("transport.bus_incidents", count=n_affected)
                razones = [_t("transport.line_incident", linea=d['linea'], causa=d['causa']) for d in details[:5]]
                if n_affected > 5:
                    razones.append(_t("transport.bus_more_lines", count=n_affected - 5))

            return {
                "modo": "bus",
                "nivel": nivel,
                "score": score,
                "resumen": resumen,
                "analisis": {
                    "lineas_total": total or _TOTAL_LINES["bus"],
                    "lineas_ok": ok_lines,
                    "lineas_afectadas": affected,
                    "detalle": details,
                },
                "razones": razones,
                "fuente": "TMB API",
                "datos_reales": True,
            }

        except Exception as exc:
            logger.warning("TMB Bus fallo: %s", exc)
            return self._fallback("bus")

    # ------------------------------------------------------------------
    # Rodalies — GTFS-RT alerts (público, sin API key)
    # ------------------------------------------------------------------

    async def _get_rodalies_status(self) -> dict:
        try:
            url = "https://gtfsrt.renfe.com/alerts.json"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=_TIMEOUT_RENFE) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            affected_lines: dict[str, str] = {}

            for entity in data.get("entity", []):
                alert = entity.get("alert", {})
                routes = [
                    ie.get("routeId", "")
                    for ie in alert.get("informedEntity", [])
                ]

                bcn_routes = [r for r in routes if _is_bcn_rodalies(r)]
                if not bcn_routes:
                    desc = _extract_alert_text(alert)
                    if not any(kw in desc.lower() for kw in _BCN_KEYWORDS):
                        continue

                line_names = {_route_to_line(r) for r in bcn_routes if _route_to_line(r)}
                cause = _extract_alert_text(alert)

                for line in line_names:
                    if line not in affected_lines or len(cause) > len(affected_lines[line]):
                        affected_lines[line] = cause

            n_affected = len(affected_lines)
            nivel = (
                "critico" if n_affected >= 4
                else "elevado" if n_affected >= 2
                else "normal" if n_affected == 0
                else "elevado"
            )
            score = max(0, 100 - n_affected * 20)

            razones = []
            if n_affected == 0:
                razones = [_t("transport.rodalies_ok")]
                resumen = _t("transport.rodalies_ok_detail")
            else:
                resumen = _t("transport.rodalies_incidents", count=n_affected)
                razones = [_t("transport.line_incident", linea=ln, causa=cause[:200]) for ln, cause in sorted(affected_lines.items())]

            return {
                "modo": "tren",
                "nivel": nivel,
                "score": score,
                "resumen": resumen,
                "analisis": {
                    "lineas_total": _TOTAL_LINES["rodalies"],
                    "lineas_afectadas": sorted(affected_lines.keys()),
                    "detalle": [
                        {"linea": ln, "causa": c[:200]}
                        for ln, c in affected_lines.items()
                    ],
                },
                "razones": razones,
                "fuente": "Renfe GTFS-RT",
                "datos_reales": True,
            }

        except Exception as exc:
            logger.warning("Renfe GTFS-RT fallo: %s", exc)
            return self._fallback("tren")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback(mode: str) -> dict:
        label = {"metro": "Metro", "bus": "Bus", "tren": "Rodalies"}.get(mode, mode)
        return {
            "modo": mode,
            "nivel": "normal",
            "score": 50,
            "resumen": _t("transport.fallback_no_data", label=label),
            "analisis": {},
            "razones": [_t("transport.fallback_error", label=_OPERATORS.get(mode, label))],
            "fuente": "fallback",
            "datos_reales": False,
        }


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _is_bcn_rodalies(route_id: str) -> bool:
    return (
        route_id.startswith(_BCN_RODALIES_PREFIX)
        and bool(_BCN_RODALIES_SUFFIXES.search(route_id))
    )


def _route_to_line(route_id: str) -> str:
    m = _BCN_RODALIES_SUFFIXES.search(route_id)
    return m.group(0) if m else ""


def _extract_alert_text(alert: dict) -> str:
    for t in alert.get("descriptionText", {}).get("translation", []):
        if t.get("language") == "es":
            return t.get("text", "")
    translations = alert.get("descriptionText", {}).get("translation", [])
    return translations[0].get("text", "") if translations else ""
