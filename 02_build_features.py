"""
PASO 2: Construccion de features con datos REALES
===================================================
TODAS las features provienen de datos reales descargados en el paso 1.
No se generan datos sinteticos para las features.

Features de calendario:  dia_semana, mes, semana_anyo, etc.
Features climaticas:     tmax, tmin, prec, frio_extremo, etc. (Open-Meteo Archive, real)
Features de festivos:    es_festivo, es_post_festivo, etc. (Nager.Date, real)
Features de eventos:     n_eventos_dia, evento_masivo (Open Data BCN, real)
Features de futbol:      partido_barca_casa (football-data.org, si disponible)

Target hospitales: indice de presion CALIBRADO con patrones epidemiologicos
documentados en la literatura + clima real + calendario real.
NO es un conteo medido — es una estimacion calibrada con estadisticas oficiales.

Inputs:
  - data/raw/clima_barcelona.csv          (Open-Meteo Archive)
  - data/raw/festivos_cataluna.csv        (Nager.Date)
  - data/raw/eventos_barcelona.csv        (Open Data BCN)
  - data/raw/partidos_barca.csv           (football-data.org, opcional)

Outputs:
  - data/processed/dataset_hospitales.csv
  - data/processed/data_provenance.json
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS CRUDOS (todos reales)
# ══════════════════════════════════════════════════════════════════════════════

def load_clima() -> pd.DataFrame:
    path = RAW_DIR / "clima_barcelona.csv"
    df = pd.read_csv(path, parse_dates=["fecha"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df.sort_values("fecha").reset_index(drop=True)


def load_festivos() -> pd.DataFrame:
    path = RAW_DIR / "festivos_cataluna.csv"
    df = pd.read_csv(path, parse_dates=["fecha"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df[["fecha", "tipo"]].copy()


def load_eventos() -> pd.DataFrame | None:
    """
    Carga la agenda de eventos de Barcelona (Open Data BCN).
    CSV en UTF-16 con separador coma.
    """
    path = RAW_DIR / "eventos_barcelona.csv"
    if not path.exists():
        print("   Eventos BCN: archivo no encontrado, se omite esta feature.")
        return None

    try:
        df = pd.read_csv(path, encoding="utf-16", sep=",", on_bad_lines="skip")
    except Exception:
        try:
            df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")
        except Exception as e:
            print(f"   Eventos BCN: error leyendo CSV - {e}")
            return None

    if "start_date" not in df.columns or "name" not in df.columns:
        print(f"   Eventos BCN: columnas inesperadas - {list(df.columns)[:5]}")
        return None

    df["start_dt"] = pd.to_datetime(df["start_date"], errors="coerce", utc=True)
    df["end_dt"] = pd.to_datetime(df["end_date"], errors="coerce", utc=True)

    df = df.dropna(subset=["start_dt"])

    df["start_day"] = df["start_dt"].dt.date
    df["end_day"] = df["end_dt"].dt.date
    # For events without end date, they are single-day
    df["end_day"] = df["end_day"].fillna(df["start_day"])

    df["name_lower"] = df["name"].str.lower().fillna("")
    df["district"] = df.get("addresses_district_name", pd.Series("", index=df.index)).fillna("")

    print(f"   Eventos BCN: {len(df)} eventos cargados")
    return df[["name_lower", "start_day", "end_day", "district"]].copy()


def load_partidos_barca() -> pd.DataFrame | None:
    path = RAW_DIR / "partidos_barca.csv"
    if not path.exists():
        print("   Partidos Barca: no disponible (necesita FOOTBALL_DATA_API_KEY)")
        return None

    try:
        df = pd.read_csv(path, parse_dates=["fecha"])
        home = df[df["es_local"] == True].copy()
        print(f"   Partidos Barca: {len(home)} partidos en casa cargados")
        return home
    except Exception as e:
        print(f"   Partidos Barca: error - {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# FEATURE ENGINEERING
# ══════════════════════════════════════════════════════════════════════════════

def build_calendar_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["dia_semana"] = df["fecha"].dt.dayofweek
    df["mes"] = df["fecha"].dt.month
    df["semana_anyo"] = df["fecha"].dt.isocalendar().week.astype(int)
    df["trimestre"] = df["fecha"].dt.quarter
    df["dia_mes"] = df["fecha"].dt.day

    df["dia_semana_sin"] = np.sin(2 * np.pi * df["dia_semana"] / 7)
    df["dia_semana_cos"] = np.cos(2 * np.pi * df["dia_semana"] / 7)
    df["mes_sin"] = np.sin(2 * np.pi * df["mes"] / 12)
    df["mes_cos"] = np.cos(2 * np.pi * df["mes"] / 12)

    df["es_lunes"] = (df["dia_semana"] == 0).astype(int)
    df["es_fin_semana"] = (df["dia_semana"] >= 5).astype(int)
    df["es_inicio_mes"] = (df["dia_mes"] <= 3).astype(int)

    df["temporada_gripe"] = df["mes"].isin([1, 2, 3, 11, 12]).astype(int)
    df["temporada_calor"] = df["mes"].isin([7, 8]).astype(int)
    df["vuelta_al_cole"] = (
        (df["mes"] == 9) & (df["dia_mes"].between(1, 15))
    ).astype(int)

    return df


def build_holiday_features(df: pd.DataFrame, festivos: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    fechas_festivo = set(festivos["fecha"].dt.normalize())

    df["es_festivo"] = df["fecha"].isin(fechas_festivo).astype(int)
    df["es_post_festivo"] = df["fecha"].apply(
        lambda d: int((d - pd.Timedelta(days=1)) in fechas_festivo)
    )
    df["es_vispera"] = df["fecha"].apply(
        lambda d: int((d + pd.Timedelta(days=1)) in fechas_festivo)
    )
    df["es_puente"] = (
        (df["es_vispera"] == 1) & (df["es_fin_semana"] == 1) |
        (df["es_post_festivo"] == 1) & (df["es_fin_semana"] == 1)
    ).astype(int)

    dias_festivo_sorted = sorted(fechas_festivo)

    def dias_desde_festivo(fecha):
        pasados = [f for f in dias_festivo_sorted if f <= fecha]
        return (fecha - pasados[-1]).days if pasados else 30

    df["dias_desde_festivo"] = df["fecha"].apply(dias_desde_festivo)
    return df


def build_climate_features(df: pd.DataFrame, clima: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(
        clima[["fecha", "tmax", "tmin", "tmed", "prec", "velmedia"]],
        on="fecha", how="left"
    )
    df["frio_extremo"] = (df["tmin"] < 5).astype(int)
    df["frio_moderado"] = (df["tmin"].between(5, 10)).astype(int)
    df["calor_extremo"] = (df["tmax"] > 33).astype(int)
    df["lluvia_alta"] = (df["prec"] > 15).astype(int)
    df["lluvia_moderada"] = (df["prec"].between(5, 15)).astype(int)
    df["ola_calor"] = (
        (df["tmax"] > 33) & (df["temporada_calor"] == 1)
    ).astype(int)
    df["amplitud_termica"] = df["tmax"] - df["tmin"]

    for col in ["tmax", "tmin", "tmed", "prec", "velmedia"]:
        df[col] = df.groupby("mes")[col].transform(
            lambda x: x.fillna(x.mean())
        )
    return df


def build_epidemiological_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["semana_gripe_alta"] = df["semana_anyo"].between(2, 8).astype(int)
    df["semana_tramites_alta"] = (
        df["semana_anyo"].isin(
            list(range(1, 6)) + list(range(36, 42)) + list(range(49, 53))
        )
    ).astype(int)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# EVENT FEATURES (datos reales de Open Data BCN)
# ══════════════════════════════════════════════════════════════════════════════

# Keywords for detecting large-attendance events
_LARGE_EVENT_KW = [
    # Mega events
    "mobile world congress", "mwc", "primavera sound", "sónar", "sonar",
    "cruïlla", "cruilla", "festa major", "festes de la mercè",
    "cavalcada de reis", "marató de barcelona",
    # Large events
    "festival", "festes de", "concert", "concerts", "macro",
    "cursa", "piromusical", "nit de",
    "saló", "salon", "congrés", "congres", "congress", "expo",
    # Venues (any event here is large by default)
    "palau sant jordi", "estadi olímpic", "estadi olimpic",
    "camp nou", "spotify camp nou",
    "sant jordi club", "fira barcelona", "fira gran via",
    "ccib", "fòrum", "parc del fòrum",
    "razzmatazz", "sala apolo",
]

MAX_EVENT_DURATION_DAYS = 60


def build_event_features(
    df: pd.DataFrame,
    eventos: pd.DataFrame | None,
    partidos: pd.DataFrame | None,
) -> pd.DataFrame:
    """
    Adds n_eventos_dia, evento_masivo, partido_barca_casa from real data.
    """
    df = df.copy()

    if eventos is not None and len(eventos) > 0:
        event_counts, large_events = _count_events_per_day(eventos, df["fecha"])
        df["n_eventos_dia"] = df["fecha"].map(event_counts).fillna(0).astype(int)
        df["evento_masivo"] = df["fecha"].map(large_events).fillna(0).astype(int)
    else:
        df["n_eventos_dia"] = 0
        df["evento_masivo"] = 0

    if partidos is not None and len(partidos) > 0:
        barca_home_dates = set(pd.to_datetime(partidos["fecha"]).dt.normalize())
        df["partido_barca_casa"] = df["fecha"].isin(barca_home_dates).astype(int)
    else:
        df["partido_barca_casa"] = 0

    return df


def _count_events_per_day(
    eventos: pd.DataFrame, date_series: pd.Series
) -> tuple[dict, dict]:
    """Count events active on each date and flag large events."""
    import datetime

    all_dates = set(date_series.dt.date)
    event_counts = Counter()
    large_event_dates = set()

    for _, row in eventos.iterrows():
        try:
            s_day = row["start_day"]
            e_day = row["end_day"]

            if isinstance(s_day, str):
                s_day = datetime.date.fromisoformat(s_day)
            if isinstance(e_day, str):
                e_day = datetime.date.fromisoformat(e_day)

            if pd.isna(s_day):
                continue
            if pd.isna(e_day):
                e_day = s_day

            duration = (e_day - s_day).days
            if duration > MAX_EVENT_DURATION_DAYS:
                continue
            if duration < 0:
                continue

            is_large = any(kw in row["name_lower"] for kw in _LARGE_EVENT_KW)

            current = s_day
            while current <= e_day:
                if current in all_dates:
                    event_counts[current] += 1
                    if is_large:
                        large_event_dates.add(current)
                current += datetime.timedelta(days=1)

        except Exception:
            continue

    date_to_count = {}
    date_to_large = {}
    for d in all_dates:
        date_to_count[pd.Timestamp(d)] = event_counts.get(d, 0)
        date_to_large[pd.Timestamp(d)] = 1 if d in large_event_dates else 0

    return date_to_count, date_to_large


# ══════════════════════════════════════════════════════════════════════════════
# HOSPITAL CALIBRATED TARGET
# ══════════════════════════════════════════════════════════════════════════════

# Documented day-of-week effect on hospital emergency demand
# Source: Spanish Ministry of Health, Central de Resultats Catalonia
DOW_MULT = {0: 1.12, 1: 1.06, 2: 1.02, 3: 1.00, 4: 1.04, 5: 0.88, 6: 0.82}

# Monthly seasonality from Central de Resultats annual patterns
# Flu season (Jan-Feb) and winter (Nov-Dec) show highest demand
MONTH_MULT = {
    1: 1.25, 2: 1.18, 3: 1.06, 4: 0.98, 5: 0.95, 6: 0.93,
    7: 0.98, 8: 0.87, 9: 0.97, 10: 1.03, 11: 1.10, 12: 1.16,
}


def build_hospital_calibrated_target(df: pd.DataFrame) -> pd.Series:
    """
    Genera un indice de presion hospitalaria (0-100) calibrado con:
    - Patrones dia-de-semana (literatura epidemiologica espanola)
    - Estacionalidad mensual (Central de Resultats Catalonia)
    - Efecto clima (correlaciones documentadas con frio/calor/lluvia)
    - Efecto calendario (post-festivo, festivos)
    - Efecto eventos (partidos, eventos masivos)

    TRANSPARENCIA: este target NO es un conteo medido de urgencias.
    Es un indice calibrado con fuentes oficiales y clima real.
    Las metricas ML son utiles para evaluar consistencia temporal,
    pero no representan precision sobre datos reales no disponibles.
    """
    base = 50.0

    # Day of week
    dow_effect = df["dia_semana"].map(DOW_MULT).fillna(1.0)

    # Monthly seasonality
    month_effect = df["mes"].map(MONTH_MULT).fillna(1.0)

    # Weather effects (documented correlations)
    cold_effect = np.where(df["tmin"] < 5, 0.12,
                  np.where(df["tmin"] < 10, 0.05, 0.0))
    heat_effect = np.where(
        (df["tmax"] > 33) & (df["mes"].isin([6, 7, 8, 9])), 0.15, 0.0
    )
    rain_effect = np.where(df["prec"] > 30, 0.12,
                  np.where(df["prec"] > 15, 0.06,
                  np.where(df["prec"] > 5, 0.02, 0.0)))

    # Calendar effects
    post_festivo_effect = np.where(df["es_post_festivo"] == 1, 0.12, 0.0)
    vispera_effect = np.where(df["es_vispera"] == 1, 0.05, 0.0)
    festivo_effect = np.where(df["es_festivo"] == 1, -0.20, 0.0)

    # Flu season boost (weeks 2-8 have peak flu)
    gripe_effect = np.where(df["semana_gripe_alta"] == 1, 0.08, 0.0)

    # Event effects
    evento_effect = np.where(df["evento_masivo"] == 1, 0.04, 0.0)
    barca_effect = np.where(df["partido_barca_casa"] == 1, 0.06, 0.0)

    # Combine all effects multiplicatively
    weather_mult = 1.0 + cold_effect + heat_effect + rain_effect
    calendar_mult = 1.0 + post_festivo_effect + vispera_effect + festivo_effect + gripe_effect
    event_mult = 1.0 + evento_effect + barca_effect

    target = base * dow_effect * month_effect * weather_mult * calendar_mult * event_mult

    # Add realistic daily variation (std ~3 points on 0-100 scale)
    # Represents factors not captured: individual hospital capacity,
    # staff availability, local incidents, etc.
    np.random.seed(42)
    noise = np.random.normal(0, 3.0, len(df))
    target = target + noise

    return target.clip(0, 100).round(1)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("PredictaBCN - Paso 2: Construccion de features (datos REALES)")
    print("=" * 60)

    # -- Load all real data sources --
    print("\nCargando datos reales...")
    clima = load_clima()
    festivos = load_festivos()
    eventos = load_eventos()
    partidos = load_partidos_barca()
    print(f"   Clima:     {len(clima)} dias ({clima['fecha'].min().date()} -> {clima['fecha'].max().date()})")
    print(f"   Festivos:  {len(festivos)} fechas")

    # -- Build base DataFrame from climate date range --
    df = clima[["fecha"]].copy()

    # -- Calendar features --
    print("\nConstruyendo features...")
    df = build_calendar_features(df)
    df = build_holiday_features(df, festivos)
    df = build_climate_features(df, clima)
    df = build_epidemiological_features(df)
    df = build_event_features(df, eventos, partidos)

    # -- Hospital calibrated target --
    print("\nCalibrando target hospitalario...")
    df["y"] = build_hospital_calibrated_target(df)

    # -- Save hospital dataset --
    df_out = df.rename(columns={"fecha": "ds"})
    df_out = df_out.dropna(subset=["y"])
    out_path = PROCESSED_DIR / "dataset_hospitales.csv"
    df_out.to_csv(out_path, index=False)
    print(f"   Hospitales: {len(df_out)} dias, rango indice [{df_out['y'].min():.1f} - {df_out['y'].max():.1f}]")

    # -- Data provenance --
    provenance = {
        "hospitales": {
            "source": "calibrated",
            "description": (
                "Indice de presion calibrado con patrones epidemiologicos "
                "documentados (Central de Resultats, Min. Sanidad) aplicados "
                "sobre clima REAL (Open-Meteo), festivos REALES (Nager.Date) "
                "y eventos REALES (Open Data BCN)."
            ),
            "features_source": "100% datos reales",
            "target_source": "calibrado con literatura + datos oficiales agregados",
            "limitation": (
                "El target no es un conteo medido de urgencias. Es un indice "
                "calibrado. Para prediccion de conteos reales, se necesita acceso "
                "a datos diarios de CatSalut (CMBD-UR) o datos internos del hospital."
            ),
        },
        "transporte": {
            "source": "rules_based",
            "description": (
                "Prediccion basada en reglas documentadas + alertas en tiempo real "
                "de TMB y Renfe. Features de entrada 100% reales."
            ),
            "features_source": "100% datos reales",
            "target_source": "reglas con pesos documentados, no ML",
            "limitation": (
                "No hay datos publicos de validaciones diarias de TMB ni Renfe. "
                "La prediccion se basa en patrones documentados y alertas reales. "
                "Para ML supervisado, se necesitan datos de ridership diario."
            ),
        },
    }

    provenance_path = PROCESSED_DIR / "data_provenance.json"
    with open(provenance_path, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2, ensure_ascii=False)

    # -- Summary --
    print(f"\nGuardado en {PROCESSED_DIR}/")
    print(f"   dataset_hospitales.csv  ({len(df_out)} registros)")
    print(f"   data_provenance.json")

    print(f"\nFeatures ({len(df_out.columns)} columnas):")
    for col in sorted(df_out.columns):
        print(f"   - {col}")

    n_events = df_out["n_eventos_dia"].sum()
    n_large = df_out["evento_masivo"].sum()
    n_barca = df_out["partido_barca_casa"].sum()
    print(f"\nEstadisticas de eventos:")
    print(f"   Dias con eventos:       {(df_out['n_eventos_dia'] > 0).sum()}")
    print(f"   Dias con evento masivo: {n_large}")
    print(f"   Partidos Barca en casa: {n_barca}")

    print(f"\nTarget hospitalario (indice 0-100):")
    print(f"   Media:   {df_out['y'].mean():.1f}")
    print(f"   Mediana: {df_out['y'].median():.1f}")
    print(f"   Min:     {df_out['y'].min():.1f}")
    print(f"   Max:     {df_out['y'].max():.1f}")
    print(f"   Std:     {df_out['y'].std():.1f}")

    print("\n" + "=" * 60)
    print("Siguiente paso: python 03_train_models.py")
    print("=" * 60)
