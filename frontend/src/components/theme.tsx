"use client";

import { createContext, useCallback, useContext, useEffect, useSyncExternalStore } from "react";

export type ThemeChoice = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

const STORAGE_KEY = "ringside.theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

/**
 * Runs before first paint so the right theme is on <html> and there is no flash.
 * Kept in sync with the store below by STORAGE_KEY.
 */
export const themeScript = `(function(){try{
var c=localStorage.getItem(${JSON.stringify(STORAGE_KEY)});
var d=c==="dark"||((c===null||c==="system")&&window.matchMedia(${JSON.stringify(DARK_QUERY)}).matches);
document.documentElement.classList.toggle("dark",d);
document.documentElement.style.colorScheme=d?"dark":"light";
}catch(e){}})();`;

/* --- the choice is external state (localStorage + the OS), not React state --- */

const listeners = new Set<() => void>();
const notify = () => listeners.forEach((l) => l());

function subscribe(onChange: () => void): () => void {
  listeners.add(onChange);
  const mq = window.matchMedia(DARK_QUERY);
  mq.addEventListener("change", onChange);
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    mq.removeEventListener("change", onChange);
    window.removeEventListener("storage", onChange);
  };
}

function readChoice(): ThemeChoice {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") return stored;
  } catch {
    /* storage unavailable */
  }
  return "system";
}

const readSystemDark = () => window.matchMedia(DARK_QUERY).matches;

interface ThemeContextValue {
  choice: ThemeChoice;
  resolved: ResolvedTheme;
  setChoice: (next: ThemeChoice) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const choice = useSyncExternalStore<ThemeChoice>(subscribe, readChoice, () => "system");
  const systemDark = useSyncExternalStore<boolean>(subscribe, readSystemDark, () => false);
  const resolved: ResolvedTheme =
    choice === "dark" || (choice === "system" && systemDark) ? "dark" : "light";

  // The only side effect: keep <html> in step with the resolved theme.
  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolved === "dark");
    document.documentElement.style.colorScheme = resolved;
  }, [resolved]);

  const setChoice = useCallback((next: ThemeChoice) => {
    try {
      if (next === "system") window.localStorage.removeItem(STORAGE_KEY);
      else window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* storage unavailable */
    }
    notify();
  }, []);

  return (
    <ThemeContext.Provider value={{ choice, resolved, setChoice }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used inside <ThemeProvider>");
  return ctx;
}
