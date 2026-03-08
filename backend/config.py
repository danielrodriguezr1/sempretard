"""Configuracion centralizada de PredictaBCN.

Todas las variables de entorno se leen una sola vez aqui.
Los demas modulos reciben Settings por inyeccion de dependencias.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    # --- API keys ---
    aemet_api_key: str = ""
    tmb_app_id: str = ""
    tmb_app_key: str = ""
    renfe_api_key: str = ""
    football_api_key: str = ""

    # --- Paths ---
    models_dir: Path = _BASE_DIR / "models"
    data_dir: Path = _BASE_DIR / "data"

    # --- Server ---
    port: int = 8000
    frontend_url: str = "*"

    # --- Barcelona ---
    bcn_lat: float = 41.3874
    bcn_lon: float = 2.1686

    # --- Cache TTLs (seconds) ---
    cache_ttl_forecast: int = 6 * 3600
    cache_ttl_festivos: int = 7 * 86400
    cache_ttl_transporte: int = 30 * 60

    @property
    def has_aemet(self) -> bool:
        return bool(self.aemet_api_key)

    @property
    def has_tmb(self) -> bool:
        return bool(self.tmb_app_id and self.tmb_app_key)

    @property
    def has_football(self) -> bool:
        return bool(self.football_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Construye Settings a partir del entorno (.env)."""
    return Settings(
        aemet_api_key=os.getenv("AEMET_API_KEY", ""),
        tmb_app_id=os.getenv("TMB_APP_ID", ""),
        tmb_app_key=os.getenv("TMB_APP_KEY", ""),
        renfe_api_key=os.getenv("RENFE_API_KEY", ""),
        football_api_key=os.getenv("FOOTBALL_DATA_API_KEY", ""),
        port=int(os.getenv("PORT", "8000")),
        frontend_url=os.getenv("FRONTEND_URL", "*"),
    )
