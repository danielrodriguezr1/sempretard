import { useState, useEffect, useCallback, useRef } from "react";

const LS_KEY = "sempretard_geo_enabled";
const BCN_CENTER = { lat: 41.3874, lon: 2.1686 };

export interface GeoPosition {
  lat: number;
  lon: number;
  accuracy: number;
  timestamp: number;
}

export interface GeoState {
  position: GeoPosition | null;
  enabled: boolean;
  loading: boolean;
  error: string | null;
  /** User's position or BCN center as fallback */
  effectiveCenter: { lat: number; lon: number };
  requestPermission: () => Promise<void>;
  disable: () => void;
}

function isNative(): boolean {
  return !!(window as any).Capacitor?.isNativePlatform();
}

async function getNativePosition(): Promise<GeoPosition> {
  const { Geolocation } = await import("@capacitor/geolocation");
  const pos = await Geolocation.getCurrentPosition({ enableHighAccuracy: true });
  return {
    lat: pos.coords.latitude,
    lon: pos.coords.longitude,
    accuracy: pos.coords.accuracy,
    timestamp: pos.timestamp,
  };
}

function getBrowserPosition(): Promise<GeoPosition> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new Error("Geolocation not supported"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        resolve({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          timestamp: pos.timestamp,
        }),
      (err) => reject(err),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
    );
  });
}

export function useGeolocation(): GeoState {
  const [enabled, setEnabled] = useState(() => {
    try {
      return localStorage.getItem(LS_KEY) === "true";
    } catch {
      return false;
    }
  });
  const [position, setPosition] = useState<GeoPosition | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const watchId = useRef<number | null>(null);

  const fetchPosition = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const pos = isNative() ? await getNativePosition() : await getBrowserPosition();
      setPosition(pos);
    } catch (e: any) {
      setError(e?.message ?? "Error de geolocalización");
    } finally {
      setLoading(false);
    }
  }, []);

  const requestPermission = useCallback(async () => {
    if (isNative()) {
      try {
        const { Geolocation } = await import("@capacitor/geolocation");
        const perms = await Geolocation.requestPermissions();
        if (perms.location === "denied") {
          setError("Permiso denegado");
          return;
        }
      } catch {}
    }

    setEnabled(true);
    try {
      localStorage.setItem(LS_KEY, "true");
    } catch {}
    await fetchPosition();
  }, [fetchPosition]);

  const disable = useCallback(() => {
    setEnabled(false);
    setPosition(null);
    try {
      localStorage.setItem(LS_KEY, "false");
    } catch {}
    if (watchId.current !== null && !isNative()) {
      navigator.geolocation.clearWatch(watchId.current);
      watchId.current = null;
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;

    fetchPosition();

    if (!isNative() && "geolocation" in navigator) {
      watchId.current = navigator.geolocation.watchPosition(
        (pos) =>
          setPosition({
            lat: pos.coords.latitude,
            lon: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
            timestamp: pos.timestamp,
          }),
        () => {},
        { enableHighAccuracy: false, maximumAge: 120000 },
      );
    }

    const interval = setInterval(fetchPosition, 5 * 60 * 1000);
    return () => {
      clearInterval(interval);
      if (watchId.current !== null && !isNative()) {
        navigator.geolocation.clearWatch(watchId.current);
        watchId.current = null;
      }
    };
  }, [enabled, fetchPosition]);

  return {
    position,
    enabled,
    loading,
    error,
    effectiveCenter: position
      ? { lat: position.lat, lon: position.lon }
      : BCN_CENTER,
    requestPermission,
    disable,
  };
}
