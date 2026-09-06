import { useSyncExternalStore } from "react";

/**
 * The shared access code lives in localStorage, and two screens write it: the gate and
 * Settings. That makes it external state, not component state.
 *
 * It used to be a plain getter, so the gate held its own copy. Clearing the code from
 * Settings then re-locked a gate that still had the old value typed in and still believed
 * it had been submitted, so it accused the visitor of a wrong code before they had touched
 * anything. Subscribing fixes that at the root: every reader sees the same value change.
 */

const KEY = "ringside.accessCode";

const listeners = new Set<() => void>();

function read(): string | null {
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function getAccessCode(): string | null {
  if (typeof window === "undefined") return null;
  return read();
}

export function setAccessCode(code: string | null): void {
  try {
    if (code) window.localStorage.setItem(KEY, code);
    else window.localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable */
  }
  listeners.forEach((notify) => notify());
}

function subscribe(onChange: () => void): () => void {
  listeners.add(onChange);
  // Another tab clearing the code should re-lock this one too.
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

/** The code currently saved in this browser, or null. Re-renders when it changes. */
export function useAccessCode(): string | null {
  return useSyncExternalStore(subscribe, read, () => null);
}
