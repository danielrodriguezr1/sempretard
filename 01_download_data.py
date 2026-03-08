"""
PASO 1: Descarga de datos historicos REALES
=============================================
TODAS las fuentes son datos reales y publicos. No se generan datos sinteticos.

Fuentes:
  1. Clima historico: Open-Meteo Archive API (sin key, precipitacion real en mm)
  2. Festivos: Nager.Date API (sin key)
  3. Eventos Barcelona: Open Data BCN agenda (sin key)
  4. Partidos FC Barcelona: football-data.org (key gratuita, opcional)
  5. Rodalies 2018: Renfe Data CSV (sin key)

API keys necesarias (gratuitas):
  - FOOTBALL_DATA_API_KEY: https://www.football-data.org/client/register (opcional)
  - AEMET_API_KEY: solo para pronostico, no para historico

Outputs:
  - data/raw/clima_barcelona.csv        (clima real diario 2018-hoy)
  - data/raw/festivos_cataluna.csv      (festivos reales Cataluna)
  - data/raw/eventos_barcelona.csv      (agenda eventos BCN)
  - data/raw/partidos_barca.csv         (partidos FC Barcelona)
  - data/raw/renfe_rodalies_2018.csv    (viajeros Rodalies BCN 2018)
"""

import os
import time
import json
import requests
import pandas as pd
from pathlib import Path
from datetime import date, timedelta

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

BARCELONA_LAT = 41.3874
BARCELONA_LON = 2.1686
FOOTBALL_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "")
YEARS_RANGE = list(range(2018, date.today().year + 1))


# ══════════════════════════════════════════════════════════════════════════════
# 1. CLIMA HISTORICO — Open-Meteo Archive API (datos reales, sin key)
# ══════════════════════════════════════════════════════════════════════════════

def download_clima_historico():
    """
    Descarga datos climaticos reales de Barcelona via Open-Meteo Archive API.
    Usa ERA5 reanalysis — considerado el estandar de referencia para datos
    meteorologicos historicos. Precipitacion en mm reales, no probabilidad.
    """
    print("Descargando clima historico real (Open-Meteo Archive)...")

    all_records = []
    end_limit = date.today() - timedelta(days=5)

    for year in YEARS_RANGE:
        start = f"{year}-01-01"
        end_date = date(year, 12, 31)
        if end_date > end_limit:
            end_date = end_limit
        end = str(end_date)

        if date.fromisoformat(start) > end_limit:
            break

        url = (
            f"https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={BARCELONA_LAT}&longitude={BARCELONA_LON}"
            f"&start_date={start}&end_date={end}"
            f"&daily=temperature_2m_max,temperature_2m_min,"
            f"precipitation_sum,windspeed_10m_max"
            f"&timezone=Europe%2FMadrid"
        )

        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            daily = data["daily"]

            for i, fecha in enumerate(daily["time"]):
                all_records.append({
                    "fecha": fecha,
                    "tmax": daily["temperature_2m_max"][i],
                    "tmin": daily["temperature_2m_min"][i],
                    "prec": daily["precipitation_sum"][i] or 0.0,
                    "velmedia": daily["windspeed_10m_max"][i] or 0.0,
                })

            print(f"   {year}: {len(daily['time'])} dias descargados")

        except Exception as e:
            print(f"   {year}: ERROR - {e}")

        time.sleep(0.3)

    if not all_records:
        print("   ERROR: No se pudo descargar ningun dato climatico.")
        print("   Verifica tu conexion a internet.")
        return False

    df = pd.DataFrame(all_records)
    df["tmed"] = ((df["tmax"] + df["tmin"]) / 2).round(1)
    df = df[["fecha", "tmax", "tmin", "tmed", "prec", "velmedia"]]

    out = RAW_DIR / "clima_barcelona.csv"
    df.to_csv(out, index=False)
    print(f"   OK: {len(df)} dias guardados en {out}")
    print(f"   Rango: {df['fecha'].iloc[0]} -> {df['fecha'].iloc[-1]}")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# 2. FESTIVOS — Nager.Date API (datos reales, sin key)
# ══════════════════════════════════════════════════════════════════════════════

def download_festivos():
    """Festivos reales de Cataluna via Nager.Date API publica."""
    print("Descargando festivos Cataluna (Nager.Date)...")

    all_festivos = []
    for year in YEARS_RANGE + [date.today().year + 1]:
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/ES"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()

            count = 0
            for h in resp.json():
                counties = h.get("counties") or []
                is_national = not counties
                is_catalan = any("ES-CT" in c for c in counties)

                if is_national or is_catalan:
                    all_festivos.append({
                        "fecha": h["date"],
                        "nombre": h["localName"],
                        "tipo": "nacional" if is_national else "autonomico",
                    })
                    count += 1

            print(f"   {year}: {count} festivos")

        except Exception as e:
            print(f"   {year}: ERROR - {e}")

        time.sleep(0.3)

    if not all_festivos:
        print("   ERROR: No se pudieron descargar festivos.")
        return False

    df = pd.DataFrame(all_festivos).drop_duplicates("fecha")
    out = RAW_DIR / "festivos_cataluna.csv"
    df.to_csv(out, index=False)
    print(f"   OK: {len(df)} festivos guardados en {out}")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# 3. EVENTOS BARCELONA — Open Data BCN (datos reales, sin key)
# ══════════════════════════════════════════════════════════════════════════════

def download_eventos_bcn():
    """
    Agenda de eventos y actividades de Barcelona.
    Fuente: opendata-ajuntament.barcelona.cat (CKAN API, sin key).
    Contiene conciertos, festivales, exposiciones, ferias, fiestas de barrio, etc.
    """
    print("Descargando agenda de eventos Barcelona (Open Data BCN)...")

    CSV_URL = (
        "https://opendata-ajuntament.barcelona.cat/data/dataset/"
        "a25e60cd-3083-4252-9fce-81f733871cb1/resource/"
        "877ccf66-9106-4ae2-be51-95a9f6469e4c/download"
    )

    try:
        resp = requests.get(CSV_URL, timeout=120)
        resp.raise_for_status()

        out = RAW_DIR / "eventos_barcelona.csv"
        out.write_bytes(resp.content)
        print(f"   OK: {out} ({len(resp.content):,} bytes)")

        try:
            df = pd.read_csv(out, encoding="utf-8", on_bad_lines="skip")
            print(f"   Columnas: {list(df.columns)[:8]}...")
            print(f"   Registros: {len(df)}")
        except Exception:
            df = pd.read_csv(out, encoding="latin-1", on_bad_lines="skip")
            print(f"   Columnas: {list(df.columns)[:8]}...")
            print(f"   Registros: {len(df)}")

        return True

    except Exception as e:
        print(f"   ERROR: {e}")
        print("   La agenda de eventos no esta disponible. Los modelos")
        print("   funcionaran sin la feature de eventos.")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# 4. PARTIDOS FC BARCELONA — football-data.org (key gratuita, opcional)
# ══════════════════════════════════════════════════════════════════════════════

def download_partidos_barca():
    """
    Calendario de partidos del FC Barcelona via football-data.org.
    Requiere FOOTBALL_DATA_API_KEY (gratuita, registrarse en football-data.org).
    Si no hay key, se omite esta fuente.
    """
    if not FOOTBALL_API_KEY:
        print("Sin FOOTBALL_DATA_API_KEY — partidos Barca no disponibles.")
        print("   Registrate gratis en https://www.football-data.org/client/register")
        print("   y anade FOOTBALL_DATA_API_KEY a tu .env")
        return False

    print("Descargando partidos FC Barcelona (football-data.org)...")

    all_matches = []
    headers = {"X-Auth-Token": FOOTBALL_API_KEY}
    barca_id = 81

    for season in range(2020, date.today().year + 1):
        url = f"https://api.football-data.org/v4/teams/{barca_id}/matches?season={season}"

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for match in data.get("matches", []):
                home_team = match.get("homeTeam", {})
                away_team = match.get("awayTeam", {})
                is_home = home_team.get("id") == barca_id

                all_matches.append({
                    "fecha": match["utcDate"][:10],
                    "competicion": match.get("competition", {}).get("name", ""),
                    "es_local": is_home,
                    "rival": (away_team if is_home else home_team).get("name", ""),
                    "estadio": "casa" if is_home else "fuera",
                })

            n = len(data.get("matches", []))
            print(f"   Temporada {season}/{season+1}: {n} partidos")

        except Exception as e:
            print(f"   Temporada {season}: {e}")

        time.sleep(6.5)

    if not all_matches:
        print("   No se descargaron partidos.")
        return False

    df = pd.DataFrame(all_matches)
    out = RAW_DIR / "partidos_barca.csv"
    df.to_csv(out, index=False)

    n_home = len(df[df["es_local"] == True])
    print(f"   OK: {len(df)} partidos ({n_home} en casa) guardados en {out}")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# 5. RENFE RODALIES 2018 — Renfe Data (datos reales, sin key)
# ══════════════════════════════════════════════════════════════════════════════

def download_renfe_2018():
    """
    Volumen de viajeros por franja horaria en estaciones de Rodalies Barcelona.
    Datos de 2018. Fuente: data.renfe.com (Creative Commons 4.0).
    """
    print("Descargando datos Renfe Rodalies Barcelona 2018...")

    url = (
        "https://data.renfe.com/dataset/9190f983-e138-42da-901a-b37205562fe4/"
        "resource/1417396e-4d6a-466a-a987-03d07aa92bed/download/"
        "barcelona_viajeros_por_franja_csv.csv"
    )

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        out = RAW_DIR / "renfe_rodalies_2018.csv"
        out.write_bytes(resp.content)
        print(f"   OK: {out} ({len(resp.content):,} bytes)")

        try:
            df = pd.read_csv(out, encoding="utf-8", sep=None, engine="python",
                             on_bad_lines="skip", nrows=5)
            print(f"   Columnas: {list(df.columns)}")
            print(f"   Muestra:")
            print(df.head(3).to_string())
        except Exception:
            pass

        return True

    except Exception as e:
        print(f"   ERROR: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("PredictaBCN - Paso 1: Descarga de datos REALES")
    print("=" * 60)

    results = {}

    results["clima"] = download_clima_historico()
    print()
    results["festivos"] = download_festivos()
    print()
    results["eventos"] = download_eventos_bcn()
    print()
    results["partidos"] = download_partidos_barca()
    print()
    results["renfe"] = download_renfe_2018()

    print()
    print("=" * 60)
    print("Resumen de descarga:")
    for name, ok in results.items():
        status = "OK" if ok else "FALLO (ver errores arriba)"
        print(f"   {name:15s} -> {status}")

    critical = ["clima", "festivos"]
    if all(results[k] for k in critical):
        print("\nDatos criticos descargados correctamente.")
        print("Siguiente paso: python 02_build_features.py")
    else:
        failed = [k for k in critical if not results[k]]
        print(f"\nFALTAN DATOS CRITICOS: {', '.join(failed)}")
        print("Revisa tu conexion a internet e intentalo de nuevo.")

    print("=" * 60)
