"""Servicio principal de orquestación — SempreTard.

Coordina todas las consultas en paralelo y monta la respuesta final.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from core.recommender import recommend
from i18n import _t

if TYPE_CHECKING:
    from cache.store import CacheStore
    from config import Settings
    from services.bicing import BicingService
    from services.events import EventService
    from services.holidays import HolidayService
    from services.sct import SCTService
    from services.traffic import TrafficService
    from services.transport import TransportService
    from services.weather import WeatherService

logger = logging.getLogger(__name__)

_DIAS_SEMANA = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo",
}

_CACHE_KEY = "sempretard:estado"
_CACHE_TTL = 5 * 60


class StatusService:

    def __init__(
        self,
        *,
        traffic: TrafficService,
        transport: TransportService,
        bicing: BicingService,
        weather: WeatherService,
        events: EventService,
        holidays: HolidayService,
        sct: SCTService | None = None,
        cache: CacheStore,
        settings: Settings,
    ) -> None:
        self._traffic = traffic
        self._transport = transport
        self._bicing = bicing
        self._weather = weather
        self._events = events
        self._holidays = holidays
        self._sct = sct
        self._cache = cache
        self._settings = settings

    async def get_estado(self) -> dict:
        cached = self._cache.get(_CACHE_KEY)
        if cached:
            return {**cached, "_cache_hit": True}

        try:
            result = await self._build_estado()
        except Exception as exc:
            logger.error("_build_estado fallo completo: %s", exc, exc_info=True)
            now = datetime.now()
            result = self._emergency_fallback(now)

        self._cache.put(_CACHE_KEY, result, _CACHE_TTL)
        return {**result, "_cache_hit": False}

    async def _build_estado(self) -> dict:
        now = datetime.now()

        coros = [
            self._traffic.get_realtime_status(),
            self._transport.get_all_status(),
            self._bicing.get_realtime_status(),
            self._weather.get_forecast_7days(),
            self._events.get_events_7days(),
            self._holidays.get_catalan_holidays(now.year),
        ]
        if self._sct:
            coros.append(self._sct.get_metro_incidents())

        results = await asyncio.gather(*coros, return_exceptions=True)

        traffic_data = results[0]
        transport_data = results[1]
        bicing_data = results[2]
        weather_raw = results[3]
        events_raw = results[4]
        holidays_raw = results[5]
        sct_data = results[6] if len(results) > 6 else None

        if isinstance(traffic_data, Exception):
            logger.error("Traffic fallo: %s", traffic_data)
            traffic_data = self._modo_fallback("coche")

        if isinstance(transport_data, Exception):
            logger.error("Transport fallo: %s", transport_data)
            transport_data = {
                m: self._modo_fallback(m)
                for m in ("metro", "bus", "tren")
            }

        if isinstance(bicing_data, Exception):
            logger.error("Bicing fallo: %s", bicing_data)
            bicing_data = self._modo_fallback("bicing")

        if isinstance(sct_data, Exception):
            logger.error("SCT fallo: %s", sct_data)
            sct_data = None

        if sct_data and isinstance(sct_data, dict) and sct_data.get("datos_reales"):
            traffic_data = self._merge_traffic_sct(traffic_data, sct_data)

        modos = {
            "coche": traffic_data,
            "metro": transport_data.get("metro", {}),
            "bus": transport_data.get("bus", {}),
            "tren": transport_data.get("tren", {}),
            "bicing": bicing_data,
        }

        clima = self._extract_clima(weather_raw, now)
        eventos_hoy = self._extract_eventos(events_raw, now)
        es_festivo = self._check_festivo(holidays_raw, now)

        recomendacion = recommend(
            modos=modos,
            clima=clima,
            eventos_hoy=eventos_hoy,
            hora=now.hour,
        )

        fuentes = {}
        for modo, data in modos.items():
            fuentes[modo] = {
                "fuente": data.get("fuente", "desconocido"),
                "datos_reales": data.get("datos_reales", False),
            }

        return {
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S"),
            "modos": modos,
            "recomendacion": recomendacion,
            "contexto": {
                "clima": clima,
                "es_festivo": es_festivo,
                "dia_semana": _DIAS_SEMANA.get(now.weekday(), ""),
                "hora": now.strftime("%H:%M"),
                "eventos_hoy": eventos_hoy,
            },
            "fuentes": fuentes,
        }

    @staticmethod
    def _extract_clima(weather_raw, now: datetime) -> dict:
        """Extrae clima de hoy de la lista de 7 dias del WeatherService."""
        if isinstance(weather_raw, Exception) or not weather_raw:
            return {"temperatura": None, "lluvia_mm": 0, "descripcion": "Sin datos"}
        if not isinstance(weather_raw, list) or len(weather_raw) == 0:
            return {"temperatura": None, "lluvia_mm": 0, "descripcion": "Sin datos"}
        hoy = weather_raw[0]
        return {
            "temperatura": hoy.get("tmax"),
            "lluvia_mm": hoy.get("lluvia_mm", 0),
            "descripcion": hoy.get("descripcion", ""),
        }

    @staticmethod
    def _extract_eventos(events_raw, now: datetime) -> list:
        """Extrae eventos de hoy de la lista de 7 dias del EventService."""
        if isinstance(events_raw, Exception) or not events_raw:
            return []
        if not isinstance(events_raw, list):
            return []
        hoy = now.date()
        for day_data in events_raw:
            fecha = day_data.get("fecha")
            if fecha == hoy:
                nombres = day_data.get("eventos_nombres", [])
                destacados = day_data.get("eventos_destacados", [])
                return destacados if destacados else [{"nombre": n} for n in nombres]
        return []

    @staticmethod
    def _check_festivo(holidays_raw, now: datetime) -> bool:
        """Comprueba si hoy es festivo a partir del set de dates."""
        if isinstance(holidays_raw, Exception) or not holidays_raw:
            return False
        return now.date() in holidays_raw

    @staticmethod
    def _merge_traffic_sct(traffic: dict, sct: dict) -> dict:
        """Combina datos del tráfico municipal con incidencias SCT metropolitanas."""
        sct_retenciones = sct.get("retenciones", 0)
        sct_cortadas = sct.get("carreteras_cortadas", 0)
        sct_roads = sct.get("carreteras_afectadas", [])

        analisis = traffic.get("analisis", {})
        analisis["sct_retenciones"] = sct_retenciones
        analisis["sct_cortadas"] = sct_cortadas
        analisis["sct_carreteras_afectadas"] = sct_roads
        analisis["sct_total_incidencias"] = sct.get("total_incidencias", 0)
        traffic["analisis"] = analisis

        if sct_cortadas > 0 or sct_retenciones >= 3:
            penalty = sct_cortadas * 12 + sct_retenciones * 5
            traffic["score"] = max(5, traffic.get("score", 50) - penalty)
            if traffic["score"] < 30:
                traffic["nivel"] = "critico"
            elif traffic["score"] < 55:
                traffic["nivel"] = "elevado"

        elif sct_retenciones > 0:
            penalty = sct_retenciones * 4
            traffic["score"] = max(15, traffic.get("score", 50) - penalty)
            if traffic["score"] < 55 and traffic.get("nivel") == "normal":
                traffic["nivel"] = "elevado"

        sct_razones = sct.get("razones", [])
        if sct_razones:
            existing = traffic.get("razones", [])
            traffic["razones"] = existing + sct_razones

        return traffic

    @staticmethod
    def _modo_fallback(modo: str) -> dict:
        return {
            "modo": modo,
            "nivel": "normal",
            "score": 50,
            "resumen": _t("transport.fallback_no_data", label=modo),
            "razones": [],
            "fuente": "fallback",
            "datos_reales": False,
            "analisis": {},
        }

    @staticmethod
    def _emergency_fallback(now: datetime) -> dict:
        modos_ids = ["coche", "metro", "bus", "tren", "bicing"]
        modos = {}
        for m in modos_ids:
            modos[m] = {
                "modo": m,
                "nivel": "normal",
                "score": 50,
                "resumen": _t("transport.fallback_no_data", label=m),
                "razones": [],
                "fuente": "fallback",
                "datos_reales": False,
                "analisis": {},
            }

        return {
            "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S"),
            "modos": modos,
            "recomendacion": {
                "mejor": "metro",
                "mejor_label": "Metro",
                "score": 50,
                "explicacion": [_t("rec.best_now", label="Metro")],
                "ranking": modos_ids,
                "scores_ajustados": {m: 50 for m in modos_ids},
            },
            "contexto": {
                "clima": {"temperatura": None, "lluvia_mm": 0, "descripcion": "Sin datos"},
                "es_festivo": False,
                "dia_semana": _DIAS_SEMANA.get(now.weekday(), ""),
                "hora": now.strftime("%H:%M"),
                "eventos_hoy": [],
            },
            "fuentes": {m: {"fuente": "fallback", "datos_reales": False} for m in modos_ids},
        }
