import { useState, useEffect, useCallback, useRef } from "react";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const POLL_MS = 3 * 60 * 1000;
const LS_KEY = "sempretard_notif_enabled";
const LS_SEEN_KEY = "sempretard_notif_seen";

interface Alert {
  id: string;
  tipo: string;
  modo: string | null;
  titulo: { key: string; params?: Record<string, string | number> } | string;
  mensaje: { key: string; params?: Record<string, string | number> } | string;
  score: number | null;
  timestamp: string;
  prioridad: string;
}

interface AlertsResponse {
  alerts: Alert[];
  total: number;
  hay_criticos: boolean;
  timestamp: string;
}

function isNative(): boolean {
  return !!(window as any).Capacitor?.isNativePlatform();
}

function getSeenIds(): Set<string> {
  try {
    const raw = localStorage.getItem(LS_SEEN_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function markSeen(id: string) {
  const seen = getSeenIds();
  seen.add(id);
  const arr = [...seen].slice(-100);
  try { localStorage.setItem(LS_SEEN_KEY, JSON.stringify(arr)); } catch {}
}

async function sendLocalNotification(alert: Alert, tr: (obj: any) => string) {
  if (isNative()) {
    try {
      const { LocalNotifications } = await import("@capacitor/local-notifications");
      const perms = await LocalNotifications.requestPermissions();
      if (perms.display !== "granted") return;

      await LocalNotifications.schedule({
        notifications: [{
          title: tr(alert.titulo),
          body: tr(alert.mensaje),
          id: Math.abs(hashCode(alert.id)),
          schedule: { at: new Date() },
          smallIcon: "ic_notification",
          largeIcon: "ic_notification",
        }],
      });
    } catch (e) {
      console.warn("LocalNotification failed:", e);
    }
  } else if ("Notification" in window && Notification.permission === "granted") {
    new Notification(tr(alert.titulo), { body: tr(alert.mensaje) });
  }
}

function hashCode(s: string): number {
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = ((hash << 5) - hash + s.charCodeAt(i)) | 0;
  }
  return hash;
}

export function useNotifications(tr: (obj: any) => string) {
  const [enabled, setEnabledState] = useState(() => {
    try { return localStorage.getItem(LS_KEY) === "true"; } catch { return false; }
  });
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [hasCritical, setHasCritical] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchAlerts = useCallback(async () => {
    try {
      const res = await fetch(`${BASE}/api/alertas`);
      if (!res.ok) return;
      const data: AlertsResponse = await res.json();
      setAlerts(data.alerts);
      setHasCritical(data.hay_criticos);

      if (enabled) {
        const seen = getSeenIds();
        for (const alert of data.alerts) {
          if (alert.prioridad !== "baja" && !seen.has(alert.id)) {
            await sendLocalNotification(alert, tr);
            markSeen(alert.id);
          }
        }
      }
    } catch {}
  }, [enabled, tr]);

  const setEnabled = useCallback(async (val: boolean) => {
    if (val) {
      if (!isNative() && "Notification" in window) {
        const perm = await Notification.requestPermission();
        if (perm !== "granted") return;
      }
      if (isNative()) {
        try {
          const { LocalNotifications } = await import("@capacitor/local-notifications");
          const perms = await LocalNotifications.requestPermissions();
          if (perms.display !== "granted") return;
        } catch {}
      }
    }
    setEnabledState(val);
    try { localStorage.setItem(LS_KEY, String(val)); } catch {}
  }, []);

  useEffect(() => {
    fetchAlerts();
    intervalRef.current = setInterval(fetchAlerts, POLL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchAlerts]);

  return { enabled, setEnabled, alerts, hasCritical };
}
