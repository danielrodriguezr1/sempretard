import { useState, useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, Circle, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import type { MapaResponse, BicingStation, MapaVia, SCTIncident } from "../types";
import { fetchMapa } from "../api";
import { useI18n } from "../i18n";
import type { GeoState } from "../hooks/useGeolocation";
import "leaflet/dist/leaflet.css";

const BCN_CENTER: [number, number] = [41.3874, 2.1686];
const BCN_ZOOM = 13;
const USER_ZOOM = 14;

const VIA_COLORS: Record<string, string> = {
  Cortado: "#C04040",
  Congestionado: "#D46B6B",
  "Muy denso": "#E0A458",
  Denso: "#C8A04A",
};

const SCT_COLORS: Record<string, string> = {
  tallada: "#C04040",
  retencio: "#E07040",
  obres: "#C8A04A",
  info: "#9CA3AF",
};

const userIcon = L.divIcon({
  html: '<div style="width:16px;height:16px;background:#8F7ACF;border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.3)"></div>',
  iconSize: [16, 16],
  iconAnchor: [8, 8],
  className: "",
});

function bicingColor(station: BicingStation): string {
  if (station.status !== "IN_SERVICE") return "#9CA3AF";
  if (station.bikes === 0) return "#C04040";
  if (station.bikes <= 3) return "#E0A458";
  return "#6DBB8B";
}

function bicingRadius(station: BicingStation): number {
  if (station.bikes === 0) return 4;
  if (station.bikes <= 3) return 5;
  return 6;
}

type Layer = "bicing" | "trafico" | "all";

interface Props {
  geo: GeoState;
}

function RecenterMap({ center, zoom }: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom, { animate: true });
  }, [map, center[0], center[1], zoom]);
  return null;
}

export default function MapaView({ geo }: Props) {
  const { t, lang } = useI18n();
  const [data, setData] = useState<MapaResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [layer, setLayer] = useState<Layer>("all");

  useEffect(() => {
    fetchMapa()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const mapCenter: [number, number] = geo.position
    ? [geo.position.lat, geo.position.lon]
    : BCN_CENTER;
  const mapZoom = geo.position ? USER_ZOOM : BCN_ZOOM;

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

  const showBicing = layer === "all" || layer === "bicing";
  const showTrafico = layer === "all" || layer === "trafico";
  const showSCT = layer === "all" || layer === "trafico";

  const sctRetencions = (data.sct || []).filter((i) => i.severity === "retencio" || i.severity === "tallada").length;

  return (
    <div className="px-3 pb-4">
      {!geo.enabled && (
        <button
          onClick={geo.requestPermission}
          className="w-full mb-3 py-2.5 rounded-xl text-[12px] font-semibold text-[#8F7ACF] transition-all"
          style={{ background: "rgba(198,184,243,0.15)", border: "1px solid rgba(198,184,243,0.3)" }}
        >
          {t("ui.enable_location")}
        </button>
      )}

      <div className="flex gap-1.5 mb-3 justify-center flex-wrap">
        {(["all", "trafico", "bicing"] as Layer[]).map((l) => (
          <button
            key={l}
            onClick={() => setLayer(l)}
            className={`px-4 py-1.5 rounded-lg text-[11px] font-semibold transition-all ${
              layer === l
                ? "bg-[#8F7ACF] text-white shadow-sm"
                : "bg-white/60 text-[#6B7280]"
            }`}
          >
            {l === "all"
              ? t("ui.map_all")
              : l === "trafico"
                ? t("ui.map_traffic_label")
                : "Bicing"}
          </button>
        ))}
      </div>

      <div className="rounded-2xl overflow-hidden shadow-md" style={{ height: "55vh" }}>
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          style={{ height: "100%", width: "100%" }}
          zoomControl={false}
        >
          <RecenterMap center={mapCenter} zoom={mapZoom} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />

          {geo.position && (
            <>
              <Marker position={[geo.position.lat, geo.position.lon]} icon={userIcon} />
              <Circle
                center={[geo.position.lat, geo.position.lon]}
                radius={geo.position.accuracy}
                pathOptions={{ color: "#8F7ACF", fillColor: "#8F7ACF", fillOpacity: 0.08, weight: 1 }}
              />
            </>
          )}

          {showTrafico && data.trafico.vias_afectadas.map((via) => (
            <TrafficMarker key={via.id} via={via} t={t} />
          ))}

          {showSCT && (data.sct || []).map((inc) => (
            <SCTMarker key={inc.id} incident={inc} lang={lang} />
          ))}

          {showBicing && data.bicing.map((station) => (
            <BicingMarker key={station.id} station={station} />
          ))}
        </MapContainer>
      </div>

      <div className="mt-3 flex flex-wrap gap-3 justify-center">
        {showBicing && (
          <div className="flex items-center gap-3 text-[10px] text-[#6B7280]">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#6DBB8B]" /> {t("ui.map_bikes_ok")}</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#E0A458]" /> {t("ui.map_bikes_low")}</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#C04040]" /> {t("ui.map_bikes_empty")}</span>
          </div>
        )}
        {(showTrafico || showSCT) && (
          <div className="flex items-center gap-3 text-[10px] text-[#6B7280]">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#C8A04A]" /> {t("ui.map_dense")}</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#E07040]" /> {t("ui.map_retention")}</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-[#C04040]" /> {t("ui.map_cut")}</span>
          </div>
        )}
      </div>

      <p className="text-center text-[9px] text-[#6B7280]/40 mt-2">
        {t("ui.map_bicing_count", { count: data.bicing.length })} · {t("ui.map_traffic_issues", { count: data.trafico.vias_afectadas.length })}
        {sctRetencions > 0 && ` · ${t("ui.map_sct_issues", { count: sctRetencions })}`}
      </p>
    </div>
  );
}

function BicingMarker({ station }: { station: BicingStation }) {
  return (
    <CircleMarker
      center={[station.lat, station.lon]}
      radius={bicingRadius(station)}
      pathOptions={{
        color: bicingColor(station),
        fillColor: bicingColor(station),
        fillOpacity: 0.7,
        weight: 1,
      }}
    >
      <Popup>
        <div className="text-[12px] leading-relaxed min-w-[140px]">
          <p className="font-bold text-[#2E2E2E]">{station.name}</p>
          <p className="mt-1">🚲 {station.bikes} ({station.mechanical}m + {station.electric}e)</p>
          <p>🅿️ {station.docks} anclajes</p>
          {station.status !== "IN_SERVICE" && (
            <p className="text-[#C05050] font-semibold mt-1">Fuera de servicio</p>
          )}
        </div>
      </Popup>
    </CircleMarker>
  );
}

function TrafficMarker({ via, t }: { via: MapaVia; t: (k: string, p?: Record<string, string | number>) => string }) {
  const color = VIA_COLORS[via.estado] ?? "#6B7280";
  return (
    <CircleMarker
      center={[via.lat, via.lon]}
      radius={via.estado === "Cortado" ? 10 : via.estado === "Congestionado" ? 8 : 6}
      pathOptions={{
        color,
        fillColor: color,
        fillOpacity: 0.6,
        weight: 2,
      }}
    >
      <Popup>
        <div className="text-[12px] leading-relaxed min-w-[160px]">
          <p className="font-bold text-[#2E2E2E]">{via.via}</p>
          <p className="mt-1" style={{ color }}>
            <strong>{t(`severity.${via.estado}`)}</strong>
          </p>
          <p className="text-[#6B7280]">{t("ui.prediction_15min")}: {via.prevision}</p>
        </div>
      </Popup>
    </CircleMarker>
  );
}

const SCT_TRANSLATIONS: Record<string, Record<string, string>> = {
  es: {
    "Circulació amb retencions": "Circulación con retenciones",
    "Circulació intensa": "Circulación intensa",
    "Calçada tallada": "Calzada cortada",
    "Calçada restringida": "Calzada restringida",
    "Calçada restringida. Desviaments": "Calzada restringida. Desvíos",
    "Calçada tallada. Desviaments": "Calzada cortada. Desvíos",
    "Retenció": "Retención",
    "Obres": "Obras",
    "Cons": "Aviso",
    "Circulació": "Circulación",
    "Reforçament de ferm": "Refuerzo de firme",
    "Reasfaltat": "Reasfaltado",
    "Neteja": "Limpieza",
    "Esllavissada": "Desprendimiento",
    "Avaria": "Avería",
    "Retirada de vehicle": "Retirada de vehículo",
    "Treballs de manteniment": "Trabajos de mantenimiento",
    "Treballs de jardineria": "Trabajos de jardinería",
    "Treballs d'enllumenat": "Trabajos de alumbrado",
    "Millora de traçat": "Mejora de trazado",
    "Millora de senyalització": "Mejora de señalización",
    "Senyalització horitzontal": "Señalización horizontal",
    "Construcció de rotonda": "Construcción de rotonda",
    "Estabilització de talús": "Estabilización de talud",
    "Ampliació calçada": "Ampliación de calzada",
    "Carril BICI": "Carril bici",
    "Carril BUS": "Carril bus",
    "Despreniments": "Desprendimientos",
    "Inundacions": "Inundaciones",
    "Obres en general": "Obras en general",
    "Manteniment de ponts": "Mantenimiento de puentes",
    "Sondejos": "Sondeos",
    "Reparació de ferm": "Reparación de firme",
    "Cancel·lació carril ràpid": "Cancelación carril rápido",
    "Canalització de fibra": "Canalización de fibra",
    "Instal·lació d'espires": "Instalación de espiras",
    "Ampliació al tercer carril": "Ampliación al tercer carril",
    "Reparació de juntes de dilatació": "Reparación de juntas de dilatación",
    "Reparació de barrera de seguretat": "Reparación de barrera de seguridad",
  },
};

function translateSCT(text: string, lang: string): string {
  if (lang === "ca") return text;
  const dict = SCT_TRANSLATIONS[lang] ?? SCT_TRANSLATIONS["es"];
  return dict[text] ?? text;
}

function SCTMarker({ incident, lang }: { incident: SCTIncident; lang: string }) {
  const color = SCT_COLORS[incident.severity] ?? "#9CA3AF";
  const radius = incident.severity === "tallada" ? 10 : incident.severity === "retencio" ? 8 : 5;
  const desc = translateSCT(incident.descripcion || incident.causa, lang);
  const tipo = translateSCT(incident.tipo, lang);
  const causa = translateSCT(incident.causa, lang);
  return (
    <CircleMarker
      center={[incident.lat, incident.lon]}
      radius={radius}
      pathOptions={{
        color,
        fillColor: color,
        fillOpacity: 0.7,
        weight: 2,
      }}
    >
      <Popup>
        <div className="text-[12px] leading-relaxed min-w-[180px]">
          <p className="font-bold text-[#2E2E2E]">{incident.carretera}</p>
          <p className="mt-1" style={{ color }}>
            <strong>{desc}</strong>
          </p>
          {causa !== desc && (
            <p className="text-[#6B7280]">{causa}</p>
          )}
          {incident.hacia && (
            <p className="text-[#6B7280]">→ {incident.hacia}</p>
          )}
          <p className="text-[#9CA3AF] text-[10px] mt-1">SCT · {tipo}</p>
        </div>
      </Popup>
    </CircleMarker>
  );
}
