"""Servicio de clima — Open-Meteo (primario) + AEMET (enriquecimiento).

Open-Meteo:  precipitacion en mm reales, siempre disponible.
AEMET:       temperaturas como enriquecimiento si hay API key.
Ambas se llaman en paralelo para minimizar latencia.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

import aiohttp

from exceptions import WeatherUnavailableError

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=10)
_AEMET_BCN_CODE = "0801900"


class WeatherService:

    def __init__(self, settings: Settings) -> None:
        self._aemet_key = settings.aemet_api_key
        self._lat = settings.bcn_lat
        self._lon = settings.bcn_lon
        self._has_aemet = settings.has_aemet

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def get_forecast_7days(self) -> list[dict]:
        """Pronostico de 7 dias combinando Open-Meteo + AEMET."""
        tasks: list = [self._fetch_open_meteo()]
        if self._has_aemet:
            tasks.append(self._fetch_aemet_temperatures())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        open_meteo_result = results[0]
        aemet_result = results[1] if len(results) > 1 else None

        if isinstance(open_meteo_result, Exception):
            logger.warning("Open-Meteo fallo: %s", open_meteo_result)
            if aemet_result and not isinstance(aemet_result, Exception):
                return self._build_aemet_fallback(aemet_result)
            raise WeatherUnavailableError(str(open_meteo_result))

        forecast = open_meteo_result
        if aemet_result and not isinstance(aemet_result, Exception):
            self._enrich_with_aemet(forecast, aemet_result)

        return forecast

    # ------------------------------------------------------------------
    # Open-Meteo
    # ------------------------------------------------------------------

    async def _fetch_open_meteo(self) -> list[dict]:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={self._lat}&longitude={self._lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
            f"precipitation_probability_max,weathercode"
            f"&forecast_days=7&timezone=Europe%2FMadrid"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                data = await resp.json()

        daily = data["daily"]
        return [
            {
                "fecha": daily["time"][i],
                "tmax": daily["temperature_2m_max"][i] or 20.0,
                "tmin": daily["temperature_2m_min"][i] or 12.0,
                "lluvia_mm": daily["precipitation_sum"][i] or 0.0,
                "prob_precipitacion": (
                    daily.get("precipitation_probability_max") or [None] * 7
                )[i] or 0,
                "descripcion": _wmo_description(daily["weathercode"][i] or 0),
                "fuente_temp": "Open-Meteo",
                "fuente_precip": "Open-Meteo",
            }
            for i in range(min(7, len(daily["time"])))
        ]

    # ------------------------------------------------------------------
    # AEMET
    # ------------------------------------------------------------------

    async def _fetch_aemet_temperatures(self) -> list[dict]:
        base_url = (
            "https://opendata.aemet.es/opendata/api/prediccion"
            f"/especifica/municipio/diaria/{_AEMET_BCN_CODE}"
        )
        headers = {"api_key": self._aemet_key}

        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, headers=headers, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                meta = await resp.json()
                data_url = meta.get("datos")
                if not data_url:
                    raise ValueError("AEMET no devolvio URL de datos")

            async with session.get(data_url, headers=headers, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                data = await resp.json()

        dias = data[0]["prediccion"]["dia"]
        result = []
        for dia in dias[:7]:
            tmax = _safe_float(dia.get("temperatura", {}).get("maxima"))
            tmin = _safe_float(dia.get("temperatura", {}).get("minima"))
            prob_entries = dia.get("probPrecipitacion", [])
            prob_max = max(
                (_safe_float(e.get("value")) or 0.0 for e in prob_entries),
                default=0.0,
            )
            result.append({
                "tmax": tmax,
                "tmin": tmin,
                "prob_precipitacion_aemet": prob_max,
            })
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _enrich_with_aemet(forecast: list[dict], aemet_temps: list[dict]) -> None:
        for i, day in enumerate(forecast):
            if i >= len(aemet_temps):
                break
            at = aemet_temps[i]
            if at.get("tmax") is not None:
                day["tmax"] = at["tmax"]
            if at.get("tmin") is not None:
                day["tmin"] = at["tmin"]
            day["fuente_temp"] = "AEMET"

    @staticmethod
    def _build_aemet_fallback(aemet_temps: list[dict]) -> list[dict]:
        return [
            {
                "fecha": str(date.today() + timedelta(days=i)),
                "tmax": at.get("tmax") or 20.0,
                "tmin": at.get("tmin") or 12.0,
                "lluvia_mm": 0.0,
                "prob_precipitacion": at.get("prob_precipitacion_aemet", 0),
                "descripcion": "Precipitacion no disponible (sin Open-Meteo)",
                "fuente_temp": "AEMET",
                "fuente_precip": "no_disponible",
            }
            for i, at in enumerate(aemet_temps[:7])
        ]


# ------------------------------------------------------------------
# Module-level pure functions
# ------------------------------------------------------------------

def _wmo_description(code: int) -> str:
    if code == 0:
        return "Despejado"
    if code in (1, 2):
        return "Parcialmente nublado"
    if code == 3:
        return "Nublado"
    if 51 <= code <= 67:
        return "Lluvia"
    if 71 <= code <= 77:
        return "Nieve"
    if 80 <= code <= 82:
        return "Chubascos"
    if 95 <= code <= 99:
        return "Tormenta"
    return "Variable"


def _safe_float(val: object) -> float | None:
    try:
        return float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
