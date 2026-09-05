"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { getAccessCode } from "@/lib/access-code";
import { env } from "@/lib/env";
import { useAppDispatch } from "@/store/hooks";

/**
 * Live updates over server-sent events.
 *
 * Read with `fetch` rather than `EventSource`, because EventSource cannot send headers and
 * this deployment may be gated by `X-Access-Code`. The cost is that reconnection is ours to
 * handle, which the backoff below does.
 *
 * The stream is a hint, never data: an event says which call moved, and we invalidate the
 * matching RTK Query tags so the normal API refetches it. A missed frame therefore costs a
 * few seconds of staleness rather than a wrong screen, and the slow poll is still the net.
 */
interface CallUpdated {
  callId: string;
  jobId?: string | null;
  candidateId?: string | null;
  status?: string;
  changed?: string[];
}

const MAX_BACKOFF_MS = 30_000;

export function useLiveEvents(): boolean {
  const dispatch = useAppDispatch();
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    let stopped = false;
    let attempt = 0;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;

    const onFrame = (raw: string) => {
      // Comments (": ping") are keep-alives and carry nothing.
      if (!raw || raw.startsWith(":")) return;
      let name = "message";
      const payload: string[] = [];
      for (const line of raw.split("\n")) {
        if (line.startsWith("event:")) name = line.slice(6).trim();
        else if (line.startsWith("data:")) payload.push(line.slice(5).trim());
      }
      if (name !== "call.updated" || payload.length === 0) return;

      let data: CallUpdated;
      try {
        data = JSON.parse(payload.join("\n")) as CallUpdated;
      } catch {
        return;
      }

      dispatch(
        api.util.invalidateTags([
          { type: "Call", id: data.callId },
          { type: "Call", id: "LIST" },
          { type: "Candidate", id: "LIST" },
          "Dashboard",
          ...(data.jobId ? [{ type: "Job" as const, id: data.jobId }] : []),
        ]),
      );
    };

    const run = async () => {
      while (!stopped) {
        try {
          const headers: Record<string, string> = { Accept: "text/event-stream" };
          const code = getAccessCode();
          if (code) headers["x-access-code"] = code;

          const res = await fetch(`${env.NEXT_PUBLIC_API_BASE_URL}/api/events`, {
            headers,
            signal: controller.signal,
            cache: "no-store",
          });
          if (!res.ok || !res.body) throw new Error(`stream failed: ${res.status}`);

          setConnected(true);
          attempt = 0;

          const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
          let buffer = "";
          for (;;) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += value;
            let split = buffer.indexOf("\n\n");
            while (split !== -1) {
              onFrame(buffer.slice(0, split));
              buffer = buffer.slice(split + 2);
              split = buffer.indexOf("\n\n");
            }
          }
        } catch {
          // Any failure, including a dropped connection, falls through to the backoff.
        }

        setConnected(false);
        if (stopped) return;
        attempt += 1;
        const wait = Math.min(500 * 2 ** attempt, MAX_BACKOFF_MS);
        await new Promise<void>((resolve) => {
          retryTimer = setTimeout(resolve, wait);
        });
      }
    };

    void run();
    return () => {
      stopped = true;
      controller.abort();
      if (retryTimer) clearTimeout(retryTimer);
    };
  }, [dispatch]);

  return connected;
}
