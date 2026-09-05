"use client";

import Link from "next/link";
import { BriefcaseBusiness, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/states";
import { StatusBadge } from "@/components/status-badge";
import { useGetJobsQuery } from "@/features/jobs/api";
import { formatRelative } from "@/lib/format";

export default function JobsPage() {
  const { data, error, isLoading, refetch } = useGetJobsQuery();
  return (
    <div className="space-y-6">
      <PageHeader
        title="Jobs"
        description="Each job owns its candidates, its screening agent and its call results."
        actions={
          <Button nativeButton={false} render={<Link href="/jobs/new" />}>
            <Plus data-icon="inline-start" /> New job
          </Button>
        }
      />
      {isLoading && <TableSkeleton />}
      {error && <ErrorState error={error} onRetry={() => void refetch()} />}
      {data && data.length === 0 && (
        <EmptyState
          icon={<BriefcaseBusiness className="size-5" />}
          title="No jobs yet"
          description="Paste a job description and let the assistant draft screening questions and a voice agent."
          action={
            <Button nativeButton={false} render={<Link href="/jobs/new" />}>
              <Plus data-icon="inline-start" /> Create your first job
            </Button>
          }
        />
      )}
      {data && data.length > 0 && (
        <div className="surface overflow-x-auto rounded-xl">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Agent</TableHead>
                <TableHead className="text-right">Candidates</TableHead>
                <TableHead className="text-right">Calls</TableHead>
                <TableHead className="text-right">Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((j) => (
                <TableRow key={j.id}>
                  <TableCell>
                    <Link href={`/jobs/${j.id}`} className="font-medium hover:underline">
                      {j.title}
                    </Link>
                    <div className="text-muted-foreground text-xs">
                      {[j.company, j.location].filter(Boolean).join(" · ") || "—"}
                    </div>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={j.status} />
                  </TableCell>
                  <TableCell className="text-xs">
                    {j.agentId ? (
                      "Ready"
                    ) : (
                      <span className="text-muted-foreground">Not created</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{j.candidateCount}</TableCell>
                  <TableCell className="text-right tabular-nums">{j.callCount}</TableCell>
                  <TableCell className="text-muted-foreground text-right text-xs">
                    {formatRelative(j.updatedAt)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
