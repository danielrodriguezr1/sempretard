"""Servicio de predicción — avisos para los próximos 7 días.

Combina datos reales de: clima (AEMET), eventos (Open Data BCN),
partidos FC Barcelona, y festivos para generar avisos por modo de transporte.
"""
from __future__ import annotations

import asyncio
from i18n import _t
import logging
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cache.store import CacheStore
    from config import Settings
    from services.events import EventService
    from services.history import HistoryService
    from services.holidays import HolidayService
    from services.weather import WeatherService

logger = logging.getLogger(__name__)

_CACHE_KEY = "sempretard:prediccion"
_CACHE_TTL = 30 * 60

_DIAS_SEMANA = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo",
}

_RAIN_THRESHOLD_MM = 5
_HEAVY_RAIN_MM = 15

_FRANJAS = [
    {"id": "manana",   "label": "Mañana",   "rango": "7–10h"},
    {"id": "mediodia", "label": "Mediodía", "rango": "10–14h"},
    {"id": "tarde",    "label": "Tarde",    "rango": "14–18h"},
    {"id": "noche",    "label": "Noche",    "rango": "18–22h"},
]

_BASE = {"coche": 82, "metro": 88, "bus": 78, "tren": 82, "bicing": 80}
_MODO_ICON = {"coche": "🚗", "metro": "🚇", "bus": "🚌", "tren": "🚆", "bicing": "🚲"}


class PredictionService:

    def __init__(
        self,
        *,
        weather: WeatherService,
        events: EventService,
        holidays: HolidayService,
        history: HistoryService | None = None,
        cache: CacheStore,
        settings: Settings,
    ) -> None:
        self._weather = weather
        self._events = events
        self._holidays = holidays
        self._history = history
        self._cache = cache

    async def get_prediccion(self) -> dict:
        cached = self._cache.get(_CACHE_KEY)
        if cached:
            return {**cached, "_cache_hit": True}

        result = await self._build()
        self._cache.put(_CACHE_KEY, result, _CACHE_TTL)
        return {**result, "_cache_hit": False}

    async def _build(self) -> dict:
        now = datetime.now()

        weather_raw, events_raw, holidays_raw = await asyncio.gather(
            self._weather.get_forecast_7days(),
            self._events.get_events_7days(),
            self._holidays.get_catalan_holidays(now.year),
            return_exceptions=True,
        )

        weather = weather_raw if isinstance(weather_raw, list) else []
        events = events_raw if isinstance(events_raw, list) else []
        holidays = holidays_raw if isinstance(holidays_raw, set) else set()

        dias = []
        for i in range(7):
            d = now.date() + timedelta(days=i)
            dia_weather = weather[i] if i < len(weather) else {}
            dia_events = events[i] if i < len(events) else {}
            dias.append(self._build_dia(d, dia_weather, dia_events, holidays))

        return {
            "generado_en": now.strftime("%Y-%m-%dT%H:%M:%S"),
            "dias": dias,
        }

    def _build_dia(
        self,
        d: date,
        weather: dict,
        events_data: dict,
        holidays: set,
    ) -> dict:
        es_festivo = d in holidays
        es_finde = d.weekday() >= 5

        lluvia = weather.get("lluvia_mm", 0) or 0
        temp = weather.get("tmax")
        desc_clima = weather.get("descripcion", "")

        n_eventos = events_data.get("n_eventos_dia", 0)
        evento_masivo = bool(events_data.get("evento_masivo"))
        partido_barca = bool(events_data.get("partido_barca_casa"))
        nombres_eventos = events_data.get("eventos_nombres", [])
        destacados = events_data.get("eventos_destacados", [])
        lineas_afectadas = events_data.get("lineas_afectadas_por_eventos", [])

        avisos = []

        # --- Avisos por clima ---
        if lluvia >= _HEAVY_RAIN_MM:
            avisos.append({
                "tipo": "clima",
                "nivel": "critico",
                "modos": ["coche", "bus"],
                "texto": _t("aviso.rain_heavy", mm=int(lluvia)),
            })
            avisos.append({
                "tipo": "clima",
                "nivel": "normal",
                "modos": ["metro", "tren"],
                "texto": _t("aviso.rain_metro_ok"),
            })
        elif lluvia >= _RAIN_THRESHOLD_MM:
            avisos.append({
                "tipo": "clima",
                "nivel": "elevado",
                "modos": ["coche", "bus"],
                "texto": _t("aviso.rain_moderate", mm=int(lluvia)),
            })

        # --- Avisos por eventos ---
        if partido_barca:
            avisos.append({
                "tipo": "evento",
                "nivel": "critico",
                "modos": ["coche", "metro"],
                "texto": _t("aviso.barca_match"),
                "lineas": ["L1", "L3", "L9S"],
            })

        if evento_masivo and not partido_barca:
            nombres = ", ".join(nombres_eventos[:3]) if nombres_eventos else "Evento masivo"
            avisos.append({
                "tipo": "evento",
                "nivel": "elevado",
                "modos": ["metro", "coche"],
                "texto": _t("aviso.massive_event", nombres=nombres),
                "lineas": lineas_afectadas[:5],
            })

        if n_eventos > 3 and not evento_masivo:
            avisos.append({
                "tipo": "evento",
                "nivel": "normal",
                "modos": ["metro"],
                "texto": _t("aviso.many_events", count=n_eventos),
            })

        # --- Avisos por día ---
        if es_festivo:
            avisos.append({
                "tipo": "festivo",
                "nivel": "normal",
                "modos": ["coche", "bus", "metro", "tren"],
                "texto": _t("aviso.holiday"),
            })

        if not es_finde and not es_festivo:
            avisos.append({
                "tipo": "patron",
                "nivel": "normal",
                "modos": ["coche", "bus"],
                "texto": _t("aviso.workday_rush"),
            })

        # --- Consejos prácticos (qué evitar y cuándo) ---
        consejos = self._generar_consejos(
            lluvia=lluvia,
            partido_barca=partido_barca,
            evento_masivo=evento_masivo,
            nombres_eventos=nombres_eventos,
            es_festivo=es_festivo,
            es_finde=es_finde,
        )

        # Score global del día
        score_dia = 80
        for a in avisos:
            if a["nivel"] == "critico":
                score_dia -= 25
            elif a["nivel"] == "elevado":
                score_dia -= 10
        score_dia = max(0, min(100, score_dia))

        nivel_dia = (
            "critico" if score_dia < 40
            else "elevado" if score_dia < 65
            else "normal"
        )

        historical_patterns = self._get_historical_for_day(d)

        franjas = self._generar_franjas(
            lluvia=lluvia,
            partido_barca=partido_barca,
            evento_masivo=evento_masivo,
            es_festivo=es_festivo,
            es_finde=es_finde,
            historical=historical_patterns,
        )

        return {
            "fecha": d.isoformat(),
            "dia_semana": _DIAS_SEMANA.get(d.weekday(), ""),
            "es_festivo": es_festivo,
            "es_finde": es_finde,
            "clima": {
                "temperatura": temp,
                "lluvia_mm": lluvia,
                "descripcion": desc_clima,
            },
            "eventos": {
                "total": n_eventos,
                "masivo": evento_masivo,
                "partido_barca": partido_barca,
                "destacados": destacados[:5],
                "nombres": nombres_eventos[:5],
                "lineas_afectadas": lineas_afectadas,
            },
            "avisos": avisos,
            "consejos": consejos,
            "franjas": franjas,
            "nivel": nivel_dia,
            "score": score_dia,
        }

    def _get_historical_for_day(self, d: date) -> dict:
        """Obtiene patrones históricos para cada franja del día."""
        if not self._history:
            return {}
        weekday = d.weekday()
        franja_hours = {"manana": 8, "mediodia": 12, "tarde": 16, "noche": 20}
        result = {}
        for fid, hour in franja_hours.items():
            pattern = self._history.get_historical_pattern(weekday, hour)
            if pattern:
                result[fid] = pattern
        return result

    @staticmethod
    def _generar_consejos(
        *,
        lluvia: float,
        partido_barca: bool,
        evento_masivo: bool,
        nombres_eventos: list,
        es_festivo: bool,
        es_finde: bool,
    ) -> list[dict]:
        consejos: list[dict] = []

        if partido_barca:
            consejos.append({
                "icono": "⚽",
                "texto": _t("consejo.barca_text"),
                "alternativa": _t("consejo.barca_alt"),
                "evitar": ["coche"],
                "mejor": ["metro", "tren"],
            })

        if evento_masivo and not partido_barca:
            nombre = nombres_eventos[0] if nombres_eventos else "evento masivo"
            consejos.append({
                "icono": "🎭",
                "texto": _t("consejo.event_text", nombre=nombre),
                "alternativa": _t("consejo.event_alt"),
                "evitar": ["coche"],
                "mejor": ["metro", "bus"],
            })

        if lluvia >= _HEAVY_RAIN_MM:
            consejos.append({
                "icono": "🌧",
                "texto": _t("consejo.rain_heavy_text", mm=int(lluvia)),
                "alternativa": _t("consejo.rain_heavy_alt"),
                "evitar": ["coche", "bus"],
                "mejor": ["metro", "tren"],
            })
        elif lluvia >= _RAIN_THRESHOLD_MM:
            consejos.append({
                "icono": "🌦",
                "texto": _t("consejo.rain_moderate_text", mm=int(lluvia)),
                "alternativa": _t("consejo.rain_moderate_alt"),
                "evitar": ["coche"],
                "mejor": ["metro"],
            })

        if not es_finde and not es_festivo:
            consejos.append({
                "icono": "⏰",
                "texto": _t("consejo.rush_text"),
                "alternativa": _t("consejo.rush_alt"),
                "evitar": ["coche"],
                "mejor": ["metro", "tren"],
            })

        if es_festivo:
            consejos.append({
                "icono": "📅",
                "texto": _t("consejo.holiday_text"),
                "alternativa": _t("consejo.holiday_alt"),
                "evitar": [],
                "mejor": ["coche"],
            })

        return consejos

    @staticmethod
    def _generar_franjas(
        *,
        lluvia: float,
        partido_barca: bool,
        evento_masivo: bool,
        es_festivo: bool,
        es_finde: bool,
        historical: dict | None = None,
    ) -> list[dict]:
        laborable = not es_finde and not es_festivo
        historical = historical or {}
        result = []

        for f in _FRANJAS:
            fid = f["id"]
            hist = historical.get(fid)

            if hist and hist.get("sample_count", 0) >= 5:
                scores = {
                    "coche": hist["coche"],
                    "metro": hist["metro"],
                    "bus": hist["bus"],
                    "tren": hist["tren"],
                    "bicing": hist.get("bicing", _BASE["bicing"]),
                }
                base_source = "historical"
            else:
                scores = dict(_BASE)
                base_source = "rules"

                if laborable and fid == "manana":
                    scores["coche"] -= 30
                    scores["bus"] -= 15
                elif laborable and fid == "noche":
                    scores["coche"] -= 20
                    scores["bus"] -= 10
                elif laborable and fid == "tarde":
                    scores["coche"] -= 8

                if es_finde or es_festivo:
                    scores["coche"] += 10
                    if es_festivo:
                        scores["metro"] -= 5
                        scores["bus"] -= 8
                        scores["tren"] -= 5

            if lluvia >= _HEAVY_RAIN_MM:
                scores["coche"] -= 30
                scores["bus"] -= 20
                scores["bicing"] -= 40
            elif lluvia >= _RAIN_THRESHOLD_MM:
                scores["coche"] -= 15
                scores["bus"] -= 10
                scores["bicing"] -= 25

            if (partido_barca or evento_masivo) and fid == "noche":
                scores["coche"] -= 30
                scores["metro"] -= 8
            elif (partido_barca or evento_masivo) and fid == "tarde":
                scores["coche"] -= 10

            for m in scores:
                scores[m] = max(0, min(100, scores[m]))

            mejor = max(scores, key=scores.get)  # type: ignore[arg-type]

            franja_data: dict = {
                "id": fid,
                "label": f["label"],
                "rango": f["rango"],
                "scores": scores,
                "mejor": mejor,
                "mejor_icon": _MODO_ICON[mejor],
                "score": scores[mejor],
                "source": base_source,
            }
            if hist:
                franja_data["historical_samples"] = hist.get("sample_count", 0)

            result.append(franja_data)

        return result
