"""Servicio de Bicing — Open Data BCN (GBFS / Citybik.es fallback).

Estado en tiempo real de las estaciones de Bicing de Barcelona.
Fuente primaria: Open Data BCN (GBFS).
Fallback: Citybik.es API (público, sin key).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import aiohttp

from i18n import _t

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=12)

_STATION_INFO_URL = (
    "https://opendata-ajuntament.barcelona.cat"
    "/data/dataset/informacio-estacions-bicing"
    "/resource/f60e9291-5aaa-417d-9b91-612a9de800aa/download"
)
_STATION_STATUS_URL = (
    "https://opendata-ajuntament.barcelona.cat"
    "/data/dataset/estat-estacions-bicing"
    "/resource/1b215493-9e63-4a12-8980-2d7e0fa19f85/download"
)

_CITYBIKES_URL = "https://api.citybik.es/v2/networks/bicing"


class BicingService:

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_map_stations(self) -> list[dict]:
        """Estaciones con coordenadas para el mapa."""
        try:
            return await self._map_stations_gbfs()
        except Exception as exc:
            logger.warning("Bicing map GBFS fallo: %s, probando Citybik.es", exc)
            try:
                return await self._map_stations_citybikes()
            except Exception as exc2:
                logger.warning("Bicing map Citybik.es fallo: %s", exc2)
                return []

    async def _map_stations_gbfs(self) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(_STATION_INFO_URL, timeout=_TIMEOUT) as info_resp:
                info_resp.raise_for_status()
                info_data = await info_resp.json(content_type=None)

            async with session.get(_STATION_STATUS_URL, timeout=_TIMEOUT) as status_resp:
                status_resp.raise_for_status()
                status_data = await status_resp.json(content_type=None)

        info_stations = {
            s["station_id"]: s
            for s in info_data.get("data", {}).get("stations", [])
        }
        status_stations = status_data.get("data", {}).get("stations", [])

        result = []
        for s in status_stations:
            sid = s.get("station_id")
            info = info_stations.get(sid, {})
            lat = info.get("lat")
            lon = info.get("lon")
            if lat is None or lon is None:
                continue

            bikes = s.get("num_bikes_available", 0) or 0
            docks = s.get("num_docks_available", 0) or 0
            types = s.get("num_bikes_available_types", {})
            mechanical = 0
            electric = 0
            if isinstance(types, dict):
                mechanical = types.get("mechanical", 0) or 0
                electric = types.get("ebike", 0) or 0

            result.append({
                "id": sid,
                "name": info.get("name", f"Estació {sid}"),
                "lat": lat,
                "lon": lon,
                "bikes": bikes,
                "mechanical": mechanical,
                "electric": electric,
                "docks": docks,
                "status": s.get("status", "IN_SERVICE"),
            })
        if not result:
            raise RuntimeError("GBFS no devolvió estaciones")
        return result

    async def _map_stations_citybikes(self) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(_CITYBIKES_URL, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                data = await resp.json()

        raw_stations = data.get("network", {}).get("stations", [])
        if not raw_stations:
            raise RuntimeError("Citybik.es sin estaciones")

        result = []
        for s in raw_stations:
            lat = s.get("latitude")
            lon = s.get("longitude")
            if lat is None or lon is None:
                continue
            extra = s.get("extra", {})
            mechanical = extra.get("normal_bikes", 0) or 0
            electric = extra.get("ebikes", 0) or 0
            bikes = s.get("free_bikes", 0) or 0

            result.append({
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "lat": lat,
                "lon": lon,
                "bikes": bikes,
                "mechanical": mechanical,
                "electric": electric,
                "docks": s.get("empty_slots", 0) or 0,
                "status": "IN_SERVICE",
            })
        return result

    async def get_realtime_status(self) -> dict:
        try:
            return await self._fetch_gbfs()
        except Exception as exc:
            logger.warning("Bicing GBFS fallo (%s), probando Citybik.es", exc)
            try:
                return await self._fetch_citybikes()
            except Exception as exc2:
                logger.warning("Bicing Citybik.es fallo: %s", exc2)
                return self._fallback()

    async def _fetch_gbfs(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(_STATION_STATUS_URL, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)

        stations = data.get("data", {}).get("stations", [])
        if not stations:
            raise RuntimeError("GBFS sin estaciones")

        return self._build_result(stations, "Open Data BCN (GBFS)")

    async def _fetch_citybikes(self) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(_CITYBIKES_URL, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                data = await resp.json()

        raw_stations = data.get("network", {}).get("stations", [])
        if not raw_stations:
            raise RuntimeError("Citybik.es sin estaciones")

        stations = []
        for s in raw_stations:
            extra = s.get("extra", {})
            stations.append({
                "num_bikes_available": s.get("free_bikes", 0),
                "num_bikes_available_types": {
                    "mechanical": extra.get("normal_bikes", 0),
                    "ebike": extra.get("ebikes", 0),
                },
                "num_docks_available": s.get("empty_slots", 0),
                "is_renting": 1,
                "is_returning": 1,
                "status": "IN_SERVICE",
            })

        return self._build_result(stations, "Citybik.es")

    def _build_result(self, stations: list[dict], fuente: str) -> dict:
        total = len(stations)
        en_servicio = sum(
            1 for s in stations
            if s.get("status", "IN_SERVICE") == "IN_SERVICE"
        )
        fuera_servicio = total - en_servicio

        total_bikes = 0
        total_mechanical = 0
        total_electric = 0
        total_docks = 0
        empty_stations = 0
        full_stations = 0

        for s in stations:
            bikes = s.get("num_bikes_available", 0) or 0
            docks = s.get("num_docks_available", 0) or 0
            total_bikes += bikes
            total_docks += docks

            types = s.get("num_bikes_available_types", {})
            if isinstance(types, dict):
                total_mechanical += types.get("mechanical", 0) or 0
                total_electric += types.get("ebike", 0) or 0
            elif isinstance(types, list):
                for t in types:
                    if isinstance(t, dict):
                        total_mechanical += t.get("mechanical", 0) or 0
                        total_electric += t.get("ebike", 0) or 0

            if bikes == 0 and s.get("status") == "IN_SERVICE":
                empty_stations += 1
            if docks == 0 and bikes > 0:
                full_stations += 1

        capacidad_total = total_bikes + total_docks
        disponibilidad = (total_bikes / capacidad_total * 100) if capacidad_total > 0 else 0

        if en_servicio == 0:
            score = 0
            nivel = "critico"
        else:
            pct_fuera = fuera_servicio / total if total > 0 else 0
            pct_vacias = empty_stations / en_servicio if en_servicio > 0 else 0

            score = max(0, min(100, int(
                disponibilidad * 0.4
                + (1 - pct_fuera) * 100 * 0.3
                + (1 - pct_vacias) * 100 * 0.3
            )))

            if score >= 70:
                nivel = "normal"
            elif score >= 40:
                nivel = "elevado"
            else:
                nivel = "critico"

        razones = self._generar_razones(
            en_servicio, fuera_servicio, total_bikes, total_mechanical,
            total_electric, total_docks, empty_stations, full_stations,
        )

        resumen = self._generar_resumen(nivel, total_bikes, en_servicio, empty_stations)

        return {
            "modo": "bicing",
            "nivel": nivel,
            "score": score,
            "resumen": resumen,
            "analisis": {
                "estaciones_total": total,
                "estaciones_activas": en_servicio,
                "estaciones_fuera_servicio": fuera_servicio,
                "estaciones_vacias": empty_stations,
                "estaciones_llenas": full_stations,
                "bicis_disponibles": total_bikes,
                "bicis_mecanicas": total_mechanical,
                "bicis_electricas": total_electric,
                "anclajes_libres": total_docks,
                "disponibilidad_pct": round(disponibilidad, 1),
            },
            "razones": razones,
            "fuente": fuente,
            "datos_reales": True,
        }

    @staticmethod
    def _generar_resumen(nivel: str, total_bikes: int, en_servicio: int, empty: int):
        if en_servicio == 0:
            return _t("bicing.no_service")
        if nivel == "critico":
            return _t("bicing.critical", bikes=total_bikes, empty=empty)
        if nivel == "elevado":
            return _t("bicing.elevated", bikes=total_bikes, empty=empty)
        return _t("bicing.ok", bikes=total_bikes, stations=en_servicio)

    @staticmethod
    def _generar_razones(
        en_servicio: int, fuera: int, bikes: int, mechanical: int,
        electric: int, docks: int, empty: int, full: int,
    ):
        razones = []
        razones.append(_t("bicing.reason_bikes", bikes=bikes, mechanical=mechanical, electric=electric))
        razones.append(_t("bicing.reason_docks", docks=docks))
        razones.append(_t("bicing.reason_stations", active=en_servicio, out=fuera))
        if empty > 0:
            razones.append(_t("bicing.reason_empty", count=empty))
        if full > 0:
            razones.append(_t("bicing.reason_full", count=full))
        return razones

    @staticmethod
    def _fallback() -> dict:
        return {
            "modo": "bicing",
            "nivel": "normal",
            "score": 50,
            "resumen": _t("bicing.fallback"),
            "analisis": {},
            "razones": [_t("bicing.fallback_error")],
            "fuente": "fallback",
            "datos_reales": False,
        }
