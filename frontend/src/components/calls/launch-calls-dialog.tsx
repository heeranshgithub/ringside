"use client";

import { PhoneOutgoing, ShieldCheck, ShieldOff } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Field } from "@/components/field";
import { useGetAgentsQuery } from "@/features/agents/api";
import { useGetConfigQuery, useLaunchCallsMutation } from "@/features/calls/api";
import { getErrorMessage } from "@/lib/errors";
import type { Candidate } from "@/types/candidate";
import type { LaunchCallsResult } from "@/types/call";

const WINDOWS = {
  now: {
    label: "Call now (any time)",
    allowedDays: ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
    earliestCallTime: "00:00",
    lastCallTime: "23:59",
  },
  business: {
    label: "Business hours (Mon–Sat, 09:00–20:00 IST)",
    allowedDays: ["MON", "TUE", "WED", "THU", "FRI", "SAT"],
    earliestCallTime: "09:00",
    lastCallTime: "20:00",
  },
} as const;

type WindowKey = keyof typeof WINDOWS;

export function LaunchCallsDialog({
  open,
  onOpenChange,
  jobId,
  defaultAgentId,
  candidates,
  onLaunched,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  jobId: string;
  defaultAgentId: string | null;
  candidates: Candidate[];
  onLaunched?: (result: LaunchCallsResult) => void;
}) {
  const { data: config } = useGetConfigQuery();
  const { data: agents } = useGetAgentsQuery();
  const [launch, { isLoading }] = useLaunchCallsMutation();
  const [agentId, setAgentId] = useState<string | null>(defaultAgentId);
  const [win, setWin] = useState<WindowKey>("now");
  const [retries, setRetries] = useState("1");

  const effectiveAgent = agentId ?? defaultAgentId;
  const realDial = config && !config.safeDialMode;
  const clearedCount = candidates.filter((c) => c.allowRealDial && c.phone).length;

  const submit = async () => {
    if (!effectiveAgent) return;
    const w = WINDOWS[win];
    try {
      const res = await launch({
        jobId,
        candidateIds: candidates.map((c) => c.id),
        agentId: effectiveAgent,
        guardrails: {
          allowedDays: [...w.allowedDays],
          earliestCallTime: w.earliestCallTime,
          lastCallTime: w.lastCallTime,
        },
        retry: { maxRetryCount: Number(retries), retryIntervalHours: 3 },
      }).unwrap();
      if (res.calls.length)
        toast.success(`Queued ${res.calls.length} call${res.calls.length === 1 ? "" : "s"}`);
      if (res.skipped.length)
        toast.warning(`${res.skipped.length} skipped: ${res.skipped[0]?.reason ?? ""}`);
      onLaunched?.(res);
      onOpenChange(false);
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <PhoneOutgoing className="size-4" />
            Call {candidates.length} candidate{candidates.length === 1 ? "" : "s"}
          </DialogTitle>
          <DialogDescription>
            The voice agent dials each candidate, asks the screening questions and posts structured
            answers back here.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div
            className={
              realDial
                ? "border-destructive/30 bg-destructive/10 text-destructive flex items-start gap-2 rounded-lg border p-3 text-xs"
                : "flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-800 dark:text-emerald-200"
            }
          >
            {realDial ? (
              <ShieldOff className="mt-0.5 size-3.5 shrink-0" />
            ) : (
              <ShieldCheck className="mt-0.5 size-3.5 shrink-0" />
            )}
            <div>
              {realDial ? (
                <>
                  <span className="font-medium">Real dialling is enabled.</span> {clearedCount} of{" "}
                  {candidates.length} selected candidates are cleared and will be called on their
                  own number. The rest go to the test number{" "}
                  {config?.testPhoneNumbersMasked[0] ?? "(none configured)"}.
                </>
              ) : (
                <>
                  <span className="font-medium">Safe dial is on.</span> Every call is routed to{" "}
                  {config?.testPhoneNumbersMasked[0] ?? "the test number (none configured yet)"};
                  the candidate&apos;s own number is never dialled. The agent still uses the
                  candidate&apos;s name and role.
                </>
              )}
            </div>
          </div>

          <Field label="Voice agent" htmlFor="launch-agent">
            <Select value={effectiveAgent ?? ""} onValueChange={(v) => setAgentId(v)}>
              <SelectTrigger id="launch-agent" className="w-full">
                <SelectValue placeholder="Choose an agent" />
              </SelectTrigger>
              <SelectContent>
                {(agents ?? []).map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {a.name} · {a.voicePersona}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field
            label="Calling window"
            htmlFor="launch-window"
            hint="Outside the window Hunar keeps the call scheduled."
          >
            <Select value={win} onValueChange={(v) => setWin((v as WindowKey | null) ?? "now")}>
              <SelectTrigger id="launch-window" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(Object.keys(WINDOWS) as WindowKey[]).map((k) => (
                  <SelectItem key={k} value={k}>
                    {WINDOWS[k].label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field
            label="Retries if not connected"
            htmlFor="launch-retries"
            hint="Retried every 3 hours."
          >
            <Select value={retries} onValueChange={(v) => setRetries(v ?? "1")}>
              <SelectTrigger id="launch-retries" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["0", "1", "2", "3"].map((n) => (
                  <SelectItem key={n} value={n}>
                    {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={isLoading || !effectiveAgent || candidates.length === 0}
          >
            <PhoneOutgoing data-icon="inline-start" />
            {isLoading ? "Queuing…" : "Start calls"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
