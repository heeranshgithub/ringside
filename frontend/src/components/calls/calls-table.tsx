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
import { formatDuration, formatRelative, maskPhone } from "@/lib/format";
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
    <div className="overflow-x-auto rounded-xl border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Candidate</TableHead>
            {showJob && <TableHead>Job</TableHead>}
            <TableHead>Status</TableHead>
            <TableHead>Engaged</TableHead>
            <TableHead>Fit</TableHead>
            <TableHead>Summary</TableHead>
            <TableHead className="text-right">Duration</TableHead>
            <TableHead className="text-right">Updated</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {calls.map((c) => {
            const summary =
              c.assessment?.headline ??
              (typeof c.result.summary === "string" ? c.result.summary : null);
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
                  <div className="text-muted-foreground text-xs">
                    {maskPhone(c.dialedNumber)}
                    {c.safeDial && " · safe"}
                  </div>
                </TableCell>
                {showJob && (
                  <TableCell className="text-muted-foreground max-w-40 truncate text-xs">
                    {jobTitles?.[c.jobId] ?? c.jobId.slice(0, 8)}
                  </TableCell>
                )}
                <TableCell>
                  <StatusBadge status={c.status} />
                </TableCell>
                <TableCell>
                  <StatusBadge status={c.engagementStatus} />
                </TableCell>
                <TableCell>
                  {c.assessment ? <ScorePill score={c.assessment.fitScore} /> : "—"}
                </TableCell>
                <TableCell className="text-muted-foreground max-w-72 truncate text-xs">
                  {summary ?? "—"}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatDuration(c.durationSeconds)}
                </TableCell>
                <TableCell className="text-muted-foreground text-right text-xs">
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
