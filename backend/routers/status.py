"""Router principal — /api/estado + /api/prediccion + /api/mapa + /api/cercano."""
import asyncio

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get("/estado")
async def get_estado(request: Request):
    try:
        service = request.app.state.status_service
        return await service.get_estado()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/prediccion")
async def get_prediccion(request: Request):
    try:
        service = request.app.state.prediction_service
        return await service.get_prediccion()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/alertas")
async def get_alertas(request: Request):
    try:
        container = request.app.state.container
        return await container.alerts.get_active_alerts()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/historico/patrones")
async def get_patrones(request: Request):
    try:
        container = request.app.state.container
        patterns = container.history.get_weekly_patterns()
        return {"patrones": patterns}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/cercano")
async def get_cercano(
    request: Request,
    lat: float = Query(..., ge=40.5, le=42.5),
    lon: float = Query(..., ge=1.0, le=3.5),
):
    try:
        container = request.app.state.container
        return await container.nearby.get_nearby(lat, lon)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/mapa")
async def get_mapa(request: Request):
    try:
        container = request.app.state.container
        traffic_map, bicing_stations, sct_incidents = await asyncio.gather(
            container.traffic.get_map_data(),
            container.bicing.get_map_stations(),
            container.sct.get_map_incidents(),
            return_exceptions=True,
        )
        if isinstance(traffic_map, Exception):
            traffic_map = {"vias_afectadas": [], "resumen": {"nivel": "normal", "score": 50}}
        if isinstance(bicing_stations, Exception):
            bicing_stations = []
        if isinstance(sct_incidents, Exception):
            sct_incidents = []

        return {
            "trafico": traffic_map,
            "bicing": bicing_stations,
            "sct": sct_incidents,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/sct")
async def get_sct(request: Request):
    try:
        container = request.app.state.container
        return await container.sct.get_metro_incidents()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
