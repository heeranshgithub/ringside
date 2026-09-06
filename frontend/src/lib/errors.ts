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

export interface ErrorSummary {
  /** What went wrong, in the reader's terms. */
  title: string;
  /** What they can do about it, or what happens next. */
  message: string;
  /** The developer's version. Never the headline; shown folded away underneath. */
  technical: string | null;
}

const UNREACHABLE = /failed to fetch|networkerror|load failed|network request failed/i;

/**
 * Turn anything thrown at a boundary into something a person can read.
 *
 * A render crash arrives as a raw `TypeError`, and putting "Cannot read properties of undefined"
 * in front of a user tells them nothing and looks broken. The distinction that matters to them
 * is whether the service is reachable — which is usually temporary and worth retrying — or
 * whether this screen has a bug, which is not their problem to solve.
 */
export function describeError(
  error: ApiError | Error | undefined,
  fallbackTitle = "Something went wrong",
): ErrorSummary {
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return {
      title: "You are offline",
      message: "The browser has no network connection. Reconnect and retry.",
      technical: null,
    };
  }

  if (error instanceof Error) {
    if (UNREACHABLE.test(error.message)) {
      return {
        title: "Cannot reach the service",
        message:
          "The API did not respond. It may be restarting after a deploy, which usually clears within a few minutes.",
        technical: error.message,
      };
    }
    return {
      title: "This screen hit a bug",
      message: "Nothing was lost. Retrying may work; if it does not, this needs a fix.",
      technical: `${error.name}: ${error.message}`,
    };
  }

  if (error && "status" in error) {
    const { status } = error;
    if (status === "FETCH_ERROR") {
      return {
        title: "Cannot reach the service",
        message:
          "The API did not respond. It may be restarting after a deploy, which usually clears within a few minutes.",
        technical: getErrorMessage(error),
      };
    }
    if (status === "PARSING_ERROR" || status === "CUSTOM_ERROR") {
      return {
        title: "The service replied with something unreadable",
        message: "This is usually a mismatch between the app and the API. Retrying may work.",
        technical: getErrorMessage(error),
      };
    }
    if (typeof status === "number" && status >= 500) {
      return {
        title: "The service is having trouble",
        message: "The request reached the API and it failed to handle it. Retrying may work.",
        technical: getErrorMessage(error),
      };
    }
    // 4xx carries our own envelope, which is already written for a person to read.
    return { title: fallbackTitle, message: getErrorMessage(error), technical: null };
  }

  return { title: fallbackTitle, message: getErrorMessage(error), technical: null };
}
