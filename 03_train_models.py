"""
PASO 3: Entrenamiento de modelos
=================================
Modelo ML (Prophet): solo hospitales — target calibrado con features reales.
Transporte: reglas documentadas (no se finge ML donde no hay datos reales).

Validacion: Walk-forward cross-validation (ventana expandible)
Metricas: MAE, RMSE, sMAPE, Coverage 80%

Outputs:
  - models/modelo_hospitales.pkl
  - models/norm_params.pkl
  - models/metricas_evaluacion.json
"""

import json
import joblib
import warnings
import pandas as pd
import numpy as np
from pathlib import Path
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore")

PROCESSED_DIR = Path("data/processed")
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

REGRESSORS_HOSPITALES = [
    "frio_extremo",
    "frio_moderado",
    "calor_extremo",
    "ola_calor",
    "lluvia_alta",
    "lluvia_moderada",
    "es_post_festivo",
    "es_vispera",
    "es_puente",
    "temporada_gripe",
    "temporada_calor",
    "semana_gripe_alta",
    "amplitud_termica",
    "n_eventos_dia",
    "evento_masivo",
    "partido_barca_casa",
]


# ── Utils ─────────────────────────────────────────────────────────────────────

def _prepare_prophet_df(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    result = pd.DataFrame()
    for c in cols:
        if c == "ds":
            result["ds"] = pd.to_datetime(np.asarray(df["ds"].tolist()))
        else:
            arr = np.asarray(df[c], dtype=np.float64)
            result[c] = np.nan_to_num(arr, nan=0.0)
    return result


def _create_prophet_model(holidays: pd.DataFrame, regressors: list[str],
                          df_cols: list[str]) -> Prophet:
    model = Prophet(
        holidays=holidays,
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode="multiplicative",
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=10.0,
        holidays_prior_scale=10.0,
        interval_width=0.80,
    )
    for reg in regressors:
        if reg in df_cols:
            model.add_regressor(reg, standardize=True)
    return model


def _compute_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                     y_lower: np.ndarray, y_upper: np.ndarray) -> dict:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))

    denominator = np.abs(y_true) + np.abs(y_pred) + 1e-8
    smape = float(np.mean(2 * np.abs(y_true - y_pred) / denominator) * 100)

    nonzero = y_true > 0
    mape_nz = None
    if nonzero.sum() > 10:
        mape_nz = float(np.mean(
            np.abs((y_true[nonzero] - y_pred[nonzero]) / y_true[nonzero])
        ) * 100)

    coverage = float(np.mean(
        (y_true >= y_lower) & (y_true <= y_upper)
    ) * 100)

    return {
        "mae": round(mae, 2),
        "rmse": round(rmse, 2),
        "smape_pct": round(smape, 2),
        "mape_nonzero_pct": round(mape_nz, 2) if mape_nz is not None else None,
        "coverage_80_pct": round(coverage, 1),
    }


def build_prophet_holidays() -> pd.DataFrame:
    festivos_raw = pd.read_csv("data/raw/festivos_cataluna.csv", parse_dates=["fecha"])
    return pd.DataFrame({
        "holiday": "festivo_catalan",
        "ds": festivos_raw["fecha"],
        "lower_window": -1,
        "upper_window": 1,
    })


# ── Walk-forward cross-validation ────────────────────────────────────────────

def walk_forward_cv(
    df: pd.DataFrame,
    regressors: list[str],
    holidays: pd.DataFrame,
    min_train_days: int = 365,
    test_days: int = 90,
    max_folds: int = 5,
) -> list[dict]:
    total = len(df)
    available = total - min_train_days

    if available < test_days:
        print(f"   Solo {total} dias, insuficiente para walk-forward CV")
        return []

    n_possible = available // test_days
    n_folds = min(max_folds, n_possible)
    if n_folds < 2:
        n_folds = 1

    step = (available - test_days) // max(n_folds - 1, 1) if n_folds > 1 else 0
    cols_needed = ["ds", "y"] + [r for r in regressors if r in df.columns]
    fold_metrics = []

    for fold_idx in range(n_folds):
        train_end = min_train_days + fold_idx * step
        test_start = train_end
        test_end = min(test_start + test_days, total)

        if test_end <= test_start + 7:
            break

        df_train = df.iloc[:train_end].copy()
        df_test = df.iloc[test_start:test_end].copy()

        model = _create_prophet_model(holidays, regressors, df.columns.tolist())
        fit_df = _prepare_prophet_df(df_train, cols_needed)
        model.fit(fit_df)

        test_df = _prepare_prophet_df(df_test, cols_needed)
        forecast = model.predict(test_df)

        y_true = df_test["y"].values
        y_pred = forecast["yhat"].clip(lower=0).values
        y_lower = forecast["yhat_lower"].clip(lower=0).values
        y_upper = forecast["yhat_upper"].clip(lower=0).values

        metrics = _compute_metrics(y_true, y_pred, y_lower, y_upper)
        metrics["fold"] = fold_idx + 1
        metrics["train_days"] = len(df_train)
        metrics["test_days"] = len(df_test)
        metrics["test_range"] = (
            f"{df_test['ds'].min().date()} -> {df_test['ds'].max().date()}"
        )
        fold_metrics.append(metrics)

        print(f"     Fold {fold_idx + 1}: "
              f"MAE={metrics['mae']:.1f} | "
              f"sMAPE={metrics['smape_pct']:.1f}% | "
              f"Coverage80={metrics['coverage_80_pct']:.0f}%")

    return fold_metrics


# ── Entrenamiento ────────────────────────────────────────────────────────────

def train_hospital_model(
    df: pd.DataFrame,
    holidays: pd.DataFrame,
) -> tuple[Prophet, dict]:
    """Trains Prophet model for hospital pressure index."""
    regressors = REGRESSORS_HOSPITALES

    print(f"\n{'='*50}")
    print(f"  MODELO: HOSPITALES")
    print(f"  Target: indice de presion calibrado (0-100)")
    print(f"  Features: 100% datos reales")
    print(f"  Datos: {len(df)} dias ({df['ds'].min().date()} -> {df['ds'].max().date()})")
    print(f"{'='*50}")

    print(f"   Walk-forward cross-validation:")
    cv_metrics = walk_forward_cv(df, regressors, holidays)

    if cv_metrics:
        avg_smape = np.mean([m["smape_pct"] for m in cv_metrics])
        avg_mae = np.mean([m["mae"] for m in cv_metrics])
        avg_coverage = np.mean([m["coverage_80_pct"] for m in cv_metrics])
        print(f"   Promedio CV: MAE={avg_mae:.1f} | sMAPE={avg_smape:.1f}% | Coverage80={avg_coverage:.0f}%")
    else:
        avg_smape = avg_mae = avg_coverage = None

    print(f"   Entrenando modelo final con {len(df)} dias...")
    cols_needed = ["ds", "y"] + [r for r in regressors if r in df.columns]
    model = _create_prophet_model(holidays, regressors, df.columns.tolist())
    fit_df = _prepare_prophet_df(df, cols_needed)
    model.fit(fit_df)

    # Holdout metrics (last 20%)
    split_idx = int(len(df) * 0.80)
    df_test = df.iloc[split_idx:].copy()
    test_df = _prepare_prophet_df(df_test, cols_needed)
    forecast = model.predict(test_df)

    y_true = df_test["y"].values
    y_pred = forecast["yhat"].clip(lower=0).values
    y_lower = forecast["yhat_lower"].clip(lower=0).values
    y_upper = forecast["yhat_upper"].clip(lower=0).values
    holdout_metrics = _compute_metrics(y_true, y_pred, y_lower, y_upper)

    residuals = y_true - y_pred
    residual_stats = {
        "mean": round(float(np.mean(residuals)), 2),
        "std": round(float(np.std(residuals)), 2),
        "skewness": round(float(pd.Series(residuals).skew()), 3),
        "p90_error": round(float(np.percentile(np.abs(residuals), 90)), 2),
    }

    metrics_summary = {
        "service": "hospitales",
        "model_type": "Prophet",
        "data_source": "calibrated",
        "regressors": [r for r in regressors if r in df.columns],
        "total_days": len(df),
        "holdout_metrics": holdout_metrics,
        "cv_folds": cv_metrics,
        "cv_avg": {
            "smape_pct": round(avg_smape, 2) if avg_smape else None,
            "mae": round(avg_mae, 2) if avg_mae else None,
            "coverage_80_pct": round(avg_coverage, 1) if avg_coverage else None,
        },
        "residual_analysis": residual_stats,
    }

    return model, metrics_summary


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("PredictaBCN - Paso 3: Entrenamiento de modelos")
    print("=" * 60)

    print("\nCargando dataset hospitalario...")
    df_hosp = pd.read_csv(PROCESSED_DIR / "dataset_hospitales.csv", parse_dates=["ds"])
    print(f"   {len(df_hosp)} dias cargados")

    holidays = build_prophet_holidays()
    print(f"   {len(holidays)} festivos para Prophet")

    # Train hospital model
    model, metrics = train_hospital_model(df_hosp, holidays)

    # Save model
    joblib.dump(model, MODELS_DIR / "modelo_hospitales.pkl")
    print(f"\n   Guardado: models/modelo_hospitales.pkl")

    # Norm params (for hospital index normalization)
    y_valid = df_hosp["y"]
    norm_params = {
        "hospitales": {
            "p5": float(np.percentile(y_valid, 5)),
            "p95": float(np.percentile(y_valid, 95)),
            "median": float(np.median(y_valid)),
        },
    }
    joblib.dump(norm_params, MODELS_DIR / "norm_params.pkl")
    print(f"   Guardado: models/norm_params.pkl")

    # Save all metrics
    all_metrics = [
        metrics,
        {
            "service": "metro",
            "model_type": "rules_based",
            "data_source": "no_data",
            "note": "Sin datos reales de validaciones TMB. Prediccion por reglas documentadas + alertas en tiempo real.",
        },
        {
            "service": "bus",
            "model_type": "rules_based",
            "data_source": "no_data",
            "note": "Sin datos reales de validaciones TMB. Prediccion por reglas documentadas + alertas en tiempo real.",
        },
        {
            "service": "rodalies",
            "model_type": "rules_based",
            "data_source": "aggregate_2018",
            "note": "Datos agregados Renfe 2018 (por franja, no diarios). Prediccion por reglas + alertas en tiempo real.",
        },
    ]

    metrics_path = MODELS_DIR / "metricas_evaluacion.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("Resumen:")
    print(f"   Hospitales (Prophet): sMAPE={metrics.get('cv_avg', {}).get('smape_pct', 'N/A')}%")
    print(f"   Metro:     reglas documentadas (sin datos para ML)")
    print(f"   Bus:       reglas documentadas (sin datos para ML)")
    print(f"   Rodalies:  reglas documentadas (datos agregados 2018)")
    print()
    print("   IMPORTANTE: el modelo hospitalario usa un target CALIBRADO,")
    print("   no conteos medidos. Las metricas evaluan la consistencia")
    print("   temporal del modelo, no precision sobre datos reales.")
    print()
    print("   Transporte NO usa ML — las alertas en tiempo real de TMB/Renfe")
    print("   aportan mucho mas valor que un modelo sobre datos inexistentes.")
    print()
    print("   Siguiente paso: python 04_evaluate.py")
    print("=" * 60)
