import { useState, useEffect } from "react";
import type { PrediccionResponse, DiaPrediccion, Consejo, Franja, ModoId } from "../types";
import { fetchPrediccion } from "../api";
import { useI18n } from "../i18n";
import { scoreBg, scoreBorder, scoreColor, scoreBarColor } from "../utils/colors";

export default function Prediccion() {
  const { t } = useI18n();
  const [data, setData] = useState<PrediccionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(0);

  useEffect(() => {
    fetchPrediccion()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="px-5 py-16 flex justify-center">
        <div className="w-7 h-7 border-2 border-[#C6B8F3]/30 border-t-[#C6B8F3] rounded-full animate-spin" />
      </div>
    );
  }

  if (!data) {
    return <p className="px-5 py-16 text-center text-[13px] text-[#6B7280]">{t("ui.error_load")}</p>;
  }

  return (
    <div className="px-5 pb-8 space-y-2">
      {data.dias.map((dia, i) => (
        <DayRow
          key={dia.fecha}
          dia={dia}
          isToday={i === 0}
          open={expanded === i}
          toggle={() => setExpanded(expanded === i ? -1 : i)}
        />
      ))}
    </div>
  );
}

function DayRow({ dia, isToday, open, toggle }: {
  dia: DiaPrediccion; isToday: boolean; open: boolean; toggle: () => void;
}) {
  const { t, tr } = useI18n();
  const s = dia.score;
  const consejos = dia.consejos ?? [];
  const franjas = dia.franjas ?? [];

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ background: scoreBg(s), border: `1px solid ${scoreBorder(s)}` }}
    >
      <button onClick={toggle} className="w-full px-4 py-3.5 flex items-center gap-3 text-left">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-semibold text-[#2E2E2E]">
              {isToday ? t("ui.today") : t(`day.${dia.dia_semana}`)}
            </span>
            <span className="text-[12px] text-[#6B7280]/50">{fmtDate(dia.fecha)}</span>
            {dia.es_festivo && (
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md"
                style={{ background: "rgba(224,164,88,0.15)", color: "#C8852E" }}>
                {t("ui.holiday")}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5 mt-1">
            <span className="text-[11px] text-[#6B7280]">{dia.clima.descripcion}</span>
            {dia.clima.lluvia_mm > 0 && (
              <span className="text-[11px] text-[#8FAADC] font-medium">{dia.clima.lluvia_mm}mm</span>
            )}
            {dia.eventos.partido_barca && (
              <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded-md"
                style={{ background: "rgba(143,170,220,0.18)", color: "#5A7DB5" }}>
                ⚽ Barça
              </span>
            )}
            {dia.eventos.masivo && !dia.eventos.partido_barca && (
              <span className="text-[11px] font-semibold px-1.5 py-0.5 rounded-md"
                style={{ background: "rgba(198,184,243,0.18)", color: "#6B5EAD" }}>
                🎭
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[16px] font-bold" style={{ color: scoreColor(s) }}>{s}</span>
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: scoreBarColor(s) }} />
        </div>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-3 space-y-3" style={{ borderTop: `1px solid ${scoreBorder(s)}` }}>
          {franjas.length > 0 && <FranjaTimeline franjas={franjas} />}

          {consejos.length > 0 && (
            <div className="space-y-2">
              {consejos.map((c, i) => <ConsejoCard key={i} consejo={c} />)}
            </div>
          )}

          {dia.eventos.lineas_afectadas.length > 0 && (
            <div>
              <p className="text-[10px] text-[#6B7280]/40 mb-1.5">{t("ui.affected_lines_label")}</p>
              <div className="flex flex-wrap gap-1">
                {dia.eventos.lineas_afectadas.slice(0, 8).map((l) => (
                  <span key={l} className="text-[10px] font-medium px-2 py-0.5 rounded-md"
                    style={{ background: "rgba(212,107,107,0.08)", color: "#C05050" }}>
                    {l}
                  </span>
                ))}
              </div>
            </div>
          )}

          {consejos.length === 0 && franjas.length === 0 && (
            <p className="text-[12px] text-[#4A9E6B]/60">{t("ui.good_day")}</p>
          )}
        </div>
      )}
    </div>
  );
}

function FranjaTimeline({ franjas }: { franjas: Franja[] }) {
  const { t } = useI18n();
  const [detail, setDetail] = useState<number | null>(null);

  return (
    <div>
      <div className="flex gap-1 mb-1">
        {franjas.map((f, i) => (
          <button
            key={f.id}
            onClick={() => setDetail(detail === i ? null : i)}
            className="flex-1 rounded-lg py-2 flex flex-col items-center gap-0.5 transition-all"
            style={{
              background: `rgba(${scoreToRgb(f.score)},0.15)`,
              border: detail === i ? `1.5px solid rgba(${scoreToRgb(f.score)},0.4)` : "1.5px solid transparent",
            }}
          >
            <span className="text-[14px]">{f.mejor_icon}</span>
            <span className="text-[10px] font-semibold" style={{ color: scoreColor(f.score) }}>
              {f.score}
            </span>
          </button>
        ))}
      </div>

      <div className="flex gap-1">
        {franjas.map((f) => (
          <span key={f.id} className="flex-1 text-center text-[9px] text-[#6B7280]/40">{f.rango}</span>
        ))}
      </div>

      {detail !== null && franjas[detail] && (
        <FranjaDetail franja={franjas[detail]} t={t} />
      )}
    </div>
  );
}

function FranjaDetail({ franja, t }: { franja: Franja; t: (k: string) => string }) {
  const modos: ModoId[] = ["coche", "metro", "bus", "tren", "bicing"];
  const icons: Record<ModoId, string> = { coche: "🚗", metro: "🚇", bus: "🚌", tren: "🚆", bicing: "🚲" };
  const maxScore = Math.max(...Object.values(franja.scores));

  return (
    <div className="mt-2 rounded-xl p-3" style={{ background: "rgba(255,255,255,0.7)" }}>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[11px] font-semibold text-[#2E2E2E]/60">
          {t(`franja.${franja.id}`)} ({franja.rango})
        </p>
        {franja.source === "historical" && (
          <span className="text-[9px] font-medium px-1.5 py-0.5 rounded bg-[#8F7ACF]/10 text-[#8F7ACF]">
            {t("ui.historical_data")} ({franja.historical_samples})
          </span>
        )}
      </div>
      <div className="space-y-1.5">
        {modos
          .sort((a, b) => franja.scores[b] - franja.scores[a])
          .map((m) => {
            const sc = franja.scores[m];
            const isBest = sc === maxScore;
            return (
              <div key={m} className="flex items-center gap-2">
                <span className="text-[12px] w-5 text-center">{icons[m]}</span>
                <span className="text-[11px] w-12 text-[#2E2E2E]/50">{t(`modo.${m}`)}</span>
                <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(0,0,0,0.04)" }}>
                  <div
                    className="h-full rounded-full transition-all"
                    style={{ width: `${sc}%`, background: scoreBarColor(sc) }}
                  />
                </div>
                <span
                  className="text-[11px] w-7 text-right font-semibold"
                  style={{ color: isBest ? scoreColor(sc) : "#6B7280" }}
                >
                  {sc}
                </span>
              </div>
            );
          })}
      </div>
    </div>
  );
}

function ConsejoCard({ consejo }: { consejo: Consejo }) {
  const { t, tr } = useI18n();
  return (
    <div className="rounded-xl p-3" style={{ background: "rgba(255,255,255,0.7)" }}>
      <div className="flex gap-2.5 items-start">
        <span className="text-[18px] mt-0.5 shrink-0">{consejo.icono}</span>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] text-[#2E2E2E] font-medium leading-relaxed">{tr(consejo.texto)}</p>
          <p className="text-[12px] text-[#4A9E6B] mt-1">{tr(consejo.alternativa)}</p>
          <div className="flex items-center gap-3 mt-2">
            {consejo.evitar.length > 0 && (
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-[#C05050]/60">{t("ui.avoid")}</span>
                {consejo.evitar.map((m) => (
                  <span key={m} className="text-[10px] font-semibold px-1.5 py-0.5 rounded"
                    style={{ background: "rgba(212,107,107,0.08)", color: "#C05050" }}>
                    {t(`modo.${m}`)}
                  </span>
                ))}
              </div>
            )}
            {consejo.mejor.length > 0 && (
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-[#4A9E6B]/60">{t("ui.better")}</span>
                {consejo.mejor.map((m) => (
                  <span key={m} className="text-[10px] font-semibold px-1.5 py-0.5 rounded"
                    style={{ background: "rgba(109,187,139,0.10)", color: "#4A9E6B" }}>
                    {t(`modo.${m}`)}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function scoreToRgb(score: number): string {
  if (score >= 80) return "109,187,139";
  if (score >= 60) return "160,200,120";
  if (score >= 40) return "224,164,88";
  return "212,107,107";
}

function fmtDate(iso: string) {
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}
