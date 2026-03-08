export type Nivel = "normal" | "elevado" | "critico";
export type ModoId = "coche" | "metro" | "bus" | "tren" | "bicing";

/** Backend translatable object */
export interface Translatable {
  key: string;
  params?: Record<string, string | number>;
}

export interface ViaAfectada {
  id: string;
  via: string;
  estado: string;
  prevision: string;
}

export interface ModoStatus {
  modo: ModoId;
  nivel: Nivel;
  score: number;
  resumen: Translatable;
  analisis: {
    tramos_total?: number;
    tramos_activos?: number;
    fluido?: number;
    denso?: number;
    muy_denso?: number;
    congestionado?: number;
    cortado?: number;
    prevision_15min?: string;
    vias_afectadas?: ViaAfectada[];
    lineas_total?: number;
    lineas_ok?: number;
    lineas_afectadas?: string[];
    detalle?: Array<{ linea: string; causa: string }>;
    todas_lineas?: Array<{ linea: string; color: string; estado: string; causa?: string }>;
    // Bicing
    estaciones_total?: number;
    estaciones_activas?: number;
    estaciones_fuera_servicio?: number;
    estaciones_vacias?: number;
    estaciones_llenas?: number;
    bicis_disponibles?: number;
    bicis_mecanicas?: number;
    bicis_electricas?: number;
    anclajes_libres?: number;
    disponibilidad_pct?: number;
  };
  razones: Translatable[];
  fuente: Translatable | string;
  datos_reales: boolean;
  timestamp_datos?: string;
}

export interface Recomendacion {
  mejor: ModoId;
  mejor_label: string;
  score: number;
  explicacion: Translatable[];
  ranking: ModoId[];
  scores_ajustados: Record<ModoId, number>;
}

export interface Contexto {
  clima: { temperatura: number | null; lluvia_mm: number; descripcion: string };
  es_festivo: boolean;
  dia_semana: string;
  hora: string;
  eventos_hoy: Array<{ nombre?: string; name?: string }>;
}

export interface EstadoResponse {
  timestamp: string;
  modos: Record<ModoId, ModoStatus>;
  recomendacion: Recomendacion;
  contexto: Contexto;
  fuentes: Record<ModoId, { fuente: string; datos_reales: boolean }>;
  _cache_hit: boolean;
}

export interface Aviso {
  tipo: string;
  nivel: Nivel;
  modos: ModoId[];
  texto: Translatable;
  lineas?: string[];
}

export interface Consejo {
  icono: string;
  texto: Translatable;
  alternativa: Translatable;
  evitar: ModoId[];
  mejor: ModoId[];
}

export interface Franja {
  id: string;
  label: string;
  rango: string;
  scores: Record<ModoId, number>;
  mejor: ModoId;
  mejor_icon: string;
  score: number;
  source?: "historical" | "rules";
  historical_samples?: number;
}

export interface DiaPrediccion {
  fecha: string;
  dia_semana: string;
  es_festivo: boolean;
  es_finde: boolean;
  clima: { temperatura: number | null; lluvia_mm: number; descripcion: string };
  eventos: {
    total: number;
    masivo: boolean;
    partido_barca: boolean;
    destacados: Array<{ nombre?: string; name?: string }>;
    nombres: string[];
    lineas_afectadas: string[];
  };
  avisos: Aviso[];
  consejos: Consejo[];
  franjas: Franja[];
  nivel: Nivel;
  score: number;
}

export interface PrediccionResponse {
  generado_en: string;
  dias: DiaPrediccion[];
  _cache_hit: boolean;
}

export interface MapaVia {
  id: string;
  via: string;
  estado: string;
  prevision: string;
  lat: number;
  lon: number;
}

export interface BicingStation {
  id: string;
  name: string;
  lat: number;
  lon: number;
  bikes: number;
  mechanical: number;
  electric: number;
  docks: number;
  status: string;
}

export interface SCTIncident {
  id: string;
  lat: number;
  lon: number;
  carretera: string;
  causa: string;
  descripcion: string;
  tipo: string;
  severity: "tallada" | "retencio" | "obres" | "info";
  nivel: number;
  sentido: string;
  hacia: string;
  fecha: string;
  fuente: string;
}

export interface MapaResponse {
  trafico: {
    vias_afectadas: MapaVia[];
    resumen: { nivel: string; score: number };
    timestamp?: string;
  };
  bicing: BicingStation[];
  sct: SCTIncident[];
}
