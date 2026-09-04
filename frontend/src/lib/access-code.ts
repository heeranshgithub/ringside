const KEY = "ringside.accessCode";

export function getAccessCode(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function setAccessCode(code: string | null): void {
  try {
    if (code) window.localStorage.setItem(KEY, code);
    else window.localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable */
  }
}
