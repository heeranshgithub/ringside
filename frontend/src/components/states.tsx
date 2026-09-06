"use client";

import type { ReactNode } from "react";
import { AlertTriangle, Inbox, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { describeError } from "@/lib/errors";
import type { ApiError } from "@/lib/errors";

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="border-border flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed px-6 py-14 text-center">
      <div
        className="text-tint grid size-10 place-items-center rounded-full"
        style={{ background: "color-mix(in oklab, var(--tint) 12%, transparent)" }}
      >
        {icon ?? <Inbox className="size-5" />}
      </div>
      <div className="space-y-1">
        <p className="text-[15px] font-medium">{title}</p>
        {description && <p className="text-muted-foreground max-w-sm text-[13px]">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
  title = "Could not load this view",
}: {
  error?: ApiError | Error;
  onRetry?: () => void;
  title?: string;
}) {
  const summary = describeError(error, title);
  return (
    <div className="border-fail-line bg-fail-bg flex flex-col items-start gap-3 rounded-xl border p-5">
      <div className="text-fail flex items-center gap-2 text-sm font-medium">
        <AlertTriangle className="size-4" />
        {summary.title}
      </div>
      <p className="text-muted-foreground text-[13px]">{summary.message}</p>
      {summary.technical ? (
        <details className="w-full">
          <summary className="text-muted-foreground cursor-pointer text-xs select-none">
            Technical detail
          </summary>
          <p className="text-muted-foreground mt-1.5 font-mono text-xs break-all">
            {summary.technical}
          </p>
        </details>
      ) : null}
      {onRetry && (
        <Button size="sm" variant="outline" onClick={onRetry}>
          <RefreshCw data-icon="inline-start" />
          Retry
        </Button>
      )}
    </div>
  );
}

export function TableSkeleton({ rows = 6, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="surface overflow-hidden rounded-xl">
      <div className="bg-muted/40 flex gap-3 px-4 py-2.5">
        {Array.from({ length: cols }).map((_, c) => (
          <Skeleton key={c} className="h-3 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="border-border flex gap-3 border-t px-4 py-3">
          {Array.from({ length: cols }).map((__, c) => (
            <Skeleton key={c} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-[76px] rounded-xl" />
        ))}
      </div>
      <TableSkeleton />
    </div>
  );
}
