"use client";

import Link from "next/link";
import { AlertTriangle, KeyRound } from "lucide-react";

import { useGetConfigQuery } from "@/features/calls/api";
import { getErrorCode, type ApiError } from "@/lib/errors";
import type { Capability } from "@/types/common";
import { cn } from "@/lib/utils";

/**
 * Missing credentials are a first-class state, not a surprise.
 *
 * The backend refuses rather than simulating when a key is absent, so the job of these
 * components is to say which key and where to put it, instead of letting the user meet a
 * bare 503 or, worse, a convincing fake.
 */

export function useCapability(key: string): Capability | undefined {
  const { data } = useGetConfigQuery();
  return data?.capabilities.find((c) => c.key === key);
}

/** Inline banner for a feature the current screen depends on. */
export function CapabilityNotice({
  capability,
  className,
}: {
  capability: string;
  className?: string;
}) {
  const cap = useCapability(capability);
  if (!cap || cap.state === "ok") return null;

  const missing = cap.state === "missing";
  return (
    <div
      role="status"
      className={cn(
        "flex items-start gap-3 rounded-xl border p-3.5 text-[13px]",
        missing ? "border-fail-line bg-fail-bg" : "border-live-line bg-live-bg",
        className,
      )}
    >
      {missing ? (
        <KeyRound className="text-fail mt-0.5 size-4 shrink-0" />
      ) : (
        <AlertTriangle className="text-live-ink mt-0.5 size-4 shrink-0" />
      )}
      <div className="min-w-0">
        <p className={cn("font-medium", missing ? "text-fail" : "text-live-ink")}>
          {missing ? `${cap.label} is not configured` : `${cap.label} is running degraded`}
        </p>
        <p className="text-muted-foreground mt-0.5">{cap.detail}</p>
        {cap.envVar && (
          <p className="text-muted-foreground mt-1.5">
            Set <code className="text-foreground font-mono text-xs">{cap.envVar}</code> in{" "}
            <code className="font-mono text-xs">backend/.env</code> and restart the backend.{" "}
            <Link href="/settings" className="text-tint underline-offset-2 hover:underline">
              See all integrations
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}

/**
 * Turns the backend's refusal into the same message, for actions that fail at click time
 * rather than on page load.
 */
export function CredentialError({ error }: { error: ApiError }) {
  const { data } = useGetConfigQuery();
  if (getErrorCode(error) !== "credential_missing") return null;
  const missing = data?.capabilities.filter((c) => c.state === "missing") ?? [];
  return (
    <div className="border-fail-line bg-fail-bg flex items-start gap-3 rounded-xl border p-3.5 text-[13px]">
      <KeyRound className="text-fail mt-0.5 size-4 shrink-0" />
      <div>
        <p className="text-fail font-medium">That needs a key this deployment does not have</p>
        <p className="text-muted-foreground mt-0.5">
          {missing.length
            ? `Not configured: ${missing.map((c) => c.envVar ?? c.label).join(", ")}.`
            : "Check the backend environment."}
        </p>
      </div>
    </div>
  );
}
