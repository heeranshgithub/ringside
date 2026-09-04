"use client";

import { PhoneCall, RefreshCw } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CallDetailSheet } from "@/components/calls/call-detail-sheet";
import { CallsTable } from "@/components/calls/calls-table";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/states";
import { useGetCallsQuery, useSyncAllCallsMutation } from "@/features/calls/api";
import { useGetJobsQuery } from "@/features/jobs/api";
import { getErrorMessage } from "@/lib/errors";
import type { CallStatus } from "@/types/call";

const STATUSES: CallStatus[] = [
  "SCHEDULED",
  "INITIATED",
  "RINGING",
  "IN_PROGRESS",
  "COMPLETED",
  "NOT_CONNECTED",
  "CANCELLED",
  "FAILED",
];
const PAGE_SIZE = 25;

export default function CallsPage() {
  const [status, setStatus] = useState<string>("all");
  const [jobId, setJobId] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const { data: jobs } = useGetJobsQuery();
  const { data, error, isLoading, refetch } = useGetCallsQuery(
    {
      status: status === "all" ? undefined : [status as CallStatus],
      jobId: jobId === "all" ? undefined : jobId,
      page,
      pageSize: PAGE_SIZE,
    },
    { pollingInterval: 10000 },
  );
  const [syncAll, syncState] = useSyncAllCallsMutation();
  const jobTitles = Object.fromEntries((jobs ?? []).map((j) => [j.id, j.title]));
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Calls"
        description="Every call placed from this app, synced from Hunar via webhooks and a background poller."
        actions={
          <Button
            variant="outline"
            size="sm"
            disabled={syncState.isLoading}
            onClick={async () => {
              try {
                const r = await syncAll().unwrap();
                toast.success(`Synced ${r.synced}, ${r.errors} error${r.errors === 1 ? "" : "s"}`);
              } catch (e) {
                toast.error(getErrorMessage(e as never));
              }
            }}
          >
            <RefreshCw
              data-icon="inline-start"
              className={syncState.isLoading ? "animate-spin" : ""}
            />{" "}
            Sync pending
          </Button>
        }
      />
      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v ?? "all");
            setPage(1);
          }}
        >
          <SelectTrigger className="w-44" aria-label="Filter by status">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s.replace("_", " ")}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={jobId}
          onValueChange={(v) => {
            setJobId(v ?? "all");
            setPage(1);
          }}
        >
          <SelectTrigger className="w-56" aria-label="Filter by job">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All jobs</SelectItem>
            {(jobs ?? []).map((j) => (
              <SelectItem key={j.id} value={j.id}>
                {j.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {data && (
          <span className="text-muted-foreground ml-auto text-xs">
            {data.total} call{data.total === 1 ? "" : "s"}
          </span>
        )}
      </div>
      {isLoading && <TableSkeleton />}
      {error && <ErrorState error={error} onRetry={() => void refetch()} />}
      {data && data.items.length === 0 && (
        <EmptyState
          icon={<PhoneCall className="size-5" />}
          title="No calls match"
          description="Start calls from a job's Candidates tab."
        />
      )}
      {data && data.items.length > 0 && (
        <>
          <CallsTable calls={data.items} onSelect={setSelected} showJob jobTitles={jobTitles} />
          {totalPages > 1 && (
            <div className="flex items-center justify-end gap-2 text-sm">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-muted-foreground text-xs">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
      <CallDetailSheet callId={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
