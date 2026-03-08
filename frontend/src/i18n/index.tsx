import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import ca from "./ca.json";
import es from "./es.json";

export type Lang = "ca" | "es";
type Dict = Record<string, string>;

const dicts: Record<Lang, Dict> = { ca, es };

interface I18n {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
  /** Resolve a backend translatable object { key, params? } */
  tr: (obj: { key: string; params?: Record<string, string | number> } | string) => string;
}

const I18nCtx = createContext<I18n>(null!);

const LS_KEY = "sempretard_lang";

function getInitialLang(): Lang {
  try {
    const stored = localStorage.getItem(LS_KEY);
    if (stored === "ca" || stored === "es") return stored;
  } catch {}
  const nav = navigator.language.toLowerCase();
  return nav.startsWith("ca") ? "ca" : "es";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(getInitialLang);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try { localStorage.setItem(LS_KEY, l); } catch {}
  }, []);

  const t = useCallback((key: string, params?: Record<string, string | number>): string => {
    let text = dicts[lang][key] ?? dicts["es"][key] ?? key;
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        text = text.split(`{{${k}}}`).join(String(v));
      }
    }
    return text;
  }, [lang]);

  const tr = useCallback((obj: { key: string; params?: Record<string, string | number> } | string): string => {
    if (typeof obj === "string") return obj;
    return t(obj.key, obj.params);
  }, [t]);

  return <I18nCtx.Provider value={{ lang, setLang, t, tr }}>{children}</I18nCtx.Provider>;
}

export const useI18n = () => useContext(I18nCtx);
