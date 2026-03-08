"""Servicio de historial — almacena snapshots periódicos del estado de transporte.

Guarda un snapshot cada vez que se llama a save_snapshot().
Diseñado para ser llamado por un cron/scheduler cada 15 minutos.
Los datos se guardan en SQLite para simplicidad y portabilidad.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)

_DB_NAME = "history.db"


class HistoryService:

    def __init__(self, settings: Settings) -> None:
        db_path = settings.data_dir / _DB_NAME
        self._db_path = str(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    weekday INTEGER NOT NULL,
                    is_holiday INTEGER NOT NULL DEFAULT 0,
                    rain_mm REAL NOT NULL DEFAULT 0,
                    has_event INTEGER NOT NULL DEFAULT 0,
                    coche_score INTEGER,
                    metro_score INTEGER,
                    bus_score INTEGER,
                    tren_score INTEGER,
                    bicing_score INTEGER,
                    coche_nivel TEXT,
                    metro_nivel TEXT,
                    bus_nivel TEXT,
                    tren_nivel TEXT,
                    bicing_nivel TEXT,
                    traffic_congested INTEGER DEFAULT 0,
                    traffic_cut INTEGER DEFAULT 0,
                    metro_incidents INTEGER DEFAULT 0,
                    bus_incidents INTEGER DEFAULT 0,
                    tren_incidents INTEGER DEFAULT 0,
                    raw_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_ts
                ON snapshots(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_hour_weekday
                ON snapshots(hour, weekday)
            """)

    def save_snapshot(self, estado: dict) -> None:
        now = datetime.now()
        modos = estado.get("modos", {})
        contexto = estado.get("contexto", {})
        clima = contexto.get("clima", {})

        coche = modos.get("coche", {})
        metro = modos.get("metro", {})
        bus = modos.get("bus", {})
        tren = modos.get("tren", {})
        bicing = modos.get("bicing", {})

        coche_analisis = coche.get("analisis", {})
        metro_analisis = metro.get("analisis", {})
        bus_analisis = bus.get("analisis", {})
        tren_analisis = tren.get("analisis", {})

        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("""
                    INSERT INTO snapshots (
                        timestamp, hour, weekday, is_holiday, rain_mm, has_event,
                        coche_score, metro_score, bus_score, tren_score, bicing_score,
                        coche_nivel, metro_nivel, bus_nivel, tren_nivel, bicing_nivel,
                        traffic_congested, traffic_cut,
                        metro_incidents, bus_incidents, tren_incidents,
                        raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    now.isoformat(),
                    now.hour,
                    now.weekday(),
                    int(contexto.get("es_festivo", False)),
                    clima.get("lluvia_mm", 0) or 0,
                    int(len(contexto.get("eventos_hoy", [])) > 0),
                    coche.get("score"),
                    metro.get("score"),
                    bus.get("score"),
                    tren.get("score"),
                    bicing.get("score"),
                    coche.get("nivel"),
                    metro.get("nivel"),
                    bus.get("nivel"),
                    tren.get("nivel"),
                    bicing.get("nivel"),
                    coche_analisis.get("congestionado", 0) or 0,
                    coche_analisis.get("cortado", 0) or 0,
                    len(metro_analisis.get("detalle", [])),
                    len(bus_analisis.get("detalle", [])),
                    len(tren_analisis.get("detalle", [])),
                    json.dumps(estado, default=str),
                ))
            logger.info("Snapshot guardado: %s", now.isoformat())
        except Exception as exc:
            logger.error("Error guardando snapshot: %s", exc)

    def get_historical_pattern(self, weekday: int, hour: int) -> dict | None:
        """Obtiene el patrón histórico promedio para un día/hora específico."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("""
                    SELECT
                        AVG(coche_score) as avg_coche,
                        AVG(metro_score) as avg_metro,
                        AVG(bus_score) as avg_bus,
                        AVG(tren_score) as avg_tren,
                        AVG(bicing_score) as avg_bicing,
                        AVG(traffic_congested) as avg_congested,
                        AVG(traffic_cut) as avg_cut,
                        AVG(metro_incidents) as avg_metro_inc,
                        AVG(bus_incidents) as avg_bus_inc,
                        AVG(tren_incidents) as avg_tren_inc,
                        COUNT(*) as sample_count
                    FROM snapshots
                    WHERE weekday = ? AND hour = ?
                    AND timestamp > ?
                """, (
                    weekday,
                    hour,
                    (datetime.now() - timedelta(days=90)).isoformat(),
                )).fetchone()

                if not rows or rows["sample_count"] < 3:
                    return None

                return {
                    "coche": int(rows["avg_coche"] or 50),
                    "metro": int(rows["avg_metro"] or 50),
                    "bus": int(rows["avg_bus"] or 50),
                    "tren": int(rows["avg_tren"] or 50),
                    "bicing": int(rows["avg_bicing"] or 50),
                    "traffic_congested": round(rows["avg_congested"] or 0, 1),
                    "traffic_cut": round(rows["avg_cut"] or 0, 1),
                    "metro_incidents": round(rows["avg_metro_inc"] or 0, 1),
                    "sample_count": rows["sample_count"],
                }
        except Exception as exc:
            logger.error("Error obteniendo patrón histórico: %s", exc)
            return None

    def get_weekly_patterns(self) -> list[dict]:
        """Obtiene patrones promedio para cada día de la semana por franja."""
        franjas = [
            ("manana", 7, 10),
            ("mediodia", 10, 14),
            ("tarde", 14, 18),
            ("noche", 18, 22),
        ]
        patterns = []
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                for weekday in range(7):
                    day_franjas = []
                    for fid, h_start, h_end in franjas:
                        row = conn.execute("""
                            SELECT
                                AVG(coche_score) as avg_coche,
                                AVG(metro_score) as avg_metro,
                                AVG(bus_score) as avg_bus,
                                AVG(tren_score) as avg_tren,
                                AVG(bicing_score) as avg_bicing,
                                COUNT(*) as n
                            FROM snapshots
                            WHERE weekday = ? AND hour >= ? AND hour < ?
                            AND timestamp > ?
                        """, (
                            weekday, h_start, h_end,
                            (datetime.now() - timedelta(days=90)).isoformat(),
                        )).fetchone()

                        if row and row["n"] >= 2:
                            day_franjas.append({
                                "franja": fid,
                                "scores": {
                                    "coche": int(row["avg_coche"] or 50),
                                    "metro": int(row["avg_metro"] or 50),
                                    "bus": int(row["avg_bus"] or 50),
                                    "tren": int(row["avg_tren"] or 50),
                                    "bicing": int(row["avg_bicing"] or 50),
                                },
                                "samples": row["n"],
                            })

                    patterns.append({
                        "weekday": weekday,
                        "franjas": day_franjas,
                        "has_data": len(day_franjas) > 0,
                    })
        except Exception as exc:
            logger.error("Error obteniendo patrones semanales: %s", exc)

        return patterns
