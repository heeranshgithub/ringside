import type { FetchBaseQueryError } from "@reduxjs/toolkit/query";
import type { SerializedError } from "@reduxjs/toolkit";

import type { ApiErrorEnvelope } from "@/types/common";

export type ApiError = FetchBaseQueryError | SerializedError | undefined;

function isEnvelope(data: unknown): data is ApiErrorEnvelope {
  return (
    typeof data === "object" &&
    data !== null &&
    "error" in data &&
    typeof (data as { error: unknown }).error === "object"
  );
}

export function getErrorCode(error: ApiError): string | null {
  if (!error || !("data" in error)) return null;
  return isEnvelope(error.data) ? error.data.error.code : null;
}

export function getErrorMessage(error: ApiError, fallback = "Something went wrong"): string {
  if (!error) return fallback;
  if ("status" in error) {
    if (isEnvelope(error.data)) {
      const { message, details } = error.data.error;
      const rid = details?.requestId ? ` (request ${details.requestId})` : "";
      return `${message}${rid}`;
    }
    if (error.status === "FETCH_ERROR") return "Cannot reach the API. Is the backend running?";
    if (error.status === "PARSING_ERROR") return "The API returned an unreadable response.";
    return `${fallback} (HTTP ${String(error.status)})`;
  }
  return error.message ?? fallback;
}
