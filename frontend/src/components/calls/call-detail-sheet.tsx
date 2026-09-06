"use client";

import { FileAudio, RefreshCw, ScrollText, Sparkles } from "lucide-react";
import { Fragment } from "react";
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
  formatDayOnly,
  formatDuration,
  formatResultValue,
  formatTimeOnly,
  humanizeKey,
  maskPhone,
  sameDay,
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

/** Inside one call's timeline every webhook kind is prefixed "call_", which says nothing here. */
const eventLabel = (kind: string) => titleCase(kind.replace(/^call_/, ""));

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
          <span className="bg-done-bg text-done rounded-full px-2 text-xs">safe dial</span>
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
              <span className="text-muted-foreground ml-auto text-[11px]">model-scored</span>
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
            {!config?.llmEnabled
              ? "Transcription needs an OpenRouter key on the backend."
              : transcribeState.isLoading
                ? "Transcribing the recording…"
                : "Not transcribed yet. Transcription sends the recording to the configured audio model."}
          </p>
        )}
        {/*
          No re-transcribe once a transcript exists. The audio never changes, so a second run only
          costs money and returns the same words; Re-assess is different because its inputs do change.
          The word on the button changes while it runs because a pulsing icon alone reads as nothing
          happening: the recording is downloaded and sent up whole, so this is the slowest button here.
        */}
        {!call.transcript && (
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
            {transcribeState.isLoading ? "Transcribing…" : "Transcribe"}
          </Button>
        )}
      </Section>

      <Section title="Timeline">
        <ol className="space-y-1.5 text-xs">
          {call.events.map((e, i) => {
            const prev = i > 0 ? call.events[i - 1] : null;
            return (
              <Fragment key={i}>
                {/*
                  The day is a heading, not a column. Repeating "06 Sept" on every row spent a
                  third of the width restating something that changes once, if at all — and that
                  width is exactly what a long kind plus its badge needed to stay on one line.
                  A call that retries overnight still reads correctly, because the heading only
                  appears when the day actually changes.
                */}
                {(!prev || !sameDay(prev.at, e.at)) && (
                  <li className="text-muted-foreground pt-1.5 text-[11px] font-medium first:pt-0">
                    {formatDayOnly(e.at)}
                  </li>
                )}
                {/*
                  A grid, not a flex row. As flex, `ml-auto` on the source pushed it to the edge
                  and squeezed the kind until a long one wrapped; `items-center` then centred the
                  timestamp and source against the taller row, so that line sat out of step with
                  every other. Real columns give the kind its own track instead of leftovers.
                */}
                <li className="grid grid-cols-[4.5rem_1fr_auto] items-baseline gap-x-2 gap-y-1">
                  <span className="text-muted-foreground tabular-nums">{formatTimeOnly(e.at)}</span>
                  <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="font-medium">{eventLabel(e.kind)}</span>
                    {e.status && <StatusBadge status={e.status} />}
                  </span>
                  <span className="text-muted-foreground text-right">{e.source}</span>
                </li>
              </Fragment>
            );
          })}
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
      {/*
        The width has to carry the same variant chain as the base component's
        `data-[side=right]:sm:max-w-sm`, not a plain `sm:max-w-xl`. tailwind-merge sees two
        different variant chains, keeps both, and the attribute selector then wins on
        specificity — so a plain `sm:max-w-xl` here is silently dead and the sheet stays at
        384px. That is what cramped the timeline into wrapping.
      */}
      <SheetContent className="w-full overflow-y-auto data-[side=right]:sm:max-w-xl">
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
