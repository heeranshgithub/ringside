"use client";

import { createContext, useContext } from "react";

import { useLiveEvents } from "@/features/live/use-live-events";

const LiveContext = createContext(false);

/** Opens one event stream for the whole app and shares its connection state. */
export function LiveProvider({ children }: { children: React.ReactNode }) {
  const connected = useLiveEvents();
  return <LiveContext.Provider value={connected}>{children}</LiveContext.Provider>;
}

export const useLive = () => useContext(LiveContext);

/**
 * How often a query should refetch on its own.
 *
 * While the stream is up, updates arrive by push and polling is only a safety net for a
 * frame we never received, so it drops to a minute. When the stream is down it is the
 * only mechanism left and goes back to its normal pace.
 */
export function useLiveInterval(fallbackMs: number): number {
  return useLive() ? 60_000 : fallbackMs;
}
