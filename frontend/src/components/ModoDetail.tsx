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
          : modo === "metro" ? <MetroDetail analisis={data.analisis} />
          : modo === "tren" ? <TrenDetail analisis={data.analisis} />
          : <BusDetail analisis={data.analisis} />}

        <p className="text-[10px] text-[#6B7280]/30 pt-2">
          {typeof data.fuente === "string" ? data.fuente : tr(data.fuente)} · {data.datos_reales ? t("ui.real_data") : t("ui.estimation")}
        </p>
      </div>
    </div>
  );
}

/** Resolve causa which can be a plain string or {es:"...", ca:"..."} dict */
function useCausa(causa: string | Record<string, string> | undefined): string {
  const { lang } = useI18n();
  if (!causa) return "";
  if (typeof causa === "string") return causa;
  return causa[lang] ?? causa["es"] ?? Object.values(causa)[0] ?? "";
}

/* ------------------------------------------------------------------ */
/*  Shared line card used by Metro and Tren                           */
/* ------------------------------------------------------------------ */

function LineCard({
  line,
  incident,
  isExpanded,
  onToggle,
  showRoute,
}: {
  line: { linea: string; color: string; estado: string; recorrido?: string };
  incident?: { linea: string; causa: string | Record<string, string> };
  isExpanded: boolean;
  onToggle: () => void;
  showRoute: boolean;
}) {
  const { t } = useI18n();
  const causaText = useCausa(incident?.causa);
  const hasIssue = line.estado === "incidencia";
  const lineColor = line.color.startsWith("#") ? line.color : `#${line.color}`;
  const shortName = line.linea.length <= 3;

  return (
    <div
      className="rounded-xl overflow-hidden transition-all duration-200"
      style={{
        background: hasIssue ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.7)",
        border: hasIssue ? "1px solid rgba(212,107,107,0.2)" : "1px solid rgba(0,0,0,0.04)",
      }}
      onClick={() => hasIssue && onToggle()}
    >
      <div className="flex items-center gap-3 px-3 py-2.5">
        <div
          className={`${shortName ? "w-10 h-10 rounded-xl" : "h-9 px-2.5 rounded-lg"} flex items-center justify-center shrink-0`}
          style={{ background: lineColor }}
        >
          <span className={`text-white font-bold ${shortName ? "text-[13px]" : "text-[11px]"}`}>
            {line.linea}
          </span>
        </div>

        <div className="flex-1 min-w-0">
          {showRoute && line.recorrido && (
            <p className="text-[10px] text-[#9CA3AF] leading-tight">{line.recorrido}</p>
          )}
          <p className="text-[11px] mt-0.5"
            style={{ color: hasIssue ? "#C05050" : "#4A9E6B" }}>
            {hasIssue ? "⚠ " + t("ui.active_incidents") : "✓ OK"}
          </p>
        </div>

        <div className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ background: hasIssue ? "#C05050" : "#4A9E6B" }} />

        {hasIssue && (
          <span className="text-[#9CA3AF] text-[12px] shrink-0">
            {isExpanded ? "▲" : "▼"}
          </span>
        )}
      </div>

      {isExpanded && causaText && (
        <div className="px-3 pb-3 pt-0 border-t"
          style={{ borderColor: "rgba(212,107,107,0.1)" }}>
          <p className="text-[12px] text-[#2E2E2E]/70 leading-relaxed pt-2 whitespace-pre-wrap">
            {causaText}
          </p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Summary strip (shared by Metro and Tren)                          */
/* ------------------------------------------------------------------ */

function LineSummaryStrip({ ok, issues }: { ok: number; issues: number }) {
  const { t } = useI18n();
  return (
    <div className="flex gap-3 text-[11px]">
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
        style={{ background: "rgba(109,187,139,0.12)", color: "#4A9E6B" }}>
        <span className="w-1.5 h-1.5 rounded-full bg-[#4A9E6B]" />
        {ok} OK
      </div>
      {issues > 0 && (
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full"
          style={{ background: "rgba(212,107,107,0.12)", color: "#C05050" }}>
          <span className="w-1.5 h-1.5 rounded-full bg-[#C05050]" />
          {issues} {t("ui.active_incidents").toLowerCase()}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Metro — visual diagram of all lines                               */
/* ------------------------------------------------------------------ */

function MetroDetail({ analisis }: { analisis: ModoStatus["analisis"] }) {
  const { t } = useI18n();
  const allLines = analisis.todas_lineas ?? [];
  const detalle = analisis.detalle ?? [];
  const [expanded, setExpanded] = useState<string | null>(null);

  if (allLines.length === 0 && detalle.length === 0) {
    return <p className="text-[13px] text-[#6B7280]/50">{t("ui.no_incidents")}</p>;
  }

  const linesOk = allLines.filter(l => l.estado === "normal").length;
  const linesIssue = allLines.filter(l => l.estado === "incidencia").length;

  return (
    <div className="space-y-4">
      <LineSummaryStrip ok={linesOk} issues={linesIssue} />
      <div className="space-y-2">
        {allLines.map((line) => (
          <LineCard
            key={line.linea}
            line={line}
            incident={detalle.find(d => d.linea === line.linea)}
            isExpanded={expanded === line.linea}
            onToggle={() => setExpanded(expanded === line.linea ? null : line.linea)}
            showRoute={false}
          />
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Tren (Rodalies) — visual line cards with route info               */
/* ------------------------------------------------------------------ */

function TrenDetail({ analisis }: { analisis: ModoStatus["analisis"] }) {
  const { t } = useI18n();
  const allLines = analisis.todas_lineas ?? [];
  const detalle = analisis.detalle ?? [];
  const [expanded, setExpanded] = useState<string | null>(null);

  if (allLines.length === 0 && detalle.length === 0) {
    return <p className="text-[13px] text-[#6B7280]/50">{t("ui.no_incidents")}</p>;
  }

  const linesOk = allLines.filter(l => l.estado === "normal").length;
  const linesIssue = allLines.filter(l => l.estado === "incidencia").length;

  return (
    <div className="space-y-4">
      <LineSummaryStrip ok={linesOk} issues={linesIssue} />
      <div className="space-y-2">
        {allLines.map((line) => (
          <LineCard
            key={line.linea}
            line={line}
            incident={detalle.find(d => d.linea === line.linea)}
            isExpanded={expanded === line.linea}
            onToggle={() => setExpanded(expanded === line.linea ? null : line.linea)}
            showRoute={true}
          />
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Car detail                                                        */
/* ------------------------------------------------------------------ */

function TrafficStateBar({ segments }: { segments: { label: string; count: number; color: string }[] }) {
  const total = segments.reduce((s, x) => s + x.count, 0);
  if (total === 0) return null;
  return (
    <div>
      <div className="flex h-3 rounded-full overflow-hidden">
        {segments.filter(s => s.count > 0).map((s) => (
          <div key={s.label} style={{ width: `${(s.count / total) * 100}%`, background: s.color }} />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
        {segments.filter(s => s.count > 0).map((s) => (
          <span key={s.label} className="flex items-center gap-1 text-[10px] text-[#6B7280]">
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: s.color }} />
            {s.count} {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}

function CarDetail({ analisis }: { analisis: ModoStatus["analisis"] }) {
  const { t } = useI18n();
  const [showAll, setShowAll] = useState(false);

  const hasCity = analisis.tramos_activos != null;
  const hasSCT = (analisis.sct_total_incidencias ?? 0) > 0 || (analisis.sct_carreteras_afectadas ?? []).length > 0;

  if (!hasCity && !hasSCT) return null;

  const vias = analisis.vias_afectadas ?? [];
  const total = analisis.tramos_activos ?? 0;
  const fluido = analisis.fluido ?? 0;
  const denso = analisis.denso ?? 0;
  const muyDenso = analisis.muy_denso ?? 0;
  const congestionado = analisis.congestionado ?? 0;
  const cortado = analisis.cortado ?? 0;
  const prevision = analisis.prevision_15min;
  const visible = showAll ? vias : vias.slice(0, 5);

  const sctRet = analisis.sct_retenciones ?? 0;
  const sctCut = analisis.sct_cortadas ?? 0;
  const sctTotal = analisis.sct_total_incidencias ?? 0;
  const sctRoads = analisis.sct_carreteras_afectadas ?? [];

  const segments = [
    { label: t("car.segments_fluid"), count: fluido, color: "#6DBB8B" },
    { label: t("car.segments_dense"), count: denso, color: "#C8A04A" },
    { label: t("car.segments_very_dense"), count: muyDenso, color: "#E0A458" },
    { label: t("car.segments_congested"), count: congestionado, color: "#D46B6B" },
    { label: t("car.segments_cut"), count: cortado, color: "#C04040" },
  ];

  const forecastColor = prevision === "mejorando" ? "#4A9E6B" : prevision === "empeorando" ? "#C05050" : "#6B7280";
  const forecastLabel = prevision === "mejorando" ? t("car.forecast_improving")
    : prevision === "empeorando" ? t("car.forecast_worsening")
    : t("car.forecast_stable");
  const forecastIcon = prevision === "mejorando" ? "↗" : prevision === "empeorando" ? "↘" : "→";

  return (
    <div className="space-y-5">
      {hasCity && (
        <div className="space-y-3">
          <p className="text-[11px] font-bold text-[#2E2E2E]/50 uppercase tracking-wide">
            {t("car.section_city")}
          </p>

          <TrafficStateBar segments={segments} />

          <p className="text-[11px] text-[#6B7280]">
            {t("ui.fluid_pct", { pct: total > 0 ? Math.round((fluido / total) * 100) : 0, total })}
          </p>

          {prevision && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl"
              style={{ background: `${forecastColor}10`, border: `1px solid ${forecastColor}20` }}>
              <span className="text-[16px]">{forecastIcon}</span>
              <div>
                <p className="text-[11px] font-semibold" style={{ color: forecastColor }}>
                  {t("car.forecast_15")}: {forecastLabel}
                </p>
              </div>
            </div>
          )}

          {vias.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold text-[#6B7280] mb-2">
                {t("ui.roads_issues", { count: vias.length })}
              </p>
              <div className="space-y-1">
                {visible.map((v: ViaAfectada, i: number) => {
                  const st = estadoViaStyle[v.estado] ?? { bg: "rgba(107,114,128,0.06)", text: "#6B7280" };
                  return (
                    <div key={i} className="flex items-center gap-2 py-1.5 px-2 rounded-lg"
                      style={{ background: "rgba(255,255,255,0.6)" }}>
                      <span
                        className="text-[10px] font-semibold px-2 py-0.5 rounded-md shrink-0"
                        style={{ background: st.bg, color: st.text }}
                      >
                        {t(`severity.${v.estado}`)}
                      </span>
                      <span className="text-[12px] text-[#2E2E2E]/60 truncate flex-1">{v.via}</span>
                      {v.prevision && (
                        <span className="text-[9px] text-[#9CA3AF] shrink-0">
                          → {v.prevision}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
              {vias.length > 5 && (
                <button
                  onClick={() => setShowAll(!showAll)}
                  className="text-[12px] text-[#8F7ACF] font-medium mt-2"
                >
                  {showAll ? t("ui.see_less") : t("ui.see_all", { count: vias.length })}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {hasSCT && (
        <div className="space-y-3">
          <p className="text-[11px] font-bold text-[#2E2E2E]/50 uppercase tracking-wide">
            {t("car.section_metro")}
          </p>

          <div className="grid grid-cols-2 gap-2">
            {sctRet > 0 && (
              <div className="rounded-xl px-3 py-2.5" style={{ background: "rgba(224,112,64,0.08)" }}>
                <p className="text-[18px] font-bold text-[#E07040]">{sctRet}</p>
                <p className="text-[10px] text-[#6B7280]">{t("car.sct_retentions", { count: sctRet }).replace(/^\d+\s*/, "")}</p>
              </div>
            )}
            {sctCut > 0 && (
              <div className="rounded-xl px-3 py-2.5" style={{ background: "rgba(192,64,64,0.08)" }}>
                <p className="text-[18px] font-bold text-[#C04040]">{sctCut}</p>
                <p className="text-[10px] text-[#6B7280]">{t("car.sct_cuts", { count: sctCut }).replace(/^\d+\s*/, "")}</p>
              </div>
            )}
            {sctTotal > 0 && sctRet === 0 && sctCut === 0 && (
              <div className="rounded-xl px-3 py-2.5" style={{ background: "rgba(156,163,175,0.08)" }}>
                <p className="text-[18px] font-bold text-[#6B7280]">{sctTotal}</p>
                <p className="text-[10px] text-[#6B7280]">{t("car.sct_total", { count: sctTotal }).replace(/^\d+\s*/, "")}</p>
              </div>
            )}
          </div>

          {sctRoads.length > 0 && (
            <div>
              <p className="text-[10px] text-[#9CA3AF] mb-1.5">{t("car.sct_roads_affected")}</p>
              <div className="flex flex-wrap gap-1.5">
                {sctRoads.map((road: string) => (
                  <span key={road} className="px-2.5 py-1 rounded-lg text-[11px] font-semibold"
                    style={{ background: "rgba(224,112,64,0.1)", color: "#C05050" }}>
                    {road}
                  </span>
                ))}
              </div>
            </div>
          )}

          {sctTotal === 0 && (
            <p className="text-[12px] text-[#4A9E6B]">✓ {t("car.sct_no_incidents")}</p>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Bus detail                                                        */
/* ------------------------------------------------------------------ */

function BusDetail({ analisis }: { analisis: ModoStatus["analisis"] }) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState<string | null>(null);
  const totalLines = analisis.lineas_total ?? 0;
  const okLines = analisis.lineas_ok ?? 0;
  const detalle = analisis.detalle ?? [];
  const nAffected = analisis.lineas_afectadas?.length ?? detalle.length;

  return (
    <div className="space-y-4">
      {totalLines > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <p className="text-[13px] font-semibold text-[#2E2E2E]/70">
              {t("bus.total_lines", { total: totalLines })}
            </p>
          </div>

          <div className="flex h-2.5 rounded-full overflow-hidden">
            {okLines > 0 && (
              <div style={{ width: `${(okLines / totalLines) * 100}%`, background: "#6DBB8B" }} />
            )}
            {nAffected > 0 && (
              <div style={{ width: `${(nAffected / totalLines) * 100}%`, background: "#D46B6B" }} />
            )}
          </div>

          <div className="flex gap-3">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px]"
              style={{ background: "rgba(109,187,139,0.12)", color: "#4A9E6B" }}>
              <span className="w-1.5 h-1.5 rounded-full bg-[#4A9E6B]" />
              {t("bus.lines_ok", { count: okLines })}
            </div>
            {nAffected > 0 && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px]"
                style={{ background: "rgba(212,107,107,0.12)", color: "#C05050" }}>
                <span className="w-1.5 h-1.5 rounded-full bg-[#C05050]" />
                {t("bus.lines_affected", { count: nAffected })}
              </div>
            )}
          </div>
        </div>
      )}

      {nAffected === 0 && (
        <p className="text-[13px] text-[#4A9E6B]">✓ {t("bus.all_ok")}</p>
      )}

      {detalle.length > 0 && (
        <div className="space-y-2">
          <p className="text-[11px] font-bold text-[#2E2E2E]/50 uppercase tracking-wide">
            {t("bus.affected_lines")}
          </p>
          {detalle.map((d, i) => {
            const isExp = expanded === d.linea;
            return (
              <div key={i}
                className="rounded-xl overflow-hidden transition-all"
                style={{
                  background: "rgba(255,255,255,0.95)",
                  border: "1px solid rgba(212,107,107,0.15)",
                }}
                onClick={() => setExpanded(isExp ? null : d.linea)}
              >
                <div className="flex items-center gap-3 px-3 py-2.5">
                  <span className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 text-white text-[12px] font-bold"
                    style={{ background: "#C05050" }}>
                    {d.linea}
                  </span>
                  <p className="text-[12px] text-[#C05050] flex-1">⚠ {t("ui.active_incidents")}</p>
                  <span className="text-[#9CA3AF] text-[12px]">{isExp ? "▲" : "▼"}</span>
                </div>
                {isExp && d.causa && (
                  <div className="px-3 pb-3 pt-0 border-t" style={{ borderColor: "rgba(212,107,107,0.1)" }}>
                    <p className="text-[12px] text-[#2E2E2E]/70 leading-relaxed pt-2 whitespace-pre-wrap">
                      {typeof d.causa === "string" ? d.causa : d.causa?.es ?? Object.values(d.causa)[0] ?? ""}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Bicing detail                                                     */
/* ------------------------------------------------------------------ */

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
