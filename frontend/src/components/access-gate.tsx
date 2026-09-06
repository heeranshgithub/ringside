"use client";

import { KeyRound } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState, PageSkeleton } from "@/components/states";
import { useGetConfigQuery } from "@/features/calls/api";
import { setAccessCode, useAccessCode } from "@/lib/access-code";
import { getErrorCode } from "@/lib/errors";

/** Who to ask for a code. Shown only when someone actually gets one wrong. */
const CONTACT_EMAIL = "heeranshconnect@gmail.com";

export function AccessGate({ children }: { children: React.ReactNode }) {
  const { error, isLoading, isFetching, refetch } = useGetConfigQuery();
  const stored = useAccessCode();

  const locked = getErrorCode(error) === "access_code_required";

  if (isLoading) return <PageSkeleton />;

  if (locked) {
    // Rejection is derived, not remembered: a code is saved and the server still refuses
    // it. Clearing the code from Settings therefore clears the error for free, instead of
    // leaving a stale "attempted" flag behind to accuse the next visitor.
    const rejected = stored !== null && !isFetching;
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="size-4" /> Access code required
            </CardTitle>
            <CardDescription>
              This deployment can place real phone calls, so it is gated behind a shared code. You
              will find it in the same email as this link.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/*
              Keyed on the saved code so the field re-seeds whenever storage changes: it
              keeps what you typed when a code is rejected, and empties when Settings
              forgets one.
            */}
            <AccessCodeForm
              key={stored ?? "∅"}
              initial={stored ?? ""}
              rejected={rejected}
              busy={isFetching}
              onSubmit={(code) => {
                setAccessCode(code);
                void refetch();
              }}
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error)
    return <ErrorState error={error} onRetry={() => void refetch()} title="Backend unreachable" />;

  return <>{children}</>;
}

function AccessCodeForm({
  initial,
  rejected,
  busy,
  onSubmit,
}: {
  initial: string;
  rejected: boolean;
  busy: boolean;
  onSubmit: (code: string) => void;
}) {
  const [code, setCode] = useState(initial);

  return (
    <form
      className="space-y-3"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(code.trim());
      }}
    >
      <div className="space-y-1.5">
        <Label htmlFor="access-code">Access code</Label>
        {/*
          Plain text on purpose. This is a shared code that gets handed out, not a
          personal password, so masking hides it from the one person entitled to
          read it while doing nothing about anyone else. It also keeps browser
          password managers from saving and re-filling it, which otherwise makes
          "Forget it" in Settings look like it failed.
        */}
        <Input
          id="access-code"
          name="ringside-access"
          type="text"
          autoComplete="off"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          placeholder="paste the code from the email"
          aria-invalid={rejected || undefined}
          aria-describedby={rejected ? "access-code-error" : undefined}
          className="font-mono tracking-wide"
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        {rejected && (
          <p id="access-code-error" role="alert" className="text-fail text-xs">
            That code is not right. Email{" "}
            <a
              href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent("Ringside access code")}`}
              className="text-fail font-medium underline underline-offset-2"
            >
              {CONTACT_EMAIL}
            </a>{" "}
            to get one.
          </p>
        )}
      </div>
      <Button type="submit" className="w-full" disabled={!code.trim() || busy}>
        {busy ? "Checking…" : "Continue"}
      </Button>
    </form>
  );
}
