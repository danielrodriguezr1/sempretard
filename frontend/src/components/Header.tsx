import type { Contexto } from "../types";
import { useI18n, type Lang } from "../i18n";

interface Props {
  contexto: Contexto;
  activeTab: "ahora" | "prediccion" | "mapa";
  onTabChange: (tab: "ahora" | "prediccion" | "mapa") => void;
  notifEnabled?: boolean;
  onToggleNotif?: () => void;
  hasCritical?: boolean;
}

export default function Header({ contexto, activeTab, onTabChange, notifEnabled, onToggleNotif, hasCritical }: Props) {
  const { t, lang, setLang } = useI18n();
  const { clima, dia_semana, hora, es_festivo } = contexto;

  return (
    <header className="px-5 pt-8 pb-4">
      <div className="flex items-end justify-between mb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-bold tracking-tight text-[#2E2E2E]">
              Sempre<span className="text-[#D46B6B]">Tard</span>
            </h1>
            <LangToggle lang={lang} setLang={setLang} />
            {onToggleNotif && (
              <button
                onClick={onToggleNotif}
                className="relative w-7 h-7 flex items-center justify-center rounded-lg transition-all"
                style={{
                  background: notifEnabled ? "rgba(109,187,139,0.15)" : "rgba(107,114,128,0.08)",
                }}
                title={notifEnabled ? t("ui.notifications_enabled") : t("ui.notifications_disabled")}
              >
                <span className="text-[14px]">{notifEnabled ? "🔔" : "🔕"}</span>
                {hasCritical && notifEnabled && (
                  <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-[#D46B6B] animate-pulse" />
                )}
              </button>
            )}
          </div>
          <p className="text-[13px] text-[#6B7280] mt-0.5">
            {t(`day.${dia_semana}`)} {hora}
            {es_festivo && <span className="text-[#E0A458] font-medium"> — {t("ui.holiday")}</span>}
          </p>
        </div>
        <div className="text-right rounded-xl px-3 py-1.5" style={{ background: "rgba(143,170,220,0.12)" }}>
          <p className="text-[12px] text-[#2E2E2E]/70">{clima.descripcion}</p>
          <p className="text-[11px] text-[#6B7280]">
            {clima.temperatura !== null && `${clima.temperatura}°`}
            {clima.lluvia_mm > 0 && <span className="text-[#8FAADC] font-medium"> · {clima.lluvia_mm}mm</span>}
          </p>
        </div>
      </div>

      <div className="flex gap-1 rounded-2xl p-1" style={{ background: "rgba(198,184,243,0.15)" }}>
        <TabBtn active={activeTab === "ahora"} onClick={() => onTabChange("ahora")} label={t("tabs.now")} />
        <TabBtn active={activeTab === "prediccion"} onClick={() => onTabChange("prediccion")} label={t("tabs.prediction")} />
        <TabBtn active={activeTab === "mapa"} onClick={() => onTabChange("mapa")} label={t("ui.tab_map")} />
      </div>
    </header>
  );
}

function LangToggle({ lang, setLang }: { lang: Lang; setLang: (l: Lang) => void }) {
  return (
    <div className="flex rounded-lg overflow-hidden text-[10px] font-bold" style={{ border: "1px solid #E5E7EB" }}>
      <button
        onClick={() => setLang("ca")}
        className="px-2 py-0.5 transition-all"
        style={{ background: lang === "ca" ? "#8FAADC" : "transparent", color: lang === "ca" ? "white" : "#6B7280" }}
      >
        CA
      </button>
      <button
        onClick={() => setLang("es")}
        className="px-2 py-0.5 transition-all"
        style={{ background: lang === "es" ? "#8FAADC" : "transparent", color: lang === "es" ? "white" : "#6B7280" }}
      >
        ES
      </button>
    </div>
  );
}

function TabBtn({ active, onClick, label }: { active: boolean; onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 py-2.5 text-[13px] font-semibold rounded-xl transition-all ${
        active ? "bg-white text-[#2E2E2E] shadow-sm" : "text-[#6B7280]/60"
      }`}
    >
      {label}
    </button>
  );
}
