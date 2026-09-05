"use client";

import Link from "next/link";
import { Bot, Download, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Field } from "@/components/field";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/states";
import { useGetAgentsQuery, useImportAgentMutation } from "@/features/agents/api";
import { useGetJobsQuery } from "@/features/jobs/api";
import { getErrorMessage } from "@/lib/errors";
import { formatRelative } from "@/lib/format";

export default function AgentsPage() {
  const { data, error, isLoading, refetch } = useGetAgentsQuery();
  const { data: jobs } = useGetJobsQuery();
  const [importAgent, importState] = useImportAgentMutation();
  const [importOpen, setImportOpen] = useState(false);
  const [hunarId, setHunarId] = useState("");
  const jobTitle = Object.fromEntries((jobs ?? []).map((j) => [j.id, j.title]));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Voice agents"
        description="Each agent is a Hunar voice persona with a prompt, a script and a result schema. This list shows only agents created or imported by this app."
        actions={
          <>
            <Button variant="outline" onClick={() => setImportOpen(true)}>
              <Download data-icon="inline-start" /> Import by ID
            </Button>
            <Button nativeButton={false} render={<Link href="/agents/new" />}>
              <Plus data-icon="inline-start" /> New agent
            </Button>
          </>
        }
      />
      {isLoading && <TableSkeleton />}
      {error && <ErrorState error={error} onRetry={() => void refetch()} />}
      {data && data.length === 0 && (
        <EmptyState
          icon={<Bot className="size-5" />}
          title="No agents yet"
          description="Agents are usually generated from a job. You can also write one from scratch."
          action={
            <Button nativeButton={false} render={<Link href="/agents/new" />}>
              <Plus data-icon="inline-start" /> Create agent
            </Button>
          }
        />
      )}
      {data && data.length > 0 && (
        <div className="surface overflow-x-auto rounded-xl">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Agent</TableHead>
                <TableHead>Voice</TableHead>
                <TableHead>Variables</TableHead>
                <TableHead>Job</TableHead>
                <TableHead className="text-right">Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((a) => (
                <TableRow key={a.id}>
                  <TableCell>
                    <Link href={`/agents/${a.id}`} className="font-medium hover:underline">
                      {a.name}
                    </Link>
                    <div className="text-muted-foreground text-xs">
                      {a.agentCode ?? "—"} · {a.source}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm">
                    {a.voicePersona}
                    <span className="text-muted-foreground"> · {a.language}</span>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {a.customVariables.map((v) => (
                        <Badge key={v} variant="outline" className="font-mono">
                          {v}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-xs">
                    {a.jobId ? (
                      <Link href={`/jobs/${a.jobId}`} className="hover:underline">
                        {jobTitle[a.jobId] ?? a.jobId.slice(0, 8)}
                      </Link>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-right text-xs">
                    {formatRelative(a.createdAt)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={importOpen} onOpenChange={setImportOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Import an existing Hunar agent</DialogTitle>
            <DialogDescription>
              Paste the agent UUID from the Hunar console or API. Its prompts are mirrored here.
            </DialogDescription>
          </DialogHeader>
          <Field label="Hunar agent ID" htmlFor="import-agent-id">
            <Input
              id="import-agent-id"
              value={hunarId}
              onChange={(e) => setHunarId(e.target.value)}
              placeholder="e76d7b18-…"
            />
          </Field>
          <DialogFooter>
            <Button variant="outline" onClick={() => setImportOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={!hunarId.trim() || importState.isLoading}
              onClick={async () => {
                try {
                  await importAgent({ hunarAgentId: hunarId.trim() }).unwrap();
                  toast.success("Agent imported");
                  setImportOpen(false);
                  setHunarId("");
                } catch (e) {
                  toast.error(getErrorMessage(e as never));
                }
              }}
            >
              {importState.isLoading ? "Importing…" : "Import"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
