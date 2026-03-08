"""
PASO 4: Evaluacion del modelo hospitalario
============================================
Genera visualizaciones y metricas detalladas del modelo Prophet
entrenado sobre el indice de presion hospitalaria calibrado.

IMPORTANTE: estas metricas evaluan la capacidad del modelo de
capturar patrones temporales sobre un target CALIBRADO (no medido).
Son utiles para validar consistencia pero NO representan precision
sobre conteos reales de urgencias.

Outputs:
  - models/eval_hospitales_prediccion_vs_real.png
  - models/eval_hospitales_errores.png
  - models/eval_hospitales_residuos.png
"""

import json
import joblib
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import mean_absolute_error, mean_squared_error

warnings.filterwarnings("ignore")

PROCESSED_DIR = Path("data/processed")
MODELS_DIR = Path("models")


def evaluate_hospital_model():
    """Full evaluation of the hospital Prophet model."""
    model_path = MODELS_DIR / "modelo_hospitales.pkl"
    if not model_path.exists():
        print("Modelo no encontrado. Ejecuta primero: python 03_train_models.py")
        return

    model = joblib.load(model_path)
    df = pd.read_csv(PROCESSED_DIR / "dataset_hospitales.csv", parse_dates=["ds"])

    # Predict on the full dataset
    regressors = list(model.extra_regressors.keys())
    cols_needed = ["ds"] + regressors
    df_pred = pd.DataFrame()
    df_pred["ds"] = pd.to_datetime(df["ds"].tolist())
    for c in regressors:
        if c in df.columns:
            arr = np.asarray(df[c], dtype=np.float64)
            df_pred[c] = np.nan_to_num(arr, nan=0.0)

    forecast = model.predict(df_pred)

    y_true = df["y"].values
    y_pred = forecast["yhat"].clip(lower=0).values
    y_lower = forecast["yhat_lower"].clip(lower=0).values
    y_upper = forecast["yhat_upper"].clip(lower=0).values
    dates = df["ds"].values

    # -- Metrics --
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    denominator = np.abs(y_true) + np.abs(y_pred) + 1e-8
    smape = float(np.mean(2 * np.abs(y_true - y_pred) / denominator) * 100)
    coverage = float(np.mean((y_true >= y_lower) & (y_true <= y_upper)) * 100)

    print(f"\nMetricas globales (modelo entrenado sobre todo el dataset):")
    print(f"   MAE:          {mae:.2f} puntos (escala 0-100)")
    print(f"   RMSE:         {rmse:.2f}")
    print(f"   sMAPE:        {smape:.1f}%")
    print(f"   Coverage 80%: {coverage:.1f}%")

    residuals = y_true - y_pred
    print(f"\nAnalisis de residuos:")
    print(f"   Media (sesgo):  {np.mean(residuals):.2f}")
    print(f"   Std:            {np.std(residuals):.2f}")
    print(f"   P90 error abs:  {np.percentile(np.abs(residuals), 90):.2f}")

    # -- Plot 1: Prediction vs Real --
    fig, ax = plt.subplots(figsize=(16, 5))
    ax.plot(dates, y_true, alpha=0.5, linewidth=0.5, label="Calibrado (target)", color="steelblue")
    ax.plot(dates, y_pred, alpha=0.7, linewidth=0.5, label="Prediccion Prophet", color="orangered")
    ax.fill_between(dates, y_lower, y_upper, alpha=0.15, color="orangered", label="Intervalo 80%")
    ax.set_title("Hospitales: Prediccion vs Target Calibrado")
    ax.set_ylabel("Indice de presion (0-100)")
    ax.legend(loc="upper right")
    ax.set_ylim(0, 105)
    plt.tight_layout()
    path1 = MODELS_DIR / "eval_hospitales_prediccion_vs_real.png"
    fig.savefig(path1, dpi=150)
    plt.close(fig)
    print(f"\n   Grafica: {path1}")

    # -- Plot 2: Absolute errors over time --
    abs_errors = np.abs(residuals)
    fig, ax = plt.subplots(figsize=(16, 4))
    ax.bar(dates, abs_errors, width=1.5, color="coral", alpha=0.6)
    ax.axhline(mae, color="red", linestyle="--", label=f"MAE = {mae:.1f}")
    ax.set_title("Error absoluto por dia")
    ax.set_ylabel("Error (puntos)")
    ax.legend()
    plt.tight_layout()
    path2 = MODELS_DIR / "eval_hospitales_errores.png"
    fig.savefig(path2, dpi=150)
    plt.close(fig)
    print(f"   Grafica: {path2}")

    # -- Plot 3: Residual distribution --
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].hist(residuals, bins=50, color="steelblue", alpha=0.7, edgecolor="white")
    axes[0].axvline(0, color="red", linestyle="--")
    axes[0].set_title("Distribucion de residuos")
    axes[0].set_xlabel("Residuo (real - prediccion)")

    axes[1].scatter(y_pred, residuals, alpha=0.2, s=2, color="steelblue")
    axes[1].axhline(0, color="red", linestyle="--")
    axes[1].set_title("Residuos vs Prediccion")
    axes[1].set_xlabel("Prediccion")
    axes[1].set_ylabel("Residuo")
    plt.tight_layout()
    path3 = MODELS_DIR / "eval_hospitales_residuos.png"
    fig.savefig(path3, dpi=150)
    plt.close(fig)
    print(f"   Grafica: {path3}")

    # -- Feature importance (approximate via regressor coefficients) --
    print(f"\nImportancia de features (coeficientes Prophet):")
    if hasattr(model, 'params') and 'beta' in model.params:
        betas = model.params['beta'].flatten()
        reg_names = list(model.extra_regressors.keys())
        if len(betas) == len(reg_names):
            importance = sorted(
                zip(reg_names, np.abs(betas)),
                key=lambda x: x[1],
                reverse=True
            )
            for name, imp in importance[:10]:
                bar = "#" * int(imp * 100)
                print(f"   {name:25s} {imp:.4f}  {bar}")

    # -- Top error days --
    print(f"\nTop 10 dias con mayor error:")
    error_df = pd.DataFrame({
        "fecha": df["ds"],
        "real": y_true,
        "pred": np.round(y_pred, 1),
        "error": np.round(abs_errors, 1),
    }).nlargest(10, "error")

    for _, row in error_df.iterrows():
        print(f"   {row['fecha'].date()}: real={row['real']:.1f} pred={row['pred']:.1f} error={row['error']:.1f}")


if __name__ == "__main__":
    print("=" * 60)
    print("PredictaBCN - Paso 4: Evaluacion del modelo")
    print("=" * 60)

    evaluate_hospital_model()

    print("\n" + "=" * 60)
    print("NOTA: transporte usa reglas documentadas (no ML).")
    print("Las reglas no tienen metricas de precision porque")
    print("no existen datos reales de validaciones diarias.")
    print("Su valor esta en las alertas en tiempo real de TMB/Renfe.")
    print("=" * 60)
