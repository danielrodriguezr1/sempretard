"""
Schemas Pydantic — contratos de datos del API
"""
from pydantic import BaseModel
from typing import Literal
from datetime import date

NivelPresion = Literal["normal", "elevado", "critico"]


class ClimaDelDia(BaseModel):
    temperatura_max: float
    temperatura_min: float
    lluvia_mm: float
    descripcion: str


class IndiceServicio(BaseModel):
    indice: int                  # 0-100
    nivel: NivelPresion
    valor_crudo: float           # Valor real predicho (urgencias, viajes, etc.)
    intervalo_inferior: int      # Intervalo de confianza 80%
    intervalo_superior: int


class PronosticoDia(BaseModel):
    fecha: date
    dia_semana: str
    es_festivo: bool
    es_post_festivo: bool
    es_vispera_festivo: bool
    indice_global: int
    nivel_global: NivelPresion
    servicios: dict[str, IndiceServicio]  # hospitales, oacs, transporte
    clima: ClimaDelDia
    factores_activos: list[str]
    explicacion: str


class FuenteInfo(BaseModel):
    fuente: str
    actualizado: str
    estado: Literal["ok", "cache", "fallback"]


class ForecastResponse(BaseModel):
    generado_en: str
    ciudad: str
    dias_pronosticados: int
    pronostico: list[PronosticoDia]
    fuentes: dict[str, FuenteInfo]
    modelos_cargados: bool
