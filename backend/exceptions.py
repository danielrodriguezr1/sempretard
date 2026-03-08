"""Jerarquia de excepciones de PredictaBCN.

Cada capa lanza excepciones tipadas para que la capa superior
pueda decidir como responder (HTTP 503, fallback, log, etc.).
"""


class PredictaBCNError(Exception):
    """Base para todas las excepciones de la aplicacion."""


class ExternalServiceError(PredictaBCNError):
    """Una API externa no respondio o devolvio error."""

    def __init__(self, service: str, detail: str = ""):
        self.service = service
        self.detail = detail
        super().__init__(f"[{service}] {detail}")


class WeatherUnavailableError(ExternalServiceError):
    def __init__(self, detail: str = ""):
        super().__init__("weather", detail)


class TransportUnavailableError(ExternalServiceError):
    def __init__(self, detail: str = ""):
        super().__init__("transport", detail)


class EventsUnavailableError(ExternalServiceError):
    def __init__(self, detail: str = ""):
        super().__init__("events", detail)


class ModelNotLoadedError(PredictaBCNError):
    """El modelo ML solicitado no esta en memoria."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        super().__init__(f"Modelo '{model_name}' no cargado")
