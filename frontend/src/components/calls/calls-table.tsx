"use client";

import { ScorePill, StatusBadge } from "@/components/status-badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDuration, formatRelative } from "@/lib/format";
import type { Call } from "@/types/call";

export function CallsTable({
  calls,
  onSelect,
  showJob,
  jobTitles,
}: {
  calls: Call[];
  onSelect: (id: string) => void;
  showJob?: boolean;
  jobTitles?: Record<string, string>;
}) {
  return (
    <div className="border-border overflow-x-auto rounded-xl border">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Candidate</TableHead>
            {showJob && <TableHead>Job</TableHead>}
            <TableHead>Status</TableHead>
            <TableHead>Fit</TableHead>
            <TableHead>What the agent heard</TableHead>
            <TableHead className="text-right">Length</TableHead>
            <TableHead className="text-right">Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {calls.map((c) => {
            const summary =
              c.assessment?.headline ??
              (typeof c.result.summary === "string" ? c.result.summary : null);
            const retrying = c.status === "NOT_CONNECTED" && (c.retriesLeft ?? 0) > 0;
            return (
              <TableRow
                key={c.id}
                className="cursor-pointer"
                tabIndex={0}
                onClick={() => onSelect(c.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(c.id);
                  }
                }}
              >
                <TableCell>
                  <div className="font-medium">{c.calleeName}</div>
                  <div className="text-muted-foreground text-[11.5px]">
                    {c.engagementStatus === "ENGAGED"
                      ? "Engaged"
                      : c.engagementStatus === "NOT_ENGAGED"
                        ? "Did not engage"
                        : retrying
                          ? "Retry queued"
                          : c.safeDial
                            ? "Safe dial"
                            : "Direct dial"}
                  </div>
                </TableCell>
                {showJob && (
                  <TableCell className="text-muted-foreground max-w-56 truncate text-[12.5px]">
                    {jobTitles?.[c.jobId] ?? "—"}
                  </TableCell>
                )}
                <TableCell>
                  <StatusBadge status={c.status} />
                </TableCell>
                <TableCell>
                  {c.assessment ? (
                    <ScorePill score={c.assessment.fitScore} />
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground max-w-80 truncate text-[12.5px]">
                  {summary ?? "—"}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatDuration(c.durationSeconds)}
                </TableCell>
                <TableCell className="text-muted-foreground text-right text-[12px] whitespace-nowrap">
                  {formatRelative(c.updatedAt)}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
