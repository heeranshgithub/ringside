const KEY = "ringside.sessionId";

/**
 * A random per-browser id, sent as `X-Session-Id`.
 *
 * It scopes a verified dial target to one visitor so two people demoing at once do not
 * ring each other's phones. It is not an identity claim and the backend never treats it as
 * one: the limits that actually matter are counted per phone number, which minting a fresh
 * id cannot reset.
 */
export function getSessionId(): string {
  if (typeof window === "undefined") return "";
  try {
    const existing = window.localStorage.getItem(KEY);
    if (existing && existing.length >= 12) return existing;
    const fresh = crypto.randomUUID();
    window.localStorage.setItem(KEY, fresh);
    return fresh;
  } catch {
    // Private mode or blocked storage: a per-tab id still scopes this visit correctly.
    return "";
  }
}
