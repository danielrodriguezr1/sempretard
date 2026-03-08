import { useState } from "react";
import type { ModoId, ModoStatus, Contexto, ViaAfectada } from "../types";
import { useI18n } from "../i18n";
import {
  modoIcon, scoreColor, scoreBarColor,
  scoreBg, scoreBorder, estadoViaStyle,
} from "../utils/colors";

interface Props {
  modo: ModoId;
  data: ModoStatus;
  contexto: Contexto;
  onBack: () => void;
}

export default function ModoDetail({ modo, data, contexto: _ctx, onBack }: Props) {
  const { t, tr } = useI18n();
  const s = data.score;

  const trendKey = typeof data.analisis.prevision_15min === "string"
    ? `trend.${data.analisis.prevision_15min === "mejorando" ? "improving" : data.analisis.prevision_15min === "empeorando" ? "worsening" : "stable"}`
    : null;

  return (
    <div className="min-h-screen" style={{ background: "#F4F1F8" }}>
      <div style={{ background: scoreBg(s), borderBottom: `1px solid ${scoreBorder(s)}` }}>
        <div className="flex items-center gap-3 px-5 pt-5 pb-3">
          <button
            onClick={onBack}
            className="w-8 h-8 flex items-center justify-center rounded-full bg-white/60 text-[#6B7280]"
          >
            ‹
          </button>
          <span className="text-xl">{modoIcon[modo]}</span>
          <span className="text-[17px] font-bold text-[#2E2E2E]">{t(`modo.${modo}`)}</span>
          <span className="ml-auto text-[28px] font-bold" style={{ color: scoreColor(s) }}>{s}</span>
        </div>

        <div className="px-5 pb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full" style={{ background: scoreBarColor(s) }} />
            <span className="text-[12px] font-semibold" style={{ color: scoreColor(s) }}>
              {t(`nivel.${data.nivel}`)}
            </span>
            {trendKey && modo === "coche" && (
              <span className="text-[12px] ml-2" style={{
                color: data.analisis.prevision_15min === "mejorando" ? "#4A9E6B"
                  : data.analisis.prevision_15min === "empeorando" ? "#C05050" : "#6B7280"
              }}>
                {t(trendKey)}
              </span>
            )}
          </div>
          <div className="h-1.5 rounded-full bg-white/50 overflow-hidden">
            <div className="h-full rounded-full" style={{ width: `${s}%`, background: scoreBarColor(s) }} />
          </div>
        </div>
      </div>

      <div className="px-5 py-5 space-y-5">
        <p className="text-[14px] text-[#2E2E2E]/80 leading-relaxed">{tr(data.resumen)}</p>

        {modo === "coche" ? <CarDetail analisis={data.analisis} />
          : modo === "bicing" ? <BicingDetail analisis={data.analisis} />
          : <TransportDetail analisis={data.analisis} />}

        <p className="text-[10px] text-[#6B7280]/30 pt-2">
          {typeof data.fuente === "string" ? data.fuente : tr(data.fuente)} · {data.datos_reales ? t("ui.real_data") : t("ui.estimation")}
        </p>
      </div>
    </div>
  );
}

function CarDetail({ analisis }: { analisis: ModoStatus["analisis"] }) {
  const { t } = useI18n();
  const [showAll, setShowAll] = useState(false);
  if (analisis.tramos_activos == null) return null;

  const vias = analisis.vias_afectadas ?? [];
  const total = analisis.tramos_activos ?? 0;
  const fluido = analisis.fluido ?? 0;
  const pctFluido = total > 0 ? Math.round((fluido / total) * 100) : 0;
  const visible = showAll ? vias : vias.slice(0, 5);

  return (
    <>
      <div>
        <div className="h-2.5 rounded-full overflow-hidden" style={{ background: "rgba(212,107,107,0.10)" }}>
          <div className="h-full rounded-full" style={{ width: `${pctFluido}%`, background: "#6DBB8B" }} />
        </div>
        <p className="text-[11px] text-[#6B7280] mt-1.5">
          {t("ui.fluid_pct", { pct: pctFluido, total })}
        </p>
      </div>

      {vias.length > 0 && (
        <div>
          <p className="text-[11px] font-semibold text-[#6B7280] mb-2">
            {t("ui.roads_issues", { count: vias.length })}
          </p>
          <div className="space-y-1">
            {visible.map((v: ViaAfectada, i: number) => {
              const st = estadoViaStyle[v.estado] ?? { bg: "rgba(107,114,128,0.06)", text: "#6B7280" };
              return (
                <div key={i} className="flex items-center gap-2 py-1.5">
                  <span
                    className="text-[10px] font-semibold px-2 py-0.5 rounded-md shrink-0"
                    style={{ background: st.bg, color: st.text }}
                  >
                    {t(`severity.${v.estado}`)}
                  </span>
                  <span className="text-[12px] text-[#2E2E2E]/60 truncate">{v.via}</span>
                </div>
              );
            })}
          </div>
          {vias.length > 5 && (
            <button
              onClick={() => setShowAll(!showAll)}
              className="text-[12px] text-[#8FAADC] font-medium mt-2"
            >
              {showAll ? t("ui.see_less") : t("ui.see_all", { count: vias.length })}
            </button>
          )}
        </div>
      )}
    </>
  );
}

function TransportDetail({ analisis }: { analisis: ModoStatus["analisis"] }) {
  const { t } = useI18n();
  const allLines = analisis.todas_lineas ?? [];
  const detalle = analisis.detalle ?? [];

  if (allLines.length > 0) {
    return (
      <div className="space-y-3">
        <div className="flex flex-wrap gap-1.5">
          {allLines.map((line) => {
            const hasIssue = line.estado === "incidencia";
            return (
              <div
                key={line.linea}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold"
                style={{
                  background: hasIssue ? "rgba(212,107,107,0.12)" : "rgba(109,187,139,0.12)",
                  color: hasIssue ? "#C05050" : "#4A9E6B",
                  border: `1px solid ${hasIssue ? "rgba(212,107,107,0.25)" : "rgba(109,187,139,0.25)"}`,
                }}
              >
                {line.color && (
                  <span className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ background: line.color.startsWith("#") ? line.color : `#${line.color}` }} />
                )}
                <span>{line.linea}</span>
                <span>{hasIssue ? "⚠" : "✓"}</span>
              </div>
            );
          })}
        </div>
        {detalle.length > 0 && (
          <div className="space-y-2 pt-1">
            {detalle.map((d, i) => (
              <div key={i} className="flex gap-2.5 items-start py-1.5">
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-md shrink-0 mt-0.5"
                  style={{ background: "rgba(212,107,107,0.10)", color: "#C05050" }}>
                  {d.linea}
                </span>
                <p className="text-[12px] text-[#2E2E2E]/60 leading-relaxed">{d.causa}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (detalle.length === 0) {
    return <p className="text-[13px] text-[#6B7280]/50">{t("ui.no_incidents")}</p>;
  }

  return (
    <div className="space-y-2">
      {detalle.map((d, i) => (
        <div key={i} className="flex gap-2.5 items-start py-1.5">
          <span
            className="text-[11px] font-bold px-2 py-0.5 rounded-md shrink-0 mt-0.5"
            style={{ background: "rgba(212,107,107,0.10)", color: "#C05050" }}
          >
            {d.linea}
          </span>
          <p className="text-[12px] text-[#2E2E2E]/60 leading-relaxed">{d.causa}</p>
        </div>
      ))}
    </div>
  );
}

function BicingDetail({ analisis }: { analisis: ModoStatus["analisis"] }) {
  const { t } = useI18n();
  const bikes = analisis.bicis_disponibles ?? 0;
  const mechanical = analisis.bicis_mecanicas ?? 0;
  const electric = analisis.bicis_electricas ?? 0;
  const docks = analisis.anclajes_libres ?? 0;
  const active = analisis.estaciones_activas ?? 0;
  const out = analisis.estaciones_fuera_servicio ?? 0;
  const empty = analisis.estaciones_vacias ?? 0;
  const full = analisis.estaciones_llenas ?? 0;
  const pct = analisis.disponibilidad_pct ?? 0;

  return (
    <div className="space-y-4">
      <div>
        <div className="h-2.5 rounded-full overflow-hidden" style={{ background: "rgba(212,107,107,0.10)" }}>
          <div className="h-full rounded-full" style={{ width: `${pct}%`, background: "#6DBB8B" }} />
        </div>
        <p className="text-[11px] text-[#6B7280] mt-1.5">
          {t("bicing.reason_bikes", { bikes, mechanical, electric })}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <StatBox label="🚲" value={String(bikes)} sub={t("ui.bicing_bikes")} color="#4A9E6B" />
        <StatBox label="🔌" value={String(electric)} sub={t("ui.bicing_electric")} color="#8FAADC" />
        <StatBox label="🅿️" value={String(docks)} sub={t("ui.bicing_docks")} color="#6B7280" />
        <StatBox label="📍" value={String(active)} sub={t("ui.bicing_stations")} color="#8F7ACF" />
      </div>

      {(empty > 0 || full > 0 || out > 0) && (
        <div className="space-y-1.5">
          {empty > 0 && (
            <div className="flex items-center gap-2 py-1">
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md"
                style={{ background: "rgba(224,164,88,0.12)", color: "#C8852E" }}>⚠</span>
              <span className="text-[12px] text-[#2E2E2E]/60">{t("bicing.reason_empty", { count: empty })}</span>
            </div>
          )}
          {full > 0 && (
            <div className="flex items-center gap-2 py-1">
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md"
                style={{ background: "rgba(224,164,88,0.12)", color: "#C8852E" }}>⚠</span>
              <span className="text-[12px] text-[#2E2E2E]/60">{t("bicing.reason_full", { count: full })}</span>
            </div>
          )}
          {out > 0 && (
            <div className="flex items-center gap-2 py-1">
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md"
                style={{ background: "rgba(212,107,107,0.10)", color: "#C05050" }}>✕</span>
              <span className="text-[12px] text-[#2E2E2E]/60">{t("bicing.reason_stations", { active, out })}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value, sub, color }: { label: string; value: string; sub: string; color: string }) {
  return (
    <div className="rounded-xl p-3 text-center" style={{ background: "rgba(255,255,255,0.7)" }}>
      <span className="text-[14px]">{label}</span>
      <p className="text-[20px] font-bold mt-0.5" style={{ color }}>{value}</p>
      <p className="text-[10px] text-[#6B7280] mt-0.5">{sub}</p>
    </div>
  );
}
