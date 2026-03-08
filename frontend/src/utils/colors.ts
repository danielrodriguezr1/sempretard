import type { ModoId } from "../types";

/* ── Dynamic score → pastel color ───────────────────── */

export function scoreBg(score: number): string {
  if (score >= 80) return "rgba(109,187,139,0.18)";
  if (score >= 60) return "rgba(160,200,120,0.18)";
  if (score >= 40) return "rgba(224,164,88,0.16)";
  if (score >= 20) return "rgba(212,107,107,0.14)";
  return "rgba(212,107,107,0.22)";
}

export function scoreBorder(score: number): string {
  if (score >= 80) return "rgba(109,187,139,0.35)";
  if (score >= 60) return "rgba(160,200,120,0.30)";
  if (score >= 40) return "rgba(224,164,88,0.30)";
  if (score >= 20) return "rgba(212,107,107,0.25)";
  return "rgba(212,107,107,0.40)";
}

export function scoreColor(score: number): string {
  if (score >= 80) return "#4A9E6B";
  if (score >= 60) return "#7AAB4A";
  if (score >= 40) return "#C8852E";
  if (score >= 20) return "#C05050";
  return "#B33A3A";
}

export function scoreBarColor(score: number): string {
  if (score >= 80) return "#6DBB8B";
  if (score >= 60) return "#A0C878";
  if (score >= 40) return "#E0A458";
  if (score >= 20) return "#D46B6B";
  return "#C04040";
}

/* ── Mode identity ──────────────────────────────────── */

export const modoIcon: Record<ModoId, string> = {
  coche: "🚗", metro: "🚇", bus: "🚌", tren: "🚆", bicing: "🚲",
};

/* ── Road status ────────────────────────────────────── */

export const estadoViaStyle: Record<string, { bg: string; text: string }> = {
  Cortado:       { bg: "rgba(212,107,107,0.15)", text: "#C05050" },
  Congestionado: { bg: "rgba(212,107,107,0.12)", text: "#C05050" },
  "Muy denso":   { bg: "rgba(224,164,88,0.12)",  text: "#C8852E" },
  Denso:         { bg: "rgba(224,164,88,0.08)",   text: "#B89040" },
};
