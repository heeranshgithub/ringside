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

export function AccessGate({ children }: { children: React.ReactNode }) {
  const { error, isLoading, refetch } = useGetConfigQuery();
  const [code, setCode] = useState("");

  if (isLoading) return <PageSkeleton />;

  if (error && getErrorCode(error) === "access_code_required") {
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
                setAccessCode(code.trim());
                void refetch();
              }}
            >
              <div className="space-y-1.5">
                <Label htmlFor="access-code">Access code</Label>
                <Input
                  id="access-code"
                  type="password"
                  autoComplete="off"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                />
              </div>
              <Button type="submit" className="w-full" disabled={!code.trim()}>
                Continue
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
