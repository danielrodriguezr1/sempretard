# PredictaBCN — Especificacion para el Frontend

## Que es PredictaBCN

Aplicacion que predice la presion sobre los servicios publicos de Barcelona (hospitales y transporte publico) para los proximos 7 dias. Combina datos climaticos reales, festivos, eventos culturales/deportivos, y estado del transporte en tiempo real.

El backend ya esta terminado y funcionando. Solo hay que construir el frontend.

---

## Stack recomendado

- **React** (Vite)
- **TypeScript**
- El backend corre en `http://localhost:8000`
- Toda la UI debe estar en **espanol**

---

## API del backend

### Base URL

```
http://localhost:8000
```

### Endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET | `/health` | Estado del servidor |
| GET | `/api/forecast?ciudad=barcelona` | Pronostico completo de 7 dias |

Solo hay un endpoint principal: `/api/forecast`. Devuelve TODO lo necesario en una sola llamada.

### CORS

El backend ya acepta peticiones desde `http://localhost:3000` y `http://localhost:5173`.

---

## Contrato de la API: `/api/forecast`

### Respuesta completa (TypeScript types)

```typescript
interface ForecastResponse {
  generado_en: string;               // ISO datetime "2026-03-07T16:10:05.876454"
  ciudad: string;                     // "Barcelona"
  dias_pronosticados: number;         // 7
  pronostico: ForecastDay[];          // Array de 7 dias
  transporte_ahora: ModalRecommendation;
  estado_transporte: Record<"metro" | "bus" | "rodalies", TransportModeStatus>;
  fuentes: Record<string, { fuente: string; estado: string }>;
  modelos_ml: boolean;
  confianza_modelos: Record<string, ModelConfidence>;
  _cache_hit: boolean;
}
```

### Dia de pronostico

```typescript
interface ForecastDay {
  fecha: string;                      // "2026-03-07"
  dia_semana: string;                 // "Lunes", "Martes", ..., "Domingo"
  es_festivo: boolean;
  es_post_festivo: boolean;
  es_vispera_festivo: boolean;

  indice_global: number;              // 0-100
  nivel_global: "normal" | "elevado" | "critico";

  servicios: {
    hospitales: HospitalForecast;
    transporte: TransportForecast;
  };

  clima: {
    temperatura_max: number;          // Celsius
    temperatura_min: number;
    lluvia_mm: number;
    descripcion: string;              // "Despejado", "Lluvia", "Tormenta", etc.
  };

  eventos: DayEvents;
  factor_estacional: SeasonalFactor;
  factores_activos: string[];         // ej: ["lluvia_alta", "evento_masivo", "es_lunes"]
  explicacion: string;                // Texto legible, ej: "Jornada con demanda elevada..."
}
```

### Hospitales

```typescript
interface HospitalForecast {
  indice: number;                     // 0-100
  nivel: "normal" | "elevado" | "critico";
  intervalo_inferior: number;         // 0-100
  intervalo_superior: number;         // 0-100
  tipo_modelo: string;                // "ML (Prophet)"
}
```

### Transporte

```typescript
interface TransportForecast {
  indice_agregado: number;            // 0-100 (media ponderada de los 3 modos)
  nivel: "normal" | "elevado" | "critico";
  tipo_modelo: string;
  tipo_dia: "laboral" | "sabado" | "domingo";

  modos: {
    metro: TransportModeDetail;
    bus: TransportModeDetail;
    rodalies: TransportModeDetail;
  };
}

interface TransportModeDetail {
  indice: number;                     // 0-100
  nivel: "normal" | "elevado" | "critico";
  intervalo_inferior: number;
  intervalo_superior: number;

  perfil_horario: Record<string, number>;
  // Clave = hora (string "0"-"23"), valor = % ocupacion estimada (0-100)
  // Ej: { "5": 5, "6": 20, "7": 60, "8": 95, ... }
  // NOTA: es una ESTIMACION, no dato real

  franjas_criticas: PeakHour[];
  impacto_eventos: EventSpike[];
}

interface PeakHour {
  franja: string;                     // "07:30 - 09:30"
  tipo: string;                       // "punta_mañana", "mediodia", "punta_tarde"
  intensidad: number;                 // 0-100
  descripcion: string;                // "Entrada al trabajo..."
}

interface EventSpike {
  evento: string;                     // Nombre del evento
  llegada: string;                    // "19:00 - 21:00"
  salida: string;                     // "22:00 - 00:00"
  lineas_afectadas?: string[];        // ["L3 (Les Corts/Palau Reial)"]
}
```

### Eventos del dia

```typescript
interface DayEvents {
  total: number;                      // Total de eventos en el dia
  evento_masivo: boolean;             // Hay algun evento masivo?
  partido_barca: boolean;             // Juega el Barca en casa?

  destacados: EventHighlight[];       // Top 10 eventos por impacto
  lineas_afectadas: string[];         // Lineas de metro afectadas por eventos
  resumen: {
    masivos: number;
    grandes: number;
    medianos: number;
    total: number;
  };
  estaciones_afectadas: AffectedStation[];  // Estaciones reales TMB mas concurridas
}

interface EventHighlight {
  nombre: string;
  impacto: "masivo" | "grande";       // Solo se muestran masivo y grande
  lineas_afectadas?: string[];
  venue?: string;                     // "camp nou", "palau sant jordi", etc.
}

interface AffectedStation {
  estacion: string;                   // "Diagonal", "Espanya", etc.
  linea: string;                      // "L5", "L1", etc.
  pasajeros_dia_laborable: number;    // Dato REAL de TMB 2024
  fuente: string;                     // "TMB 2024 (dato real)"
}
```

### Estacionalidad

```typescript
interface SeasonalFactor {
  mes: string;                        // "mar", "abr", etc.
  factor_estacional: number;          // 95.0 (% del pico anual)
  nota: string;                       // "95% del pico anual (abril=100%)"
  fuente: string;                     // "TMB 2024 (dato real)"
}
```

### Recomendacion modal (transporte ahora)

```typescript
interface ModalRecommendation {
  modo_recomendado: "metro" | "bus" | "rodalies";
  razon: string;                      // "Recomendamos metro hoy: lluvia intensa..."
  scores: Record<string, number>;     // { metro: 10, bus: 30, rodalies: 15 }
  alertas_activas: string[];          // ["🚂 Rodalies: retraso de 25 min"]
  estado_por_modo: Record<string, "normal" | "elevado" | "critico">;
}
```

### Estado transporte tiempo real

```typescript
interface TransportModeStatus {
  severidad: "normal" | "elevado" | "critico";
  n_afectadas: number;
  lineas_afectadas: string[];         // Max 5
  retraso_minutos: number;            // Solo relevante para rodalies
  operador: string;                   // "TMB" o "Renfe Rodalies"
}
```

### Confianza de modelos

```typescript
interface ModelConfidence {
  fiabilidad: string;
  tipo_modelo: string;
  datos_fuente: string;
  nota: string;
  smape_cv?: number;                  // Solo hospitales
  coverage_80_cv?: number;            // Solo hospitales
}
```

---

## Ejemplo real de respuesta (un dia)

```json
{
  "fecha": "2026-03-09",
  "dia_semana": "Lunes",
  "es_festivo": false,
  "es_post_festivo": false,
  "es_vispera_festivo": false,
  "indice_global": 63,
  "nivel_global": "elevado",
  "servicios": {
    "hospitales": {
      "indice": 62,
      "nivel": "elevado",
      "intervalo_inferior": 57,
      "intervalo_superior": 66,
      "tipo_modelo": "ML (Prophet)"
    },
    "transporte": {
      "indice_agregado": 65,
      "nivel": "elevado",
      "tipo_modelo": "reglas documentadas + alertas real-time",
      "tipo_dia": "laboral",
      "modos": {
        "metro": {
          "indice": 65,
          "nivel": "elevado",
          "intervalo_inferior": 55,
          "intervalo_superior": 75,
          "perfil_horario": {
            "5": 5, "6": 20, "7": 60, "8": 95, "9": 80, "10": 50,
            "11": 45, "12": 50, "13": 60, "14": 55, "15": 50, "16": 60,
            "17": 85, "18": 100, "19": 95, "20": 70, "21": 55, "22": 45,
            "23": 35, "0": 25
          },
          "franjas_criticas": [
            {
              "franja": "07:30 - 09:30",
              "tipo": "punta_mañana",
              "intensidad": 95,
              "descripcion": "Entrada al trabajo. Maxima ocupacion en L1, L3, L5"
            },
            {
              "franja": "17:30 - 19:30",
              "tipo": "punta_tarde",
              "intensidad": 90,
              "descripcion": "Salida del trabajo. Muy alta ocupacion"
            }
          ],
          "impacto_eventos": [
            {
              "evento": "Mobile World Congress 2026",
              "llegada": "07:00 - 09:00",
              "salida": "17:00 - 19:00",
              "lineas_afectadas": ["L1 (Fira)", "L9 Sud (Europa|Fira)"]
            }
          ]
        },
        "bus": { "..." : "misma estructura" },
        "rodalies": { "..." : "misma estructura" }
      }
    }
  },
  "clima": {
    "temperatura_max": 15.2,
    "temperatura_min": 8.1,
    "lluvia_mm": 0.0,
    "descripcion": "Parcialmente nublado"
  },
  "eventos": {
    "total": 280,
    "evento_masivo": true,
    "partido_barca": false,
    "destacados": [
      {
        "nombre": "Mobile World Congress 2026",
        "impacto": "masivo",
        "lineas_afectadas": ["L1 (Fira)", "L9 Sud (Europa|Fira)"],
        "venue": "fira gran via"
      }
    ],
    "lineas_afectadas": ["L1 (Fira)", "L9 Sud (Europa|Fira)"],
    "resumen": { "masivos": 1, "grandes": 8, "medianos": 32, "total": 280 },
    "estaciones_afectadas": [
      {
        "estacion": "Espanya",
        "linea": "L1",
        "pasajeros_dia_laborable": 30298,
        "fuente": "TMB 2024 (dato real)"
      }
    ]
  },
  "factor_estacional": {
    "mes": "mar",
    "factor_estacional": 95.0,
    "nota": "95% del pico anual (abril=100%)",
    "fuente": "TMB 2024 (dato real)"
  },
  "factores_activos": ["evento_masivo", "temporada_gripe", "es_lunes", "frio_moderado"],
  "explicacion": "Jornada con demanda moderada en transporte publico por evento masivo en Barcelona, temporada de gripe activa y frio moderado."
}
```

---

## Vistas sugeridas para el frontend

### 1. Dashboard principal (vista de 7 dias)

Barra o carrusel horizontal con los 7 dias. Cada dia muestra:
- Fecha y dia de la semana
- Icono de clima + temperatura
- **Indice global** (0-100) con color: verde (<45), amarillo (45-74), rojo (>=75)
- Nivel: "normal" / "elevado" / "critico"
- Badges si es festivo o hay evento masivo
- Texto de explicacion

Al hacer clic en un dia, se abre la vista detallada.

### 2. Vista detallada de un dia

#### Seccion Hospitales
- Indice con barra de progreso (0-100)
- Intervalo de confianza (inferior-superior)
- Badge "ML (Prophet)"

#### Seccion Transporte
- Indice agregado + desglose por modo (metro, bus, rodalies)
- Para cada modo:
  - **Grafico de barras o area** del perfil horario (24 horas, 0-100%)
  - Franjas criticas resaltadas
  - Lista de eventos que impactan y sus franjas de llegada/salida
  - Lineas afectadas por eventos

#### Seccion Clima
- Temperatura min/max
- Lluvia en mm
- Descripcion

#### Seccion Eventos
- Total de eventos
- Eventos destacados (nombre + impacto)
- Resumen por tier (masivos, grandes, medianos)
- Estaciones de metro mas afectadas (dato real TMB)
- Si hay partido del Barca: icono especial

#### Factor estacional
- "Marzo: 95% del pico anual"

### 3. Widget "Transporte ahora" (siempre visible)

- Modo recomendado (metro/bus/rodalies) con icono
- Razon: "Recomendamos metro hoy: lluvia intensa (bus mas lento)"
- Alertas activas (ej: "Rodalies: retraso de 25 min")
- Estado por modo: semaforo verde/amarillo/rojo

### 4. Seccion de transparencia/metodologia

- Tabla con la confianza de cada modelo (campo `confianza_modelos`)
- Que datos son reales vs estimados
- Fuentes de datos

---

## Paleta de colores sugerida

| Nivel | Color | Uso |
|-------|-------|-----|
| normal (0-44) | `#22c55e` (verde) | Indices bajos |
| elevado (45-74) | `#f59e0b` (ambar) | Indices medios |
| critico (75-100) | `#ef4444` (rojo) | Indices altos |
| festivo | `#8b5cf6` (violeta) | Badge festivo |
| partido barca | `#a41e32` (granate) | Badge Barca |
| evento masivo | `#f97316` (naranja) | Badge evento |

Modos de transporte:
| Modo | Color |
|------|-------|
| metro | `#dc2626` (rojo TMB) |
| bus | `#2563eb` (azul TMB) |
| rodalies | `#7c3aed` (violeta Renfe) |

---

## Notas tecnicas

1. **Una sola llamada API** — `/api/forecast` devuelve todo. No hay que hacer multiples llamadas.
2. **Cache del backend** — La respuesta se cachea 6 horas en el backend. El campo `_cache_hit` indica si viene de cache.
3. **Fallbacks** — Si no hay API keys configuradas, el backend devuelve datos en modo fallback. El campo `fuentes` indica el estado de cada fuente.
4. **Sin autenticacion** — La API no requiere auth. Es un GET publico.
5. **Perfil horario** — Las claves del objeto `perfil_horario` son strings ("0" a "23"), no numeros. Hay que convertirlas a int para graficar.
6. **Los indices van de 0 a 100** — 0 = sin presion, 100 = saturacion total.
7. **El texto de explicacion** ya viene formateado del backend. Solo hay que mostrarlo.
8. **niveles**: "normal" = indice < 45, "elevado" = 45-74, "critico" >= 75.

---

## Estructura del proyecto backend (referencia)

```
predictabcn/
├── backend/
│   ├── main.py                      # FastAPI app (puerto 8000)
│   ├── config.py                    # Settings centralizado
│   ├── exceptions.py                # Excepciones tipadas
│   ├── cache/store.py               # Cache en memoria
│   ├── core/
│   │   ├── predictor.py             # ML (Prophet) + scoring reglas
│   │   ├── enricher.py              # Feature engineering
│   │   ├── explainer.py             # Texto explicativo
│   │   ├── hourly.py                # Perfiles horarios
│   │   └── modal_advisor.py         # Recomendador de transporte
│   ├── services/
│   │   ├── weather.py               # Open-Meteo + AEMET
│   │   ├── holidays.py              # Nager.Date
│   │   ├── transport.py             # TMB + Renfe real-time
│   │   ├── events.py                # Open Data BCN + football-data
│   │   └── forecast_service.py      # Orquestador central
│   └── routers/forecast.py          # Endpoint HTTP
├── frontend/                        # <-- AQUI VA EL FRONTEND
├── models/                          # Modelo Prophet entrenado
├── data/                            # Datos historicos
└── requirements.txt
```

El frontend deberia ir en `predictabcn/frontend/`.
