"use client";

import { PhoneOutgoing, ShieldCheck, ShieldOff } from "lucide-react";
import { useMemo, useState } from "react";
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
import { DialTargetCard } from "@/components/dial/dial-target-card";
import { Field } from "@/components/field";
import { useGetAgentsQuery } from "@/features/agents/api";
import { useGetConfigQuery, useLaunchCallsMutation } from "@/features/calls/api";
import { useGetDialTargetQuery } from "@/features/dial/api";
import { getErrorMessage } from "@/lib/errors";
import { selectItems } from "@/lib/select-items";
import type { Candidate } from "@/types/candidate";
import type { LaunchCallsResult } from "@/types/call";

// Hunar rejects any window outside 08:00-21:00 with a 400, so "any time" was never on
// offer. These are the real choices; the widest one is the platform maximum.
const WINDOWS = {
  now: {
    label: "As soon as possible (08:00–21:00 IST, any day)",
    allowedDays: ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
    earliestCallTime: "08:00",
    lastCallTime: "21:00",
  },
  business: {
    label: "Business hours (Mon–Sat, 09:00–20:00 IST)",
    allowedDays: ["MON", "TUE", "WED", "THU", "FRI", "SAT"],
    earliestCallTime: "09:00",
    lastCallTime: "20:00",
  },
} as const;

type WindowKey = keyof typeof WINDOWS;

const agentLabel = (a: { name: string; voicePersona: string }) => `${a.name} · ${a.voicePersona}`;

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
  const { data: dialTarget } = useGetDialTargetQuery();
  const { data: agents } = useGetAgentsQuery();
  const [launch, { isLoading }] = useLaunchCallsMutation();
  const [agentId, setAgentId] = useState<string | null>(defaultAgentId);
  const [win, setWin] = useState<WindowKey>("now");
  const [retries, setRetries] = useState("1");

  const agentItems = useMemo(() => selectItems(agents ?? [], (a) => a.id, agentLabel), [agents]);
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
      <DialogContent className="sm:max-w-xl">
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
                : "border-done-line bg-done-bg text-done flex items-start gap-2 rounded-lg border p-3 text-xs"
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
                  own number. The rest go to{" "}
                  {dialTarget?.verified
                    ? `your verified number ${dialTarget.phonePretty}`
                    : "nobody, because no number has been verified in this browser yet"}
                  .
                </>
              ) : (
                <>
                  <span className="font-medium">Safe dial is on.</span> Every call is routed to{" "}
                  {dialTarget?.verified ? (
                    <span className="font-medium">
                      your verified number {dialTarget.phonePretty}
                    </span>
                  ) : (
                    "no number yet, so every call will be skipped — verify yours below"
                  )}
                  ; the candidate&apos;s own number is never dialled. The agent still uses the
                  candidate&apos;s name and role.
                </>
              )}
            </div>
          </div>

          <DialTargetCard />

          <Field label="Voice agent" htmlFor="launch-agent">
            <Select
              value={effectiveAgent ?? ""}
              onValueChange={(v) => setAgentId(v)}
              items={agentItems}
            >
              <SelectTrigger id="launch-agent" className="w-full">
                <SelectValue placeholder="Choose an agent" />
              </SelectTrigger>
              <SelectContent>
                {(agents ?? []).map((a) => (
                  <SelectItem key={a.id} value={a.id}>
                    {agentLabel(a)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field
            label="Calling window"
            htmlFor="launch-window"
            hint="Hunar allows 08:00–21:00 only. Outside the window it keeps the call scheduled."
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
