"use client";

import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/field";
import { DialTargetCard } from "@/components/dial/dial-target-card";
import { PageHeader } from "@/components/page-header";
import { ErrorState, PageSkeleton } from "@/components/states";
import { useGetConfigQuery } from "@/features/calls/api";
import { setAccessCode, useAccessCode } from "@/lib/access-code";

/**
 * The lamp, the word and the ink for one state, in one place. Keeping them together is what
 * stops a lamp from turning green while the word beside it still says "not configured": the
 * two used to be decided by separate ternaries at the call site.
 *
 * `off` is not a failure. It is a switch the operator turned off on purpose, so it gets the
 * muted lamp rather than the red one.
 */
const STATE = {
  ok: { lamp: "bg-done", ink: "text-done", word: "configured" },
  degraded: { lamp: "bg-live", ink: "text-live-ink", word: "degraded" },
  missing: { lamp: "bg-fail", ink: "text-fail", word: "not configured" },
  off: { lamp: "bg-muted-foreground/40", ink: "text-muted-foreground", word: "off" },
} as const;

type RowState = keyof typeof STATE;

/**
 * One line of the readout: label on the left, value on the right, status lamp beside the
 * label.
 *
 * The lamp used to sit next to the value, and it never lined up. The value column is
 * right-aligned and sized to its own content, so a lamp anchored to its left edge lands at a
 * different x on every row, and on a two-line value it floated between the lines instead of
 * beside the word it describes. Anchoring the lamp to the label instead gives it the one
 * fixed edge on the row, which is what makes a column of lamps read as a column.
 *
 * The lamp element is always rendered, transparent when the row has no state, so a stateless
 * row's label does not slide left and break the same alignment from the other direction.
 */
function Row({ label, value, state }: { label: string; value: React.ReactNode; state?: RowState }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b py-2 text-sm last:border-0">
      <span className="text-muted-foreground flex items-center gap-2">
        <span
          className={`size-2 shrink-0 rounded-full ${state ? STATE[state].lamp : "bg-transparent"}`}
          aria-hidden
        />
        {label}
      </span>
      <span className="text-right">{value}</span>
    </div>
  );
}

export default function SettingsPage() {
  const { data, error, isLoading, refetch } = useGetConfigQuery();
  const stored = useAccessCode();
  const [code, setCode] = useState(stored ?? "");
  if (isLoading) return <PageSkeleton />;
  if (error || !data) return <ErrorState error={error} onRetry={() => void refetch()} />;
  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Everything here is read from the backend environment. Secrets never reach the browser."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Dialling safety</CardTitle>
            <CardDescription>Controls where outbound calls actually ring.</CardDescription>
          </CardHeader>
          <CardContent>
            <Row
              label="Safe-dial mode"
              value={
                data.safeDialMode
                  ? "On (every call goes to a number you verified below)"
                  : "Off (cleared candidates are dialled for real)"
              }
              state={data.safeDialMode ? "ok" : "off"}
            />
            <Row label="Environment" value={data.env} />
            <DialTargetCard className="mt-3" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Integrations</CardTitle>
            <CardDescription>
              What this deployment can actually do. Anything missing is refused with a clear error,
              never quietly simulated.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* A field the running backend may predate, during a rolling deploy or a
                hot reload holding an older cached response. Never map it bare. */}
            {(data.capabilities ?? []).map((cap) => (
              <Row
                key={cap.key}
                label={cap.label}
                state={cap.state}
                value={
                  <span className="flex flex-col items-end">
                    <span className={STATE[cap.state].ink}>{STATE[cap.state].word}</span>
                    <span className="text-muted-foreground max-w-80 text-right text-[11.5px]">
                      {cap.detail}
                      {cap.envVar ? ` Set ${cap.envVar}.` : ""}
                    </span>
                  </span>
                }
              />
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Access code</CardTitle>
            <CardDescription>
              {data.accessCodeRequired
                ? "This deployment requires a code on every request."
                : "No access code is required on this deployment."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Field
              label="Code stored in this browser"
              htmlFor="settings-code"
              hint="Shown in full: it is a shared code, and hiding it from you helps nobody."
            >
              {/* Plain text, so a browser password manager never saves or re-fills it. */}
              <Input
                id="settings-code"
                name="ringside-access-stored"
                type="text"
                autoComplete="off"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                placeholder="not set"
                className="font-mono tracking-wide"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </Field>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={() => {
                  setAccessCode(code.trim() || null);
                  void refetch();
                  toast.success("Access code saved for this browser");
                }}
              >
                Save
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setCode("");
                  setAccessCode(null);
                  void refetch();
                  toast.success("Access code cleared. You will be asked for it again.");
                }}
              >
                Forget it
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
