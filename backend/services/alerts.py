"""Servicio de alertas — genera notificaciones cuando hay cambios significativos.

Compara el estado actual con umbrales configurables para decidir
si se debe alertar al usuario.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from i18n import _t

if TYPE_CHECKING:
    from cache.store import CacheStore
    from services.status_service import StatusService

logger = logging.getLogger(__name__)

_CACHE_KEY = "sempretard:alerts"
_CACHE_TTL = 2 * 60

_CRITICAL_THRESHOLD = 40
_INCIDENT_MODES = ["metro", "bus", "tren"]


class AlertService:

    def __init__(self, *, status: StatusService, cache: CacheStore) -> None:
        self._status = status
        self._cache = cache

    async def get_active_alerts(self) -> dict:
        cached = self._cache.get(_CACHE_KEY)
        if cached:
            return {**cached, "_cache_hit": True}

        result = await self._build_alerts()
        self._cache.put(_CACHE_KEY, result, _CACHE_TTL)
        return {**result, "_cache_hit": False}

    async def _build_alerts(self) -> dict:
        now = datetime.now()
        estado = await self._status.get_estado()
        modos = estado.get("modos", {})
        contexto = estado.get("contexto", {})

        alerts: list[dict] = []

        for modo_id, modo_data in modos.items():
            score = modo_data.get("score", 100)
            nivel = modo_data.get("nivel", "normal")
            datos_reales = modo_data.get("datos_reales", False)

            if not datos_reales:
                continue

            if nivel == "critico":
                alerts.append({
                    "id": f"{modo_id}_critical_{now.strftime('%Y%m%d%H')}",
                    "tipo": "critical",
                    "modo": modo_id,
                    "titulo": _t("alert.critical_title", modo=modo_id),
                    "mensaje": _t("alert.critical_msg", modo=modo_id, score=score),
                    "score": score,
                    "timestamp": now.isoformat(),
                    "prioridad": "alta",
                })
            elif nivel == "elevado" and score < _CRITICAL_THRESHOLD:
                alerts.append({
                    "id": f"{modo_id}_low_{now.strftime('%Y%m%d%H')}",
                    "tipo": "warning",
                    "modo": modo_id,
                    "titulo": _t("alert.warning_title", modo=modo_id),
                    "mensaje": _t("alert.warning_msg", modo=modo_id, score=score),
                    "score": score,
                    "timestamp": now.isoformat(),
                    "prioridad": "media",
                })

            if modo_id in _INCIDENT_MODES:
                detalle = modo_data.get("analisis", {}).get("detalle", [])
                if len(detalle) >= 3:
                    alerts.append({
                        "id": f"{modo_id}_many_incidents_{now.strftime('%Y%m%d%H')}",
                        "tipo": "incidents",
                        "modo": modo_id,
                        "titulo": _t("alert.incidents_title", modo=modo_id, count=len(detalle)),
                        "mensaje": _t("alert.incidents_msg", modo=modo_id, count=len(detalle)),
                        "score": score,
                        "timestamp": now.isoformat(),
                        "prioridad": "media",
                    })

        clima = contexto.get("clima", {})
        lluvia = clima.get("lluvia_mm", 0) or 0
        if lluvia >= 15:
            alerts.append({
                "id": f"rain_heavy_{now.strftime('%Y%m%d')}",
                "tipo": "weather",
                "modo": None,
                "titulo": _t("alert.rain_title"),
                "mensaje": _t("alert.rain_msg", mm=int(lluvia)),
                "score": None,
                "timestamp": now.isoformat(),
                "prioridad": "alta",
            })

        rec = estado.get("recomendacion", {})
        if rec:
            alerts.append({
                "id": f"recommendation_{now.strftime('%Y%m%d%H')}",
                "tipo": "recommendation",
                "modo": rec.get("mejor"),
                "titulo": _t("alert.rec_title"),
                "mensaje": _t("alert.rec_msg", modo=rec.get("mejor_label", "?")),
                "score": rec.get("score"),
                "timestamp": now.isoformat(),
                "prioridad": "baja",
            })

        alerts.sort(key=lambda a: {"alta": 0, "media": 1, "baja": 2}.get(a["prioridad"], 9))

        return {
            "alerts": alerts,
            "total": len(alerts),
            "hay_criticos": any(a["prioridad"] == "alta" for a in alerts),
            "timestamp": now.isoformat(),
        }
