import { useState, useEffect, useCallback } from "react";
import type { EstadoResponse, ModoId } from "./types";
import { fetchEstado } from "./api";
import { useI18n } from "./i18n";
import { useAdMobBanner } from "./ads/useAdMob";
import { useNotifications } from "./hooks/useNotifications";
import { useGeolocation } from "./hooks/useGeolocation";
import Header from "./components/Header";
import RecommendBanner from "./components/RecommendBanner";
import ModoCard from "./components/ModoCard";
import ModoDetail from "./components/ModoDetail";
import Prediccion from "./components/Prediccion";
import MapaView from "./components/MapaView";

const REFRESH_MS = 5 * 60 * 1000;
const MODOS: ModoId[] = ["coche", "metro", "bus", "tren", "bicing"];

export default function App() {
  const { t, tr } = useI18n();
  useAdMobBanner();
  const notifications = useNotifications(tr);
  const geo = useGeolocation();
  const [data, setData] = useState<EstadoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<ModoId | null>(null);
  const [tab, setTab] = useState<"ahora" | "prediccion" | "mapa">("ahora");

  const load = useCallback(async () => {
    try {
      setError(null);
      const res = await fetchEstado();
      setData(res);
    } catch (e) {
      setError((e as { message?: string })?.message ?? t("ui.error_load"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => clearInterval(id);
  }, [load]);

  if (loading) return <Loading />;
  if (error || !data) return <Err error={error} onRetry={load} />;

  if (selected && data.modos[selected]) {
    return (
      <ModoDetail
        modo={selected}
        data={data.modos[selected]}
        contexto={data.contexto}
        onBack={() => setSelected(null)}
      />
    );
  }

  return (
    <div className="min-h-screen max-w-lg mx-auto pb-8">
      <Header
        contexto={data.contexto}
        activeTab={tab}
        onTabChange={setTab}
        notifEnabled={notifications.enabled}
        onToggleNotif={() => notifications.setEnabled(!notifications.enabled)}
        hasCritical={notifications.hasCritical}
      />

      {tab === "ahora" ? (
        <>
          <RecommendBanner rec={data.recomendacion} />
          <div className="px-5 mt-5 space-y-2.5">
            {MODOS.map((m) => (
              <ModoCard
                key={m}
                modo={m}
                data={data.modos[m]}
                isBest={data.recomendacion.mejor === m}
                onClick={() => setSelected(m)}
              />
            ))}
          </div>
          <p className="text-center text-[11px] text-muted/40 mt-6">
            {data.timestamp.replace("T", " ")}
          </p>
        </>
      ) : tab === "prediccion" ? (
        <Prediccion />
      ) : (
        <MapaView geo={geo} />
      )}
    </div>
  );
}

function Loading() {
  const { t } = useI18n();
  return (
    <div className="min-h-screen bg-bg flex flex-col items-center justify-center gap-5">
      <div className="w-8 h-8 border-2 border-secondary/30 border-t-secondary rounded-full animate-spin" />
      <div className="text-center">
        <p className="text-[16px] font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
          {t("app.name")}
        </p>
        <p className="text-[12px] text-muted mt-1">{t("ui.loading")}</p>
      </div>
    </div>
  );
}

function Err({ error, onRetry }: { error: string | null; onRetry: () => void }) {
  const { t } = useI18n();
  return (
    <div className="min-h-screen bg-bg flex flex-col items-center justify-center gap-5 px-10">
      <div className="w-14 h-14 rounded-2xl bg-accent/30 flex items-center justify-center text-2xl">⚠️</div>
      <p className="text-[14px] text-ink text-center font-medium">{t("ui.error_load")}</p>
      <p className="text-[12px] text-muted text-center">{error}</p>
      <button
        onClick={onRetry}
        className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-primary to-secondary text-white text-[13px] font-semibold shadow-sm"
      >
        {t("ui.retry")}
      </button>
    </div>
  );
}
