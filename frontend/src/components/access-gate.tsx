"use client";

import { KeyRound } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ErrorState, PageSkeleton } from "@/components/states";
import { useGetConfigQuery } from "@/features/calls/api";
import { setAccessCode } from "@/lib/access-code";
import { getErrorCode } from "@/lib/errors";

/** Who to ask for a code. Shown only when someone actually gets one wrong. */
const CONTACT_EMAIL = "heeranshconnect@gmail.com";

export function AccessGate({ children }: { children: React.ReactNode }) {
  const { error, isLoading, isFetching, refetch } = useGetConfigQuery();
  const [code, setCode] = useState("");
  const [attempted, setAttempted] = useState(false);

  const locked = getErrorCode(error) === "access_code_required";
  const rejected = attempted && !isFetching && locked;

  if (isLoading) return <PageSkeleton />;

  if (locked) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <KeyRound className="size-4" /> Access code required
            </CardTitle>
            <CardDescription>
              This deployment can place real phone calls, so it is gated behind a shared code.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                setAttempted(true);
                setAccessCode(code.trim());
                void refetch();
              }}
            >
              <div className="space-y-1.5">
                <Label htmlFor="access-code">Access code</Label>
                {/*
                  Plain text on purpose. This is a shared code that gets handed out, not a
                  personal password, so masking hides it from the one person entitled to
                  read it while doing nothing about anyone else. It also keeps browser
                  password managers from saving and re-filling it, which otherwise makes
                  "Clear" in Settings look like it failed.
                */}
                <Input
                  id="access-code"
                  name="ringside-access"
                  type="text"
                  autoComplete="off"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  placeholder="xxxx-xxxx-xxxx"
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
              <Button type="submit" className="w-full" disabled={!code.trim() || isFetching}>
                {isFetching ? "Checking…" : "Continue"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error)
    return <ErrorState error={error} onRetry={() => void refetch()} title="Backend unreachable" />;

  return <>{children}</>;
}
