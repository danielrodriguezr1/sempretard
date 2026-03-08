import type { ModoId, ModoStatus } from "../types";
import { useI18n } from "../i18n";
import { modoIcon, scoreBg, scoreBorder, scoreColor, scoreBarColor } from "../utils/colors";

interface Props {
  modo: ModoId;
  data: ModoStatus;
  isBest: boolean;
  onClick: () => void;
}

export default function ModoCard({ modo, data, isBest, onClick }: Props) {
  const { t, tr } = useI18n();
  const s = data.score;

  return (
    <button
      onClick={onClick}
      className="w-full text-left rounded-2xl p-4 transition-all active:scale-[0.98] hover:shadow-md"
      style={{ background: scoreBg(s), borderWidth: 1, borderColor: scoreBorder(s) }}
    >
      <div className="flex items-center gap-3.5">
        <div
          className="w-11 h-11 rounded-xl flex items-center justify-center text-xl shrink-0"
          style={{ background: scoreBg(s) }}
        >
          {modoIcon[modo]}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[15px] font-semibold text-[#2E2E2E]">{t(`modo.${modo}`)}</span>
            <span className="w-2 h-2 rounded-full" style={{ background: scoreBarColor(s) }} />
            <span className="text-[12px] font-semibold" style={{ color: scoreColor(s) }}>
              {t(`nivel.${data.nivel}`)}
            </span>
            {isBest && (
              <span className="ml-auto text-[10px] font-bold text-[#8F7ACF] bg-[#C6B8F3]/20 px-2 py-0.5 rounded-full">
                {t("ui.top")}
              </span>
            )}
          </div>
          <p className="text-[12px] text-[#6B7280] mt-1 line-clamp-1">{tr(data.resumen)}</p>
        </div>
        <div className="text-right pl-2 shrink-0">
          <p className="text-[24px] font-bold leading-none" style={{ color: scoreColor(s) }}>{s}</p>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2">
        <div className="flex-1 h-1.5 rounded-full bg-white/60 overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${s}%`, background: scoreBarColor(s) }}
          />
        </div>
        <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-md shrink-0 ${
          data.datos_reales
            ? "bg-[#6DBB8B]/15 text-[#4A9E6B]"
            : "bg-[#E0A458]/15 text-[#C8852E]"
        }`}>
          {data.datos_reales ? t("ui.real_data") : t("ui.estimation")}
        </span>
      </div>
    </button>
  );
}
