"""SempreTard — Backend FastAPI.

Estado en tiempo real del transporte en Barcelona.
Datos reales de: Ajuntament BCN, TMB, Renfe, AEMET, Open Data BCN.

Arrancar con:  uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from cache.store import CacheStore
from config import Settings, get_settings
from routers.status import router as status_router
from services.alerts import AlertService
from services.bicing import BicingService
from services.events import EventService
from services.history import HistoryService
from services.nearby import NearbyService
from services.sct import SCTService
from services.holidays import HolidayService
from services.prediction_service import PredictionService
from services.status_service import StatusService
from services.traffic import TrafficService
from services.transport import TransportService
from services.weather import WeatherService

logger = logging.getLogger("sempretard")


class ServiceContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cache = CacheStore()

        self.traffic = TrafficService(settings)
        self.transport = TransportService(settings)
        self.bicing = BicingService(settings)
        self.weather = WeatherService(settings)
        self.events = EventService(settings)
        self.holidays = HolidayService()

        self.sct = SCTService()

        self.status = StatusService(
            traffic=self.traffic,
            transport=self.transport,
            bicing=self.bicing,
            weather=self.weather,
            events=self.events,
            holidays=self.holidays,
            sct=self.sct,
            cache=self.cache,
            settings=self.settings,
        )

        self.history = HistoryService(settings)

        self.prediction = PredictionService(
            weather=self.weather,
            events=self.events,
            holidays=self.holidays,
            history=self.history,
            cache=self.cache,
            settings=self.settings,
        )

        self.alerts = AlertService(
            status=self.status,
            cache=self.cache,
        )

        self.nearby = NearbyService(
            bicing=self.bicing,
            traffic=self.traffic,
        )


_SNAPSHOT_INTERVAL = 15 * 60


async def _snapshot_loop(container: ServiceContainer):
    """Guarda un snapshot del estado cada 15 minutos para el historial."""
    await asyncio.sleep(30)
    while True:
        try:
            estado = await container.status.get_estado()
            container.history.save_snapshot(estado)
        except Exception as exc:
            logger.warning("Snapshot fallo: %s", exc)
        await asyncio.sleep(_SNAPSHOT_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    container = ServiceContainer(settings)
    app.state.status_service = container.status
    app.state.prediction_service = container.prediction
    app.state.container = container

    snapshot_task = asyncio.create_task(_snapshot_loop(container))
    logger.info("SempreTard listo — todas las fuentes configuradas. Snapshot scheduler activo.")
    yield
    snapshot_task.cancel()
    logger.info("SempreTard apagándose.")


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    application = FastAPI(
        title="SempreTard API",
        description="Estado en tiempo real del transporte en Barcelona",
        version="4.0.0",
        lifespan=lifespan,
    )

    settings = get_settings()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            settings.frontend_url,
        ],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    application.include_router(status_router, prefix="/api", tags=["estado"])

    @application.get("/health", tags=["ops"])
    def health():
        return {"status": "ok", "version": "4.0.0"}

    return application


app = create_app()
