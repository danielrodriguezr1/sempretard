"""Helper para devolver textos traducibles al frontend."""
from __future__ import annotations


def _t(key: str, **params: str | int | float) -> dict:
    """Translatable object: { key, params }."""
    return {"key": key, "params": params} if params else {"key": key}
