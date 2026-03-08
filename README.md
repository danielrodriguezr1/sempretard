# PredictaBCN

Pronostico de presion en servicios publicos de Barcelona combinando datos
climaticos reales, festivos, eventos masivos y alertas de transporte en
tiempo real.

## Estado de los modelos

| Servicio | Tipo de modelo | Datos | Fiabilidad |
|----------|---------------|-------|------------|
| Hospitales | ML (Prophet) | Features reales + target calibrado | Media — features reales, target calibrado con estadisticas oficiales |
| Metro | Reglas documentadas | Alertas TMB real-time + features reales | Media-alta para alertas, media para pronostico |
| Bus | Reglas documentadas | Alertas TMB real-time + features reales | Media-alta para alertas, media para pronostico |
| Rodalies | Reglas documentadas | Alertas Renfe real-time + features reales | Media-alta para alertas, media para pronostico |

### Sobre la transparencia

**Hospitales**: El modelo Prophet usa exclusivamente features de datos reales
(clima Open-Meteo, festivos Nager.Date, eventos Open Data BCN). El target
es un indice de presion calibrado con patrones documentados del Central de
Resultats y la literatura epidemiologica espanola. NO es un conteo medido
de urgencias — para eso se necesitaria acceso a datos diarios de CatSalut.

**Transporte**: No existen datos publicos de validaciones diarias de TMB ni
Renfe. En vez de fingir ML sobre datos sinteticos, usamos reglas documentadas
con pesos transparentes + alertas en tiempo real. Esto es mas honesto y mas
auditable para un cliente de gobierno.

## Fuentes de datos (todas reales y gratuitas)

| Fuente | Que aporta | Key necesaria |
|--------|-----------|---------------|
| Open-Meteo Archive | Clima historico 2018-hoy (temp, lluvia mm, viento) | No |
| Open-Meteo Forecast | Pronostico clima 7 dias | No |
| AEMET OpenData | Temperaturas Barcelona (enriquecimiento) | Si (gratuita) |
| Nager.Date | Festivos Cataluna | No |
| Open Data BCN | Agenda de eventos Barcelona | No |
| football-data.org | Partidos FC Barcelona | Si (gratuita, opcional) |
| TMB Developer Portal | Alertas metro/bus en tiempo real | Si (gratuita) |
| Renfe Data | Alertas Rodalies + datos historicos 2018 | Si (opcional) |

## Instalacion

```bash
# 1. Clonar y entrar al proyecto
cd predictabcn

# 2. Entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
cp .env.example .env
# Editar .env con tus API keys (ver tabla de fuentes arriba)
```

## Pipeline de entrenamiento

Ejecutar en orden desde la raiz del proyecto:

```bash
# Paso 1: Descargar datos reales (clima, festivos, eventos, Renfe)
python 01_download_data.py

# Paso 2: Construir features (todas de datos reales)
python 02_build_features.py

# Paso 3: Entrenar modelo hospitalario (Prophet)
python 03_train_models.py

# Paso 4: Evaluar modelo (graficas + metricas)
python 04_evaluate.py
```

## Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### Endpoint principal

```
GET http://localhost:8000/api/forecast?ciudad=barcelona
```

Devuelve pronostico de 7 dias con:
- Indice de presion hospitalaria (0-100) via ML
- Indice de presion transporte por modo (metro/bus/rodalies) via reglas
- Recomendacion modal en tiempo real ("Hoy recomendamos metro")
- Estado de alertas de transporte (TMB/Renfe real-time)
- Eventos activos en Barcelona (agenda real)
- Explicacion textual de cada dia

### Otros endpoints

- `GET /health` — estado del servidor y modelos
- `GET /docs` — documentacion interactiva Swagger

## API Keys

Todas gratuitas. El sistema funciona sin ellas (modo fallback) pero es
mejor con todas configuradas:

1. **AEMET_API_KEY**: https://opendata.aemet.es/centrodedescargas/altaUsuario
2. **TMB_APP_ID + TMB_APP_KEY**: https://developer.tmb.cat
3. **FOOTBALL_DATA_API_KEY**: https://www.football-data.org/client/register (opcional)

## Metricas del modelo hospitalario

Evaluacion walk-forward cross-validation (5 folds):

| Metrica | Valor |
|---------|-------|
| sMAPE | 8.1% |
| MAE | 4.6 puntos (escala 0-100) |
| Coverage 80% | 64% (CV) / 79.7% (global) |

Evaluacion global (modelo entrenado con todo el dataset):

| Metrica | Valor |
|---------|-------|
| MAE | 2.58 puntos |
| RMSE | 3.24 |
| sMAPE | 4.9% |
| Coverage 80% | 79.7% |
| Sesgo | 0.00 (sin sesgo) |

## Arquitectura

```
Frontend (React, pendiente)
    |
    | GET /api/forecast
    v
Backend (FastAPI)
    |
    +-- Servicios externos (paralelo):
    |   +-- Open-Meteo / AEMET (clima 7 dias)
    |   +-- Nager.Date (festivos)
    |   +-- Open Data BCN (eventos)
    |   +-- TMB (alertas metro/bus)
    |   +-- Renfe (alertas Rodalies)
    |
    +-- Enricher (construye features por dia)
    |
    +-- Predictor:
    |   +-- Hospitales: Prophet ML
    |   +-- Transporte: reglas documentadas
    |
    +-- Modal Advisor (recomendacion metro/bus/rodalies)
    |
    +-- Explainer (texto humano)
    |
    v
JSON response (cache 6h)
```

## Estructura de archivos

```
predictabcn/
  01_download_data.py       # Descarga datos reales
  02_build_features.py      # Feature engineering
  03_train_models.py        # Entrena modelo Prophet
  04_evaluate.py            # Evaluacion y graficas
  requirements.txt
  .env.example

  data/
    raw/                    # Datos crudos descargados
    processed/              # Datasets procesados

  models/
    modelo_hospitales.pkl   # Prophet entrenado
    norm_params.pkl         # Parametros normalizacion
    metricas_evaluacion.json

  backend/
    main.py                 # Entry point FastAPI
    routers/forecast.py     # Endpoint /api/forecast
    services/               # weather, holidays, transport, events
    core/                   # enricher, predictor, explainer, modal_advisor
    cache/store.py          # Cache con TTL
```
