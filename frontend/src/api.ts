import type { EstadoResponse, PrediccionResponse, MapaResponse } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function fetchEstado(): Promise<EstadoResponse> {
  const res = await fetch(`${BASE}/api/estado`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchPrediccion(): Promise<PrediccionResponse> {
  const res = await fetch(`${BASE}/api/prediccion`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchMapa(): Promise<MapaResponse> {
  const res = await fetch(`${BASE}/api/mapa`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
