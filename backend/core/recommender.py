"""Recomendador de modo de transporte.

Compara los scores en tiempo real de los 4 modos y recomienda
el mejor, teniendo en cuenta el contexto (clima, hora, eventos).
"""
from __future__ import annotations

from i18n import _t


_RAIN_PENALTY_COCHE = -5
_RAIN_PENALTY_BUS = -10
_RAIN_PENALTY_BICING = -25
_RAIN_BONUS_METRO = 5
_RAIN_BONUS_TREN = 3

_EVENT_PENALTY_COCHE = -10
_EVENT_PENALTY_METRO = -5

_NIGHT_PENALTY_METRO = -20
_NIGHT_PENALTY_TREN = -30
_NIGHT_PENALTY_BUS = -15
_NIGHT_PENALTY_BICING = -35

_MODE_LABELS = {
    "metro": "Metro",
    "bus": "Bus",
    "coche": "Coche",
    "tren": "Rodalies",
    "bicing": "Bicing",
}


def recommend(
    modos: dict[str, dict],
    clima: dict | None = None,
    eventos_hoy: list | None = None,
    hora: int = 12,
) -> dict:
    """Devuelve la recomendación con explicación basada en datos reales."""
    clima = clima or {}
    eventos_hoy = eventos_hoy or []

    lluvia = clima.get("lluvia_mm", 0) or 0
    llueve = lluvia > 1

    hay_eventos = len(eventos_hoy) > 0
    es_noche = hora < 6 or hora >= 23

    scores: dict[str, int] = {}
    for modo, data in modos.items():
        base = data.get("score", 50)
        ajuste = 0

        if llueve:
            if modo == "coche":
                ajuste += _RAIN_PENALTY_COCHE
            elif modo == "bus":
                ajuste += _RAIN_PENALTY_BUS
            elif modo == "bicing":
                ajuste += _RAIN_PENALTY_BICING
            elif modo == "metro":
                ajuste += _RAIN_BONUS_METRO
            elif modo == "tren":
                ajuste += _RAIN_BONUS_TREN

        if hay_eventos:
            if modo == "coche":
                ajuste += _EVENT_PENALTY_COCHE
            elif modo == "metro":
                ajuste += _EVENT_PENALTY_METRO

        if es_noche:
            if modo == "metro":
                ajuste += _NIGHT_PENALTY_METRO
            elif modo == "tren":
                ajuste += _NIGHT_PENALTY_TREN
            elif modo == "bus":
                ajuste += _NIGHT_PENALTY_BUS
            elif modo == "bicing":
                ajuste += _NIGHT_PENALTY_BICING

        scores[modo] = max(0, min(100, base + ajuste))

    ranking = sorted(scores, key=lambda m: scores[m], reverse=True)
    mejor = ranking[0]

    explicacion = _build_explanation(mejor, modos, llueve, hay_eventos, es_noche)

    return {
        "mejor": mejor,
        "mejor_label": _MODE_LABELS.get(mejor, mejor),
        "score": scores[mejor],
        "explicacion": explicacion,
        "ranking": ranking,
        "scores_ajustados": scores,
    }


def _build_explanation(
    mejor: str,
    modos: dict[str, dict],
    llueve: bool,
    hay_eventos: bool,
    es_noche: bool,
) -> list:
    data = modos.get(mejor, {})
    resumen = data.get("resumen")

    parts = [_t("rec.best_now", label=_MODE_LABELS.get(mejor, mejor))]

    if resumen:
        if isinstance(resumen, dict):
            parts.append(resumen)
        elif isinstance(resumen, str) and resumen:
            parts.append(resumen)

    if llueve and mejor == "metro":
        parts.append(_t("rec.rain_metro"))
    elif llueve and mejor == "tren":
        parts.append(_t("rec.rain_train"))
    elif llueve and mejor == "bicing":
        parts.append(_t("rec.rain_bicing"))

    if hay_eventos and mejor in ("metro", "tren"):
        parts.append(_t("rec.events_demand"))

    if es_noche and mejor == "coche":
        parts.append(_t("rec.night_reduced"))
    elif es_noche and mejor == "bicing":
        parts.append(_t("rec.night_bicing"))

    return parts
