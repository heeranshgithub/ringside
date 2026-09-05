"use client";

import { FileAudio, RefreshCw, ScrollText, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { ScorePill, StatusBadge } from "@/components/status-badge";
import { ErrorState } from "@/components/states";
import {
  useAssessCallMutation,
  useGetCallQuery,
  useGetConfigQuery,
  useSyncCallMutation,
  useTranscribeCallMutation,
} from "@/features/calls/api";
import { useLiveInterval } from "@/features/live/live-provider";
import { getErrorMessage } from "@/lib/errors";
import {
  formatDateTime,
  formatDuration,
  formatResultValue,
  humanizeKey,
  maskPhone,
  titleCase,
} from "@/lib/format";
import type { Call } from "@/types/call";

function KV({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <div className="text-muted-foreground text-[11px] tracking-wide uppercase">{label}</div>
      <div className="text-sm">{children}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}

export function CallDetailBody({ call }: { call: Call }) {
  const { data: config } = useGetConfigQuery();
  const [sync, syncState] = useSyncCallMutation();
  const [assess, assessState] = useAssessCallMutation();
  const [transcribe, transcribeState] = useTranscribeCallMutation();

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toast.success(ok);
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  };

  const resultEntries = Object.entries(call.result ?? {});
  const terminal = ["COMPLETED", "FAILED", "CANCELLED"].includes(call.lifecycleStatus);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={call.status} />
        <StatusBadge status={call.engagementStatus} />
        {call.safeDial && (
          <span className="rounded-full bg-emerald-500/10 px-2 text-xs text-emerald-700 dark:text-emerald-300">
            safe dial
          </span>
        )}
        <div className="ml-auto flex gap-1.5">
          <Button
            size="sm"
            variant="outline"
            disabled={syncState.isLoading}
            onClick={() => run(() => sync(call.id).unwrap(), "Synced with Hunar")}
          >
            <RefreshCw
              data-icon="inline-start"
              className={syncState.isLoading ? "animate-spin" : ""}
            />
            Sync
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <KV label="Dialed">{maskPhone(call.dialedNumber)}</KV>
        <KV label="Target">{call.targetNumber ? maskPhone(call.targetNumber) : "none on file"}</KV>
        <KV label="Answered by">{titleCase(call.answeredBy)}</KV>
        <KV label="Duration">{formatDuration(call.durationSeconds)}</KV>
        <KV label="Candidate spoke">{formatDuration(call.userSpeechDuration)}</KV>
        <KV label="Ended by">{titleCase(call.callEndedBy)}</KV>
        <KV label="Started">{formatDateTime(call.startedAt)}</KV>
        <KV label="Retries left">{call.retriesLeft ?? "—"}</KV>
        <KV label="Next retry">{formatDateTime(call.nextRetryScheduledAt)}</KV>
      </div>

      {call.recordingUrl && (
        <Section title="Recording">
          <audio controls preload="none" src={call.recordingUrl} className="w-full" />
        </Section>
      )}

      <Separator />

      <Section title="Assessment">
        {call.assessment ? (
          <div className="space-y-2 rounded-lg border p-3">
            <div className="flex items-center gap-2">
              <ScorePill score={call.assessment.fitScore} />
              <StatusBadge status={call.assessment.recommendation} />
              <span className="text-muted-foreground ml-auto text-[11px]">
                {call.assessment.llmUsed ? "LLM" : "rule-based"}
              </span>
            </div>
            <p className="text-sm">{call.assessment.headline}</p>
            {call.assessment.strengths.length > 0 && (
              <ul className="text-muted-foreground list-disc pl-4 text-xs">
                {call.assessment.strengths.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            )}
            {call.assessment.concerns.length > 0 && (
              <ul className="list-disc pl-4 text-xs text-amber-700 dark:text-amber-300">
                {call.assessment.concerns.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            )}
            {call.assessment.nextStep && (
              <p className="text-xs">
                <span className="font-medium">Next step:</span> {call.assessment.nextStep}
              </p>
            )}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm">
            {terminal ? "No assessment yet." : "Available once the call completes."}
          </p>
        )}
        <Button
          size="sm"
          variant="outline"
          disabled={assessState.isLoading || resultEntries.length === 0}
          onClick={() => run(() => assess(call.id).unwrap(), "Assessment updated")}
        >
          <Sparkles data-icon="inline-start" />
          {call.assessment ? "Re-assess" : "Assess"}
        </Button>
      </Section>

      <Section title="Structured answers">
        {resultEntries.length === 0 ? (
          <p className="text-muted-foreground text-sm">The agent has not produced a result yet.</p>
        ) : (
          <dl className="divide-y rounded-lg border">
            {resultEntries.map(([k, v]) => (
              <div key={k} className="grid grid-cols-[minmax(0,40%)_1fr] gap-3 px-3 py-2 text-sm">
                <dt className="text-muted-foreground">{humanizeKey(k)}</dt>
                <dd className="break-words">{formatResultValue(v)}</dd>
              </div>
            ))}
          </dl>
        )}
      </Section>

      <Section title="Transcript">
        {call.transcript ? (
          <div className="max-h-72 space-y-2 overflow-y-auto rounded-lg border p-3 text-sm">
            {call.transcript.turns.length > 0
              ? call.transcript.turns.map((t, i) => (
                  <p key={i}>
                    <span className="text-muted-foreground mr-1.5 text-xs uppercase">
                      {t.speaker}
                    </span>
                    {t.text}
                  </p>
                ))
              : call.transcript.text}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm">
            {config?.llmEnabled
              ? "Not transcribed yet. Transcription sends the recording to the configured audio model."
              : "Transcription needs an OpenRouter key on the backend."}
          </p>
        )}
        <Button
          size="sm"
          variant="outline"
          disabled={!call.recordingUrl || !config?.llmEnabled || transcribeState.isLoading}
          onClick={() => run(() => transcribe(call.id).unwrap(), "Transcript ready")}
        >
          <ScrollText
            data-icon="inline-start"
            className={transcribeState.isLoading ? "animate-pulse" : ""}
          />
          {call.transcript ? "Re-transcribe" : "Transcribe"}
        </Button>
      </Section>

      <Section title="Timeline">
        <ol className="space-y-1.5 text-xs">
          {call.events.map((e, i) => (
            <li key={i} className="flex items-center gap-2">
              <span className="text-muted-foreground w-28 shrink-0 tabular-nums">
                {formatDateTime(e.at)}
              </span>
              <span className="font-medium">{titleCase(e.kind)}</span>
              {e.status && <StatusBadge status={e.status} />}
              <span className="text-muted-foreground ml-auto">{e.source}</span>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="Variables sent to the agent">
        <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
          {Object.entries(call.customData).map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-muted-foreground font-mono">{`{${k}}`}</dt>
              <dd className="truncate">{v || "—"}</dd>
            </div>
          ))}
        </dl>
        <p className="text-muted-foreground font-mono text-[11px]">hunar call {call.hunarCallId}</p>
      </Section>
    </div>
  );
}

export function CallDetailSheet({
  callId,
  onClose,
}: {
  callId: string | null;
  onClose: () => void;
}) {
  const open = callId !== null;
  const detailPoll = useLiveInterval(8000);
  const { data, error, isLoading, refetch } = useGetCallQuery(callId ?? "", {
    skip: !callId,
    pollingInterval: detailPoll,
  });
  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-xl">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <FileAudio className="size-4" />
            {data?.calleeName ?? "Call"}
          </SheetTitle>
          <SheetDescription>
            {data ? `Created ${formatDateTime(data.createdAt)}` : "Loading call…"}
          </SheetDescription>
        </SheetHeader>
        <div className="px-4 pb-6">
          {isLoading && <p className="text-muted-foreground text-sm">Loading…</p>}
          {error && <ErrorState error={error} onRetry={() => void refetch()} />}
          {data && <CallDetailBody call={data} />}
        </div>
      </SheetContent>
    </Sheet>
  );
}
