"""Servicio de proximidad — filtra datos por ubicación del usuario.

Calcula distancias con la fórmula Haversine y devuelve los elementos
más relevantes según la posición del usuario.
"""
from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from i18n import _t

if TYPE_CHECKING:
    from services.bicing import BicingService
    from services.traffic import TrafficService

logger = logging.getLogger(__name__)

_EARTH_R_KM = 6371


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en metros entre dos puntos GPS."""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return _EARTH_R_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)) * 1000


_METRO_STATIONS: list[dict] = [
    {"name": "Catalunya", "lat": 41.3870, "lon": 2.1700, "lines": ["L1", "L3"]},
    {"name": "Passeig de Gràcia", "lat": 41.3916, "lon": 2.1650, "lines": ["L2", "L3", "L4"]},
    {"name": "Universitat", "lat": 41.3866, "lon": 2.1635, "lines": ["L1", "L2"]},
    {"name": "Diagonal", "lat": 41.3946, "lon": 2.1613, "lines": ["L3", "L5"]},
    {"name": "Sants Estació", "lat": 41.3790, "lon": 2.1404, "lines": ["L3", "L5"]},
    {"name": "Sagrada Família", "lat": 41.4037, "lon": 2.1744, "lines": ["L2", "L5"]},
    {"name": "Arc de Triomf", "lat": 41.3910, "lon": 2.1808, "lines": ["L1"]},
    {"name": "Espanya", "lat": 41.3756, "lon": 2.1490, "lines": ["L1", "L3"]},
    {"name": "Hospital de Bellvitge", "lat": 41.3466, "lon": 2.1086, "lines": ["L1"]},
    {"name": "Fondo", "lat": 41.4382, "lon": 2.2342, "lines": ["L1"]},
    {"name": "Paral·lel", "lat": 41.3752, "lon": 2.1684, "lines": ["L2", "L3"]},
    {"name": "Clot", "lat": 41.4094, "lon": 2.1879, "lines": ["L1", "L2"]},
    {"name": "La Pau", "lat": 41.4184, "lon": 2.1990, "lines": ["L2", "L4"]},
    {"name": "Verdaguer", "lat": 41.3993, "lon": 2.1679, "lines": ["L4", "L5"]},
    {"name": "Urquinaona", "lat": 41.3886, "lon": 2.1722, "lines": ["L1", "L4"]},
    {"name": "Glòries", "lat": 41.4048, "lon": 2.1874, "lines": ["L1"]},
    {"name": "Sant Andreu", "lat": 41.4349, "lon": 2.1891, "lines": ["L1"]},
    {"name": "Trinitat Nova", "lat": 41.4503, "lon": 2.1859, "lines": ["L3", "L4", "L11"]},
    {"name": "Cornellà Centre", "lat": 41.3546, "lon": 2.0705, "lines": ["L5"]},
    {"name": "Zona Universitària", "lat": 41.3870, "lon": 2.1133, "lines": ["L3"]},
    {"name": "Collblanc", "lat": 41.3789, "lon": 2.1275, "lines": ["L5"]},
    {"name": "Lesseps", "lat": 41.4026, "lon": 2.1538, "lines": ["L3"]},
    {"name": "El Maresme-Fòrum", "lat": 41.4109, "lon": 2.2177, "lines": ["L4"]},
    {"name": "Badalona Pompeu Fabra", "lat": 41.4379, "lon": 2.2343, "lines": ["L2"]},
    {"name": "Can Cuiàs", "lat": 41.4614, "lon": 2.1724, "lines": ["L11"]},
    {"name": "Aeroport T1", "lat": 41.2909, "lon": 2.0671, "lines": ["L9 Sud"]},
    {"name": "Aeroport T2", "lat": 41.2989, "lon": 2.0784, "lines": ["L9 Sud"]},
    {"name": "Fira", "lat": 41.3573, "lon": 2.1259, "lines": ["L9 Sud"]},
    {"name": "Europa|Fira", "lat": 41.3608, "lon": 2.1267, "lines": ["L9 Sud"]},
    {"name": "Bon Pastor", "lat": 41.4324, "lon": 2.2036, "lines": ["L9 Nord", "L10 Nord"]},
]

_RODALIES_STATIONS: list[dict] = [
    {"name": "Sants", "lat": 41.3790, "lon": 2.1400, "lines": ["R1", "R2", "R3", "R4"]},
    {"name": "Passeig de Gràcia", "lat": 41.3916, "lon": 2.1650, "lines": ["R1", "R2", "R3", "R4"]},
    {"name": "Arc de Triomf", "lat": 41.3910, "lon": 2.1808, "lines": ["R1", "R3", "R4"]},
    {"name": "Plaça Catalunya", "lat": 41.3870, "lon": 2.1700, "lines": ["R1", "R3", "R4"]},
    {"name": "Clot-Aragó", "lat": 41.4094, "lon": 2.1879, "lines": ["R1", "R2"]},
    {"name": "Sant Andreu Comtal", "lat": 41.4349, "lon": 2.1891, "lines": ["R1", "R2", "R3"]},
    {"name": "El Prat", "lat": 41.3210, "lon": 2.0968, "lines": ["R2"]},
    {"name": "Bellvitge", "lat": 41.3523, "lon": 2.1063, "lines": ["R2"]},
]


class NearbyService:

    def __init__(self, *, bicing: BicingService, traffic: TrafficService) -> None:
        self._bicing = bicing
        self._traffic = traffic

    async def get_nearby(self, lat: float, lon: float) -> dict:
        import asyncio

        bicing_stations, traffic_map = await asyncio.gather(
            self._bicing.get_map_stations(),
            self._traffic.get_map_data(),
            return_exceptions=True,
        )

        if isinstance(bicing_stations, Exception):
            bicing_stations = []
        if isinstance(traffic_map, Exception):
            traffic_map = {"vias_afectadas": []}

        nearby_bicing = self._nearest_bicing(lat, lon, bicing_stations)
        nearby_traffic = self._nearest_traffic(lat, lon, traffic_map.get("vias_afectadas", []))
        nearby_metro = self._nearest_stations(lat, lon, _METRO_STATIONS, limit=5)
        nearby_rodalies = self._nearest_stations(lat, lon, _RODALIES_STATIONS, limit=3)

        proximity_context = self._build_proximity_context(
            lat, lon, nearby_metro, nearby_rodalies, nearby_bicing,
        )

        return {
            "ubicacion": {"lat": lat, "lon": lon},
            "bicing_cercano": nearby_bicing,
            "trafico_cercano": nearby_traffic,
            "metro_cercano": nearby_metro,
            "rodalies_cercano": nearby_rodalies,
            "contexto_proximidad": proximity_context,
        }

    @staticmethod
    def _nearest_bicing(lat: float, lon: float, stations: list[dict]) -> list[dict]:
        for s in stations:
            s["distancia_m"] = int(haversine(lat, lon, s["lat"], s["lon"]))
        stations.sort(key=lambda s: s["distancia_m"])
        return stations[:10]

    @staticmethod
    def _nearest_traffic(lat: float, lon: float, vias: list[dict]) -> list[dict]:
        result = []
        for v in vias:
            v_lat = v.get("lat")
            v_lon = v.get("lon")
            if v_lat is None or v_lon is None:
                continue
            dist = int(haversine(lat, lon, v_lat, v_lon))
            result.append({**v, "distancia_m": dist})
        result.sort(key=lambda x: x["distancia_m"])
        return [v for v in result if v["distancia_m"] < 3000][:10]

    @staticmethod
    def _nearest_stations(
        lat: float, lon: float, stations: list[dict], *, limit: int = 5,
    ) -> list[dict]:
        enriched = []
        for s in stations:
            dist = int(haversine(lat, lon, s["lat"], s["lon"]))
            enriched.append({**s, "distancia_m": dist})
        enriched.sort(key=lambda s: s["distancia_m"])
        return enriched[:limit]

    @staticmethod
    def _build_proximity_context(
        lat: float,
        lon: float,
        metros: list[dict],
        rodalies: list[dict],
        bicings: list[dict],
    ) -> dict:
        metro_near = metros[0]["distancia_m"] if metros else 99999
        rodalies_near = rodalies[0]["distancia_m"] if rodalies else 99999
        bicing_near = bicings[0]["distancia_m"] if bicings else 99999

        bicing_with_bikes = [
            b for b in bicings[:5] if b.get("bikes", 0) > 0
        ]
        bicing_avail_near = (
            bicing_with_bikes[0]["distancia_m"] if bicing_with_bikes else 99999
        )

        return {
            "metro_mas_cercano": {
                "nombre": metros[0]["name"] if metros else None,
                "distancia_m": metro_near,
                "lineas": metros[0].get("lines", []) if metros else [],
                "caminando_min": max(1, metro_near // 80),
            },
            "rodalies_mas_cercano": {
                "nombre": rodalies[0]["name"] if rodalies else None,
                "distancia_m": rodalies_near,
                "lineas": rodalies[0].get("lines", []) if rodalies else [],
                "caminando_min": max(1, rodalies_near // 80),
            },
            "bicing_mas_cercano": {
                "nombre": bicings[0].get("name") if bicings else None,
                "distancia_m": bicing_near,
                "bicis_disponibles": bicings[0].get("bikes", 0) if bicings else 0,
                "caminando_min": max(1, bicing_near // 80),
            },
            "bicing_con_bicis_cercano_m": bicing_avail_near,
            "ajustes_recomendacion": {
                "metro_bonus": 10 if metro_near < 500 else (5 if metro_near < 1000 else 0),
                "metro_penalty": -15 if metro_near > 2000 else (-5 if metro_near > 1000 else 0),
                "tren_bonus": 10 if rodalies_near < 600 else (5 if rodalies_near < 1200 else 0),
                "tren_penalty": -15 if rodalies_near > 3000 else (-5 if rodalies_near > 1500 else 0),
                "bicing_bonus": 8 if bicing_avail_near < 300 else (3 if bicing_avail_near < 600 else 0),
                "bicing_penalty": -20 if bicing_avail_near > 2000 else (-10 if bicing_avail_near > 1000 else 0),
            },
        }
