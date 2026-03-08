import type { Recomendacion } from "../types";
import { useI18n } from "../i18n";
import { modoIcon, scoreBg, scoreColor, scoreBarColor } from "../utils/colors";

interface Props {
  rec: Recomendacion;
}

export default function RecommendBanner({ rec }: Props) {
  const { t, tr } = useI18n();
  const s = rec.score;

  return (
    <div
      className="mx-5 rounded-2xl p-4 shadow-sm"
      style={{
        background: `linear-gradient(135deg, ${scoreBg(s)}, rgba(198,184,243,0.12))`,
        border: `1px solid ${scoreBarColor(s)}30`,
      }}
    >
      <div className="flex items-center gap-3.5">
        <div
          className="w-14 h-14 rounded-xl flex items-center justify-center text-2xl shadow-sm"
          style={{ background: `${scoreBg(s)}` }}
        >
          {modoIcon[rec.mejor]}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-widest" style={{ color: scoreColor(s) }}>
            {t("ui.best_option")}
          </p>
          <p className="text-[18px] font-bold text-[#2E2E2E] mt-0.5">{t(`modo.${rec.mejor}`)}</p>
        </div>
        <div className="text-right">
          <p className="text-[32px] font-bold leading-none" style={{ color: scoreColor(s) }}>{s}</p>
          <p className="text-[10px] text-[#6B7280] mt-0.5">{t("ui.score_of")}</p>
        </div>
      </div>
      <p className="text-[13px] text-[#6B7280] mt-3 leading-relaxed">
        {rec.explicacion.map((e, i) => <span key={i}>{tr(e)} </span>)}
      </p>
    </div>
  );
}
