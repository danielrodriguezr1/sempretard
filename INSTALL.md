# PredictaBCN — Guía de instalación

## Requisitos previos

- Python 3.10 o superior
- pip
- Git (opcional)

Comprueba tu versión de Python:
```bash
python --version
# Debe mostrar Python 3.10.x o superior
```

---

## 1. Estructura esperada del proyecto

Después de descomprimir o clonar, debes tener esta estructura:

```
predictabcn/
├── requirements.txt
├── .env.example
├── README.md
├── INSTALL.md                  ← este fichero
│
├── train/
│   ├── 01_download_data.py
│   ├── 02_build_features.py
│   ├── 03_train_models.py
│   └── 04_evaluate.py
│
├── models/                     ← vacío hasta entrenar
│
└── backend/
    ├── main.py
    ├── __init__.py
    ├── routers/
    │   ├── __init__.py
    │   └── forecast.py
    ├── core/
    │   ├── __init__.py
    │   ├── enricher.py
    │   ├── predictor.py
    │   └── explainer.py
    ├── services/
    │   ├── __init__.py
    │   ├── weather.py
    │   ├── holidays.py
    │   └── transport.py
    ├── cache/
    │   ├── __init__.py
    │   └── store.py
    └── schemas/
        ├── __init__.py
        └── forecast.py
```

---

## 2. Crear entorno virtual

Es muy recomendable usar un entorno virtual para no mezclar dependencias
con otras proyectos de Python en tu máquina.

```bash
# Desde la raíz del proyecto (carpeta predictabcn/)
python -m venv venv
```

Activar el entorno virtual:

```bash
# En macOS / Linux:
source venv/bin/activate

# En Windows (PowerShell):
venv\Scripts\Activate.ps1

# En Windows (CMD):
venv\Scripts\activate.bat
```

Sabrás que está activo porque el prompt cambia a algo como:
```
(venv) tu-usuario@tu-maquina predictabcn %
```

---

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

Esto instala: FastAPI, Uvicorn, Prophet, scikit-learn, pandas, numpy,
aiohttp, joblib, python-dotenv y todas sus dependencias.

La primera vez puede tardar 2-3 minutos porque Prophet tiene bastantes
dependencias (incluye Stan para el modelo bayesiano).

Verifica que todo se instaló correctamente:
```bash
python -c "import fastapi, prophet, pandas; print('OK')"
# Debe imprimir: OK
```

---

## 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita el fichero `.env` con un editor de texto:

```env
AEMET_API_KEY=tu_api_key_aqui
TMB_APP_ID=tu_app_id_aqui
TMB_APP_KEY=tu_app_key_aqui
```

### Cómo obtener las API keys (todas gratuitas):

**AEMET OpenData** (clima Barcelona):
1. Ve a https://opendata.aemet.es/centrodedescargas/altaUsuario
2. Introduce tu email
3. Recibirás la API key por correo en unos minutos

**TMB Developer** (transporte Barcelona):
1. Ve a https://developer.tmb.cat/
2. Crea una cuenta gratuita
3. Crea una nueva aplicación
4. Copia el `app_id` y `app_key`

> ⚠️ Si no tienes las keys todavía, no pasa nada.
> El sistema arrancará en modo fallback usando Open-Meteo (clima)
> y festivos hardcoded. Podrás probar todo sin keys.

---

## 5. Entrenar los modelos ML

Los modelos deben entrenarse antes de arrancar el backend.
Este paso solo se repite cuando hay datos nuevos (mensualmente).

```bash
# Desde la raíz del proyecto
cd train

# Paso 1: Descargar datos históricos
python 01_download_data.py
# Descarga datos de CatSalut, AEMET y festivos.
# Si no hay conexión o keys, genera datos sintéticos automáticamente.
# Resultado: carpeta data/raw/ con 3 ficheros CSV

# Paso 2: Construir features
python 02_build_features.py
# Resultado: carpeta data/processed/ con 3 datasets listos para ML

# Paso 3: Entrenar modelos
python 03_train_models.py
# Tarda ~2-5 minutos (Prophet entrena 3 modelos)
# Resultado: carpeta models/ con modelo_hospitales.pkl,
#            modelo_oacs.pkl, modelo_transporte.pkl

# Paso 4 (opcional): Evaluar precisión
python 04_evaluate.py
# Genera gráficas en data/evaluation/
# Muestra MAPE, MAE y RMSE por servicio
```

Al terminar deberías ver algo como:
```
Resumen de precisión:
   hospitales   → MAPE 8.3%  🟢 Bueno
   oacs         → MAPE 11.2% 🟡 Aceptable
   transporte   → MAPE 7.1%  🟢 Bueno
```

---

## 6. Arrancar el backend

```bash
# Vuelve a la raíz del proyecto
cd ..

# Arranca el servidor FastAPI
cd backend
uvicorn main:app --reload --port 8000
```

Deberías ver:
```
🚀 PredictaBCN arrancando...
📦 Cargando modelos ML...
   ✅ Modelo cargado: hospitales
   ✅ Modelo cargado: oacs
   ✅ Modelo cargado: transporte
✅ Los 3 modelos ML cargados en memoria.
INFO: Uvicorn running on http://0.0.0.0:8000
```

---

## 7. Verificar que funciona

Abre otra terminal (con el entorno virtual activado) y prueba:

```bash
# Health check
curl http://localhost:8000/health

# Pronóstico completo
curl http://localhost:8000/api/forecast | python -m json.tool
```

O simplemente abre en el navegador:
- http://localhost:8000/docs → Documentación interactiva (Swagger UI)
- http://localhost:8000/health → Estado del servidor
- http://localhost:8000/api/forecast → Datos del pronóstico

---

## Solución de problemas comunes

**Error: `ModuleNotFoundError: No module named 'prophet'`**
```bash
# Asegúrate de tener el entorno virtual activado
source venv/bin/activate  # macOS/Linux
pip install prophet
```

**Error: `No such file or directory: 'models/modelo_hospitales.pkl'`**
```bash
# Necesitas entrenar los modelos primero
cd train && python 03_train_models.py
```

**Error al importar en Windows con rutas relativas**
```bash
# Arranca uvicorn siempre desde dentro de la carpeta backend/
cd backend
uvicorn main:app --reload
```

**Las APIs externas no responden**
El sistema tiene fallbacks automáticos para todas las APIs:
- AEMET → Open-Meteo (sin key, sin límites)
- Nager.Date → festivos hardcoded
- TMB → sin incidencias (valor 0)

El backend siempre devuelve una predicción, aunque sea en modo fallback.

---

## Reentrenar cuando hay datos nuevos

CatSalut publica datos actualizados el día 8 de cada mes:

```bash
source venv/bin/activate
cd train
python 01_download_data.py
python 02_build_features.py
python 03_train_models.py
# Reinicia el backend para que cargue los modelos nuevos
```
