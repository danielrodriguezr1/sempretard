"""Servicio SCT — Servei Català de Trànsit.

Descarga incidencias viarias de toda Catalunya en tiempo real desde
el feed GML del SCT y filtra las del área metropolitana de Barcelona.

Fuente: http://www.gencat.cat/transit/opendata/incidenciesGML.xml
Licencia: Open Data Generalitat de Catalunya
Actualización: cada 5 minutos
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import aiohttp

from i18n import _t

logger = logging.getLogger(__name__)

_GML_URL = "http://www.gencat.cat/transit/opendata/incidenciesGML.xml"
_TIMEOUT = aiohttp.ClientTimeout(total=20)

_BCN_METRO_BOUNDS = {
    "lat_min": 41.28,
    "lat_max": 41.55,
    "lon_min": 1.70,
    "lon_max": 2.42,
}

_METRO_ROADS = {
    "AP-7", "A-2",
    "B-10", "B-20", "B-23", "B-24", "B-30",
    "C-16", "C-17", "C-31", "C-31c", "C-31d", "C-32", "C-33", "C-35", "C-58", "C-59",
    "C-245", "C-340",
    "N-II", "N-150", "N-152z", "N-340",
    "B-40", "B-40z",
}

_NS = {
    "gml": "http://www.opengis.net/gml",
    "wfs": "http://www.opengis.net/wfs",
    "cite": "http://www.opengeospatial.net/cite",
}

_NIVELL_LABEL = {
    "1": "info",
    "2": "obres",
    "3": "retenció",
    "4": "tallada",
    "5": "tallada",
}

_TIPO_SEVERITY = {
    "Retenció": "retencio",
    "Obres": "obres",
    "Cons": "info",
}

_SEVERITY_SCORE = {
    "tallada": 0,
    "retencio": 1,
    "obres": 2,
    "info": 3,
}


class SCTService:

    def __init__(self) -> None:
        self._cache: list[dict] | None = None
        self._cache_ts: datetime | None = None
        self._cache_ttl = 300

    async def get_metro_incidents(self) -> dict:
        """Incidencias viarias en el área metropolitana de Barcelona."""
        try:
            incidents = await self._fetch_and_parse()
            return self._build_result(incidents)
        except Exception as exc:
            logger.warning("SCT fallo: %s", exc)
            return self._fallback()

    async def get_map_incidents(self) -> list[dict]:
        """Incidencias geolocalizadas para el mapa."""
        try:
            return await self._fetch_and_parse()
        except Exception as exc:
            logger.warning("SCT map fallo: %s", exc)
            return []

    async def _fetch_and_parse(self) -> list[dict]:
        now = datetime.now()
        if (
            self._cache is not None
            and self._cache_ts is not None
            and (now - self._cache_ts).total_seconds() < self._cache_ttl
        ):
            return self._cache

        async with aiohttp.ClientSession() as session:
            async with session.get(_GML_URL, timeout=_TIMEOUT) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"SCT GML HTTP {resp.status}")
                xml_text = await resp.text(encoding="utf-8", errors="ignore")

        incidents = self._parse_gml(xml_text)
        self._cache = incidents
        self._cache_ts = now
        return incidents

    def _parse_gml(self, xml_text: str) -> list[dict]:
        root = ET.fromstring(xml_text)
        results: list[dict] = []

        for member in root.findall(".//gml:featureMember", _NS):
            feat = member.find("cite:mct2_v_afectacions_data", _NS)
            if feat is None:
                continue

            coords_el = feat.find(".//gml:coordinates", _NS)
            if coords_el is None or not coords_el.text:
                continue

            try:
                lon_s, lat_s = coords_el.text.strip().split(",")
                lon, lat = float(lon_s), float(lat_s)
            except (ValueError, IndexError):
                continue

            carretera = self._text(feat, "cite:carretera")
            if not carretera:
                continue

            if not self._is_metro_area(lat, lon, carretera):
                continue

            nivell = self._text(feat, "cite:nivell") or "1"
            tipo_desc = self._text(feat, "cite:descripcio_tipus") or ""
            severity = _TIPO_SEVERITY.get(tipo_desc, _NIVELL_LABEL.get(nivell, "info"))

            incident: dict[str, Any] = {
                "id": self._text(feat, "cite:identificador") or "",
                "lat": lat,
                "lon": lon,
                "carretera": carretera,
                "causa": self._text(feat, "cite:causa") or "",
                "descripcion": self._text(feat, "cite:descripcio") or "",
                "tipo": tipo_desc,
                "severity": severity,
                "nivel": int(nivell) if nivell.isdigit() else 1,
                "sentido": self._text(feat, "cite:sentit") or "",
                "hacia": self._text(feat, "cite:cap_a") or "",
                "pk_inicio": self._text(feat, "cite:pk_inici") or "",
                "pk_fin": self._text(feat, "cite:pk_fi") or "",
                "fecha": self._text(feat, "cite:data") or "",
                "fuente": "SCT",
            }
            results.append(incident)

        results.sort(key=lambda i: _SEVERITY_SCORE.get(i["severity"], 9))
        return results

    @staticmethod
    def _text(el: ET.Element, tag: str) -> str | None:
        child = el.find(tag, _NS)
        return child.text.strip() if child is not None and child.text else None

    @staticmethod
    def _is_metro_area(lat: float, lon: float, _road: str) -> bool:
        return (
            _BCN_METRO_BOUNDS["lat_min"] <= lat <= _BCN_METRO_BOUNDS["lat_max"]
            and _BCN_METRO_BOUNDS["lon_min"] <= lon <= _BCN_METRO_BOUNDS["lon_max"]
        )

    def _build_result(self, incidents: list[dict]) -> dict:
        retencions = [i for i in incidents if i["severity"] == "retencio"]
        tallades = [i for i in incidents if i["severity"] == "tallada"]
        obres = [i for i in incidents if i["severity"] == "obres"]

        total = len(incidents)
        graves = len(retencions) + len(tallades)

        if tallades and len(tallades) >= 2:
            nivel = "critico"
            score = max(10, 50 - len(tallades) * 12 - len(retencions) * 5)
        elif tallades or len(retencions) >= 5:
            nivel = "elevado"
            score = max(20, 55 - len(tallades) * 10 - len(retencions) * 5)
        elif len(retencions) >= 2:
            nivel = "elevado"
            score = max(35, 70 - len(retencions) * 7)
        elif retencions:
            nivel = "normal"
            score = max(50, 75 - len(retencions) * 5)
        elif obres:
            nivel = "normal"
            score = max(65, 85 - len(obres) * 2)
        else:
            nivel = "normal"
            score = 90

        roads_affected = list({i["carretera"] for i in retencions + tallades})
        roads_affected.sort()

        resumen = self._gen_resumen(retencions, tallades, roads_affected)
        razones = self._gen_razones(retencions, tallades, obres, roads_affected)

        return {
            "nivel": nivel,
            "score": score,
            "resumen": resumen,
            "razones": razones,
            "total_incidencias": total,
            "retenciones": len(retencions),
            "carreteras_cortadas": len(tallades),
            "obras": len(obres),
            "carreteras_afectadas": roads_affected,
            "incidencias": incidents[:15],
            "fuente": "Servei Català de Trànsit",
            "datos_reales": True,
        }

    @staticmethod
    def _gen_resumen(retencions: list, tallades: list, roads: list[str]) -> dict:
        if tallades:
            road_list = ", ".join(r["carretera"] for r in tallades[:3])
            return _t("sct.roads_cut", roads=road_list, count=len(tallades))
        if retencions:
            road_list = ", ".join(roads[:4])
            return _t("sct.retentions", roads=road_list, count=len(retencions))
        return _t("sct.metro_ok")

    @staticmethod
    def _gen_razones(retencions: list, tallades: list, obres: list, roads: list[str]) -> list:
        razones = []
        if tallades:
            for t in tallades[:3]:
                razones.append(_t(
                    "sct.cut_detail",
                    road=t["carretera"],
                    causa=t["causa"],
                    hacia=t.get("hacia", ""),
                ))
        if retencions:
            for r in retencions[:5]:
                razones.append(_t(
                    "sct.retention_detail",
                    road=r["carretera"],
                    causa=r["causa"],
                    hacia=r.get("hacia", ""),
                ))
        if obres and not retencions and not tallades:
            razones.append(_t("sct.works_only", count=len(obres)))
        if not razones:
            razones.append(_t("sct.no_incidents"))
        return razones

    @staticmethod
    def _fallback() -> dict:
        return {
            "nivel": "normal",
            "score": 50,
            "resumen": _t("sct.fallback"),
            "razones": [_t("sct.fallback_error")],
            "total_incidencias": 0,
            "retenciones": 0,
            "carreteras_cortadas": 0,
            "obras": 0,
            "carreteras_afectadas": [],
            "incidencias": [],
            "fuente": "SCT",
            "datos_reales": False,
        }
