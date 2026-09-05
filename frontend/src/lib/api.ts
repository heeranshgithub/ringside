import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

import { env } from "@/lib/env";
import { getAccessCode } from "@/lib/access-code";
import { getSessionId } from "@/lib/session";

export const TAG_TYPES = [
  "Job",
  "Agent",
  "Candidate",
  "Call",
  "Dashboard",
  "Config",
  "DialTarget",
] as const;
export type TagType = (typeof TAG_TYPES)[number];

/** The most recent x-request-id, surfaced in error UI for log correlation. */
let lastRequestId: string | null = null;
export const getLastRequestId = () => lastRequestId;

const fetchFn: typeof fetch = async (input, init) => {
  const res = await fetch(input, init);
  const rid = res.headers.get("x-request-id");
  if (rid) lastRequestId = rid;
  return res;
};

export const api = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({
    baseUrl: `${env.NEXT_PUBLIC_API_BASE_URL}/api`,
    fetchFn,
    prepareHeaders: (headers) => {
      const code = getAccessCode();
      if (code) headers.set("x-access-code", code);
      const session = getSessionId();
      if (session) headers.set("x-session-id", session);
      return headers;
    },
  }),
  tagTypes: TAG_TYPES,
  endpoints: () => ({}),
});
