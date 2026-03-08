"""Servicio de festivos — Nager.Date API (publica, sin key)."""
from __future__ import annotations

import logging
from datetime import date

import aiohttp

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=8)
_NAGER_URL = "https://date.nager.at/api/v3/PublicHolidays"
_CATALAN_COUNTY = "ES-CT"

_FIXED_DATES = [
    (1, 1), (1, 6), (4, 23), (5, 1), (6, 24),
    (8, 15), (9, 11), (9, 24), (10, 12),
    (11, 1), (12, 6), (12, 8), (12, 25), (12, 26),
]


class HolidayService:

    async def get_catalan_holidays(self, year: int) -> set[date]:
        """Festivos nacionales + catalanes para un ano."""
        try:
            return await self._fetch_from_nager(year)
        except Exception as exc:
            logger.warning("Nager.Date fallo (%s), usando festivos fijos", exc)
            return self._fixed_fallback(year)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    async def _fetch_from_nager(self, year: int) -> set[date]:
        url = f"{_NAGER_URL}/{year}/ES"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=_TIMEOUT) as resp:
                resp.raise_for_status()
                data = await resp.json()

        holidays: set[date] = set()
        for entry in data:
            counties = entry.get("counties") or []
            is_national = not counties
            is_catalan = any(_CATALAN_COUNTY in c for c in counties)
            if is_national or is_catalan:
                holidays.add(date.fromisoformat(entry["date"]))
        return holidays

    @staticmethod
    def _fixed_fallback(year: int) -> set[date]:
        result: set[date] = set()
        for month, day in _FIXED_DATES:
            try:
                result.add(date(year, month, day))
            except ValueError:
                pass
        return result
