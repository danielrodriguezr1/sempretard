"""Servicio de tráfico por carretera — Ajuntament de Barcelona Open Data.

Descarga en tiempo real el estado de ~530 tramos de la red viaria.
Usa HTTP Range para obtener solo los últimos ~100 KB del CSV mensual,
evitando descargar el fichero completo (que crece durante el mes).

Fuente: https://opendata-ajuntament.barcelona.cat/data/dataset/trams
Licencia: CC-BY 4.0
"""
from __future__ import annotations

import csv
import io
import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp

from i18n import _t

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)

_TRAM_NAMES: dict[str, str] = {}


def _load_tram_names() -> None:
    global _TRAM_NAMES
    path = Path(__file__).resolve().parent.parent.parent / "data" / "trams_names.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _TRAM_NAMES = json.load(f)
        logger.info("Cargados %d nombres de tramos viarios", len(_TRAM_NAMES))
    else:
        logger.warning("trams_names.json no encontrado — sin nombres de vías")


_load_tram_names()

_TIMEOUT = aiohttp.ClientTimeout(total=15)
_RANGE_BYTES = 120_000

_ESTAT_LABELS = {
    "0": "sin_datos",
    "1": "muy_fluido",
    "2": "fluido",
    "3": "denso",
    "4": "muy_denso",
    "5": "congestionado",
    "6": "cortado",
}

_DATASET_ID = "8319c2b1-4c21-4962-9acd-6db4c5ff1148"
_BASE_URL = "https://opendata-ajuntament.barcelona.cat/data/dataset"

_MONTH_NAMES = {
    1: "Gener", 2: "Febrer", 3: "Marc", 4: "Abril",
    5: "Maig", 6: "Juny", 7: "Juliol", 8: "Agost",
    9: "Setembre", 10: "Octubre", 11: "Novembre", 12: "Desembre",
}

_RESOURCE_IDS: dict[str, str] = {
    "2026_03": "e7e20745-af8e-4652-9ac0-d024bd3d49bb",
    "2026_02": "0ed5dfa6-4071-4e0e-a6b7-4a1dc647b50b",
    "2026_01": "1309e26c-54c4-4847-a1b2-38deed9937ee",
    "2025_12": "fb9bda08-d820-4dcc-864d-41827d9a9f9e",
    "2025_11": "040d76d5-8647-48e9-b966-b4ca6393d9e7",
}


def _build_csv_url(resource_id: str) -> str:
    return f"{_BASE_URL}/{_DATASET_ID}/resource/{resource_id}/download"


def _current_resource_id() -> str:
    now = datetime.now()
    key = f"{now.year}_{now.month:02d}"
    if key in _RESOURCE_IDS:
        return _RESOURCE_IDS[key]
    prev_month = now.month - 1 or 12
    prev_year = now.year if now.month > 1 else now.year - 1
    fallback_key = f"{prev_year}_{prev_month:02d}"
    return _RESOURCE_IDS.get(fallback_key, list(_RESOURCE_IDS.values())[0])


class TrafficService:

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_realtime_status(self) -> dict:
        """Estado actual del tráfico en la red viaria de Barcelona."""
        try:
            return await self._fetch_latest_snapshot()
        except Exception as exc:
            logger.warning("TrafficService fallo: %s", exc)
            return self._fallback()

    async def _fetch_latest_snapshot(self) -> dict:
        resource_id = _current_resource_id()
        url = _build_csv_url(resource_id)

        async with aiohttp.ClientSession() as session:
            headers = {"Range": f"bytes=-{_RANGE_BYTES}"}
            async with session.get(url, headers=headers, timeout=_TIMEOUT) as resp:
                if resp.status not in (200, 206):
                    raise RuntimeError(f"HTTP {resp.status}")
                raw = await resp.text(encoding="utf-8", errors="ignore")
                was_partial = resp.status == 206

        lines = raw.strip().split("\n")
        if was_partial:
            lines = lines[1:]

        latest_ts = None
        records: list[dict[str, str]] = []

        for line in reversed(lines):
            parts = line.strip().split(",")
            if len(parts) != 4:
                continue
            ts = parts[1]
            if latest_ts is None:
                latest_ts = ts
            if ts != latest_ts:
                break
            records.append({
                "idTram": parts[0],
                "estatActual": parts[2],
                "estatPrevist": parts[3],
            })

        if not records or not latest_ts:
            raise RuntimeError("No se encontraron registros en el CSV")

        return self._build_result(records, latest_ts)

    def _build_result(self, records: list[dict], timestamp: str) -> dict:
        actual = Counter(r["estatActual"] for r in records)
        previst = Counter(r["estatPrevist"] for r in records)

        total = len(records)
        sin_datos = actual.get("0", 0)
        activos = total - sin_datos

        fluido = actual.get("1", 0) + actual.get("2", 0)
        denso = actual.get("3", 0)
        muy_denso = actual.get("4", 0)
        congestionado = actual.get("5", 0)
        cortado = actual.get("6", 0)

        problematicos = denso + muy_denso + congestionado + cortado

        if activos == 0:
            nivel = "normal"
            score = 50
        else:
            ratio_problemas = problematicos / activos
            ratio_grave = (muy_denso + congestionado + cortado) / activos

            if ratio_grave > 0.15 or cortado > 10:
                nivel = "critico"
            elif ratio_problemas > 0.25 or ratio_grave > 0.05:
                nivel = "elevado"
            else:
                nivel = "normal"

            score = max(0, min(100, int(100 * (1 - ratio_problemas * 2))))

        prevision = self._calcular_prevision(actual, previst)

        razones = self._generar_razones(
            activos, fluido, denso, muy_denso, congestionado, cortado, prevision,
        )

        try:
            dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
            ts_formatted = dt.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            ts_formatted = timestamp

        vias_afectadas = _build_vias_afectadas(records)

        return {
            "modo": "coche",
            "nivel": nivel,
            "score": score,
            "resumen": self._generar_resumen(nivel, problematicos, activos),
            "analisis": {
                "tramos_total": total,
                "tramos_activos": activos,
                "fluido": fluido,
                "denso": denso,
                "muy_denso": muy_denso,
                "congestionado": congestionado,
                "cortado": cortado,
                "prevision_15min": prevision,
                "vias_afectadas": vias_afectadas,
            },
            "razones": razones,
            "timestamp_datos": ts_formatted,
            "fuente": _t("traffic.source"),
            "datos_reales": True,
        }

    @staticmethod
    def _calcular_prevision(actual: Counter, previst: Counter) -> str:
        def _peso(c: Counter) -> float:
            return (
                c.get("3", 0) * 1
                + c.get("4", 0) * 2
                + c.get("5", 0) * 3
                + c.get("6", 0) * 4
            )

        diff = _peso(previst) - _peso(actual)
        if diff > 10:
            return "empeorando"
        if diff < -10:
            return "mejorando"
        return "estable"

    @staticmethod
    def _generar_resumen(nivel: str, problematicos: int, activos: int):
        if activos == 0:
            return _t("traffic.no_data")
        pct_ok = int(100 * (activos - problematicos) / activos) if activos else 0
        if nivel == "critico":
            return _t("traffic.very_congested", count=problematicos)
        if nivel == "elevado":
            return _t("traffic.dense_areas", count=problematicos)
        return _t("traffic.fluid", pct=pct_ok)

    @staticmethod
    def _generar_razones(
        activos: int, fluido: int, denso: int, muy_denso: int,
        congestionado: int, cortado: int, prevision: str,
    ):
        razones = []
        if activos == 0:
            return [_t("traffic.reason_no_sensors")]

        pct_fluido = int(100 * fluido / activos)
        razones.append(_t("traffic.reason_fluid", pct=pct_fluido, fluido=fluido, total=activos))

        if denso:
            razones.append(_t("traffic.reason_dense", count=denso))
        if muy_denso:
            razones.append(_t("traffic.reason_very_dense", count=muy_denso))
        if congestionado:
            razones.append(_t("traffic.reason_congested", count=congestionado))
        if cortado:
            razones.append(_t("traffic.reason_cut", count=cortado))

        prev_text = {
            "mejorando": _t("traffic.reason_improving"),
            "empeorando": _t("traffic.reason_worsening"),
            "estable": _t("traffic.reason_stable"),
        }
        val = prev_text.get(prevision)
        if val is not None:
            razones.append(val)
        return razones

    async def get_map_data(self) -> dict:
        """Datos de tráfico geolocalizados para el mapa."""
        try:
            status = await self.get_realtime_status()
            vias = status.get("analisis", {}).get("vias_afectadas", [])
            geo_vias = []
            for v in vias:
                coords = _TRAM_COORDS.get(v["id"])
                if coords:
                    geo_vias.append({**v, "lat": coords[0], "lon": coords[1]})
            return {
                "vias_afectadas": geo_vias,
                "resumen": {
                    "nivel": status.get("nivel", "normal"),
                    "score": status.get("score", 50),
                },
                "timestamp": status.get("timestamp_datos", ""),
            }
        except Exception as exc:
            logger.warning("Map data fallo: %s", exc)
            return {"vias_afectadas": [], "resumen": {"nivel": "normal", "score": 50}}

    @staticmethod
    def _fallback() -> dict:
        return {
            "modo": "coche",
            "nivel": "normal",
            "score": 50,
            "resumen": _t("traffic.fallback"),
            "analisis": {},
            "razones": [_t("traffic.fallback_error")],
            "timestamp_datos": "",
            "fuente": "fallback",
            "datos_reales": False,
        }


_SEVERITY_ORDER = {"6": 0, "5": 1, "4": 2, "3": 3}
_SEVERITY_LABEL = {"6": "Cortado", "5": "Congestionado", "4": "Muy denso", "3": "Denso"}


_TRAM_COORDS: dict[str, tuple[float, float]] = {
    "1": (41.3925, 2.1300), "2": (41.3925, 2.1310), "3": (41.3930, 2.1370),
    "4": (41.3930, 2.1380), "5": (41.3935, 2.1440), "6": (41.3935, 2.1450),
    "7": (41.3940, 2.1510), "8": (41.3940, 2.1520), "9": (41.3950, 2.1590),
    "10": (41.3950, 2.1600),
    "51": (41.4020, 2.1650), "52": (41.4020, 2.1660),
    "53": (41.4010, 2.1700), "54": (41.4010, 2.1710),
    "55": (41.4000, 2.1750), "56": (41.4000, 2.1760),
    "57": (41.3980, 2.1800), "58": (41.3980, 2.1810),
    "100": (41.3880, 2.1680), "101": (41.3880, 2.1690),
    "102": (41.3880, 2.1580), "103": (41.3880, 2.1590),
    "104": (41.3875, 2.1500), "105": (41.3875, 2.1510),
    "200": (41.4250, 2.1500), "201": (41.4250, 2.1510),
    "202": (41.4230, 2.1600), "203": (41.4230, 2.1610),
    "204": (41.4200, 2.1700), "205": (41.4200, 2.1710),
    "250": (41.4100, 2.1300), "251": (41.4100, 2.1310),
    "252": (41.4090, 2.1400), "253": (41.4090, 2.1410),
    "300": (41.3850, 2.1850), "301": (41.3850, 2.1860),
    "302": (41.3860, 2.1900), "303": (41.3860, 2.1910),
    "350": (41.4050, 2.1900), "351": (41.4050, 2.1910),
    "352": (41.4060, 2.1950), "353": (41.4060, 2.1960),
    "400": (41.3800, 2.1500), "401": (41.3800, 2.1510),
    "402": (41.3790, 2.1600), "403": (41.3790, 2.1610),
    "450": (41.4150, 2.2000), "451": (41.4150, 2.2010),
    "500": (41.3750, 2.1900), "501": (41.3750, 2.1910),
    "502": (41.3760, 2.1950), "503": (41.3760, 2.1960),
}


def _build_vias_afectadas(records: list[dict[str, str]]) -> list[dict]:
    """Extrae las vías con problemas, ordenadas por gravedad."""
    problemas = [
        r for r in records if r["estatActual"] in _SEVERITY_ORDER
    ]
    problemas.sort(key=lambda r: _SEVERITY_ORDER.get(r["estatActual"], 9))

    vias = []
    for r in problemas:
        tram_id = r["idTram"]
        nombre = _TRAM_NAMES.get(tram_id, f"Tramo {tram_id}")
        estado = _SEVERITY_LABEL.get(r["estatActual"], "?")
        prev_label = _SEVERITY_LABEL.get(r["estatPrevist"], _ESTAT_LABELS.get(r["estatPrevist"], "?"))
        vias.append({
            "id": tram_id,
            "via": nombre,
            "estado": estado,
            "prevision": prev_label,
        })

    return vias
