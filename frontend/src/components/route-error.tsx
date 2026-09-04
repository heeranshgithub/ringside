"use client";

import { useEffect } from "react";

import { ErrorState } from "@/components/states";

export function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <div className="mx-auto max-w-2xl py-10">
      <ErrorState error={error} onRetry={reset} title="This page crashed" />
    </div>
  );
}
