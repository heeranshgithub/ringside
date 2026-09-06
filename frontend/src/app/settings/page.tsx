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

function Row({ label, value, ok }: { label: string; value: React.ReactNode; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b py-2 text-sm last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="flex items-center gap-2 text-right">
        {ok !== undefined && (
          <span
            className={`size-2 rounded-full ${ok ? "bg-emerald-500" : "bg-muted-foreground/40"}`}
            aria-hidden
          />
        )}
        {value}
      </span>
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
                  ? "On (all calls go to the test number)"
                  : "Off (cleared candidates are dialled for real)"
              }
              ok={data.safeDialMode}
            />
            <Row
              label="Test numbers"
              value={data.testPhoneNumbersMasked.join(", ") || "none configured"}
              ok={data.testPhoneNumbersMasked.length > 0}
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
                ok={cap.state === "ok"}
                value={
                  <span className="flex flex-col items-end">
                    <span
                      className={
                        cap.state === "ok"
                          ? "text-done"
                          : cap.state === "degraded"
                            ? "text-live-ink"
                            : "text-fail"
                      }
                    >
                      {cap.state === "ok"
                        ? "configured"
                        : cap.state === "degraded"
                          ? "degraded"
                          : "not configured"}
                    </span>
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
