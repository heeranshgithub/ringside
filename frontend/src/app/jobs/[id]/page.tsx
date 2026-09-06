"use client";

import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Bot, FileUp, PhoneOutgoing, Plus, Search, Sparkles, Trash2, UserPlus } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { AgentForm, type AgentFormOutput } from "@/components/agents/agent-form";
import { CallDetailSheet } from "@/components/calls/call-detail-sheet";
import { CallsTable } from "@/components/calls/calls-table";
import { LaunchCallsDialog } from "@/components/calls/launch-calls-dialog";
import { AddCandidateDialog, ImportCsvDialog } from "@/components/candidates/candidate-dialogs";
import { PeopleSearchPanel } from "@/components/candidates/people-search-panel";
import { CapabilityNotice } from "@/components/capability-notice";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, PageSkeleton, TableSkeleton } from "@/components/states";
import { StatusBadge } from "@/components/status-badge";
import {
  useCreateAgentMutation,
  useDraftAgentMutation,
  useGetAgentQuery,
  useGetAgentsQuery,
} from "@/features/agents/api";
import { useGetCallsQuery, useGetConfigQuery } from "@/features/calls/api";
import {
  useDeleteCandidateMutation,
  useGetCandidatesQuery,
  useUpdateCandidateMutation,
} from "@/features/candidates/api";
import { useDeleteJobMutation, useGetJobQuery, useUpdateJobMutation } from "@/features/jobs/api";
import { useLiveInterval } from "@/features/live/live-provider";
import { getErrorMessage } from "@/lib/errors";
import { selectItems } from "@/lib/select-items";
import { maskPhone } from "@/lib/format";
import type { AgentDraft } from "@/types/agent";
import type { Candidate, CandidateSource } from "@/types/candidate";
import type { Job } from "@/types/job";

const TABS = ["overview", "agent", "candidates", "calls"] as const;
type Tab = (typeof TABS)[number];

export default function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const search = useSearchParams();
  const initialTab = (TABS as readonly string[]).includes(search.get("tab") ?? "")
    ? (search.get("tab") as Tab)
    : "overview";
  const [tab, setTab] = useState<Tab>(initialTab);
  const { data: job, error, isLoading, refetch } = useGetJobQuery(id);
  const [deleteJob] = useDeleteJobMutation();
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (isLoading) return <PageSkeleton />;
  if (error || !job) return <ErrorState error={error} onRetry={() => void refetch()} />;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={
          <span className="flex items-center gap-2">
            <Link href="/jobs" className="hover:underline">
              Jobs
            </Link>
            <span>/</span>
            <StatusBadge status={job.status} />
          </span>
        }
        title={job.title}
        description={
          [job.company, job.location, job.seniority].filter(Boolean).join(" · ") || job.summary
        }
        actions={
          <>
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive"
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 data-icon="inline-start" /> Delete
            </Button>
            <ConfirmDialog
              open={confirmDelete}
              onOpenChange={setConfirmDelete}
              title="Delete this job?"
              description="Its candidates and call records are deleted with it. The Hunar agent itself is kept."
              confirmLabel="Delete job"
              pendingLabel="Deleting…"
              onConfirm={async () => {
                await deleteJob(job.id).unwrap();
                toast.success("Job deleted");
                router.push("/jobs");
              }}
            />
          </>
        }
      />

      <Tabs value={tab} onValueChange={(v) => setTab(v as Tab)}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="agent">
            Agent {job.agentId ? "" : "·"}
            {!job.agentId && (
              <span className="bg-live ml-1 size-1.5 rounded-full" aria-label="needs setup" />
            )}
          </TabsTrigger>
          <TabsTrigger value="candidates">Candidates ({job.candidateCount})</TabsTrigger>
          <TabsTrigger value="calls">Calls ({job.callCount})</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">
          <OverviewTab job={job} />
        </TabsContent>
        <TabsContent value="agent">
          <AgentTab job={job} onDone={() => setTab("candidates")} />
        </TabsContent>
        <TabsContent value="candidates">
          <CandidatesTab job={job} onLaunched={() => setTab("calls")} />
        </TabsContent>
        <TabsContent value="calls">
          <CallsTab job={job} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="space-y-1.5">
      <p className="text-sm font-medium">{title}</p>
      {items.length === 0 ? (
        <p className="text-muted-foreground text-sm">—</p>
      ) : (
        <ul className="list-disc space-y-0.5 pl-5 text-sm">
          {items.map((i) => (
            <li key={i}>{i}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function OverviewTab({ job }: { job: Job }) {
  const c = job.searchCriteria;
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>What we are screening for</CardTitle>
          <CardDescription>{job.summary || "No summary."}</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-5 sm:grid-cols-2">
          <ListBlock title="Must-haves" items={job.mustHaves} />
          <ListBlock title="Nice-to-haves" items={job.niceToHaves} />
          <div className="sm:col-span-2">
            <ListBlock title="Screening questions" items={job.screeningQuestions} />
          </div>
          <details className="sm:col-span-2">
            <summary className="cursor-pointer text-sm font-medium">Full description</summary>
            <pre className="text-muted-foreground mt-2 max-h-80 overflow-auto rounded-lg border p-3 font-sans text-xs whitespace-pre-wrap">
              {job.description}
            </pre>
          </details>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>People-search criteria</CardTitle>
          <CardDescription>Used by the search providers.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          {(
            [
              ["Titles", c.titles],
              ["Locations", c.locations],
              ["Skills", c.skills],
              ["Seniority", c.seniorities],
            ] as const
          ).map(([label, items]) => (
            <div key={label}>
              <p className="text-muted-foreground text-xs">{label}</p>
              <div className="mt-1 flex flex-wrap gap-1">
                {items.length ? (
                  items.map((i) => (
                    <Badge key={i} variant="secondary">
                      {i}
                    </Badge>
                  ))
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </div>
            </div>
          ))}
          {c.keywords && (
            <div>
              <p className="text-muted-foreground text-xs">Keywords</p>
              <p>{c.keywords}</p>
            </div>
          )}
          {job.salaryRange && (
            <div>
              <p className="text-muted-foreground text-xs">Salary</p>
              <p>{job.salaryRange}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function AgentTab({ job, onDone }: { job: Job; onDone: () => void }) {
  const { data: config } = useGetConfigQuery();
  const { data: agent, isLoading } = useGetAgentQuery(job.agentId ?? "", { skip: !job.agentId });
  const { data: agents } = useGetAgentsQuery();
  const agentItems = useMemo(
    () =>
      selectItems(
        agents ?? [],
        (a) => a.id,
        (a) => a.name,
      ),
    [agents],
  );
  const [draftAgent, draftState] = useDraftAgentMutation();
  const [createAgent, createState] = useCreateAgentMutation();
  const [updateJob] = useUpdateJobMutation();
  const [draft, setDraft] = useState<AgentDraft | null>(null);

  const generate = async () => {
    try {
      const d = await draftAgent({ jobId: job.id }).unwrap();
      setDraft(d);
      toast.success("Draft generated");
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  };

  const create = async (values: AgentFormOutput) => {
    try {
      await createAgent({
        ...values,
        jobId: job.id,
        source: draft ? "generated" : "manual",
      }).unwrap();
      toast.success("Agent created on Hunar");
      setDraft(null);
      onDone();
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  };

  if (job.agentId && isLoading) return <TableSkeleton rows={3} />;

  if (job.agentId && agent) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="size-4" /> {agent.name}
          </CardTitle>
          <CardDescription>
            {agent.voicePersona} voice · {agent.language} · code {agent.agentCode ?? "—"} ·
            variables: {agent.customVariables.map((v) => `{${v}}`).join(", ") || "none"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-muted-foreground text-xs">Introduction</p>
              <p className="text-sm">{agent.introduction}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs">Objective</p>
              <p className="text-sm">{agent.objective}</p>
            </div>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Result fields</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {Object.keys(agent.resultSchema).map((k) => (
                <Badge key={k} variant="outline">
                  {k}
                </Badge>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link href={`/agents/${agent.id}`} />}
            >
              Edit prompts
            </Button>
            <Button variant="ghost" onClick={onDone}>
              Go to candidates
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <CapabilityNotice capability="hunar" />
      <CapabilityNotice capability="llm" />
      {!draft && (
        <Card>
          <CardHeader>
            <CardTitle>This job has no voice agent yet</CardTitle>
            <CardDescription>
              Generate one from the screening questions
              {!config?.llmEnabled && " using templates"}, or attach an agent you already created.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <Button onClick={generate} disabled={draftState.isLoading}>
              <Sparkles
                data-icon="inline-start"
                className={draftState.isLoading ? "animate-pulse" : ""}
              />
              {draftState.isLoading ? "Drafting…" : "Generate agent"}
            </Button>
            {agents && agents.length > 0 && (
              <div className="flex items-end gap-2">
                {/*
                  Flex gap, not `space-y`: Base UI gives a Select a hidden `position: fixed`
                  input as its last child for form integration. That input takes the
                  `:last-child` slot `space-y` exempts, so the trigger above it keeps a 6px
                  bottom margin meant only for gaps between controls. The box then ends 6px
                  below the trigger, and this `items-end` row aligns on the box, sitting the
                  select a notch above the button beside it.
                */}
                <div className="flex flex-col gap-1.5">
                  <p className="text-muted-foreground text-xs">or attach existing</p>
                  <Select
                    items={agentItems}
                    onValueChange={async (v) => {
                      if (!v) return;
                      try {
                        await updateJob({
                          id: job.id,
                          agentId: String(v),
                          status: "active",
                        }).unwrap();
                        toast.success("Agent attached");
                      } catch (e) {
                        toast.error(getErrorMessage(e as never));
                      }
                    }}
                  >
                    <SelectTrigger className="w-64">
                      <SelectValue placeholder="Choose an agent" />
                    </SelectTrigger>
                    <SelectContent>
                      {agents.map((a) => (
                        <SelectItem key={a.id} value={a.id}>
                          {a.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
      {draft && (
        <Card>
          <CardHeader>
            <CardTitle>Review the generated agent</CardTitle>
            <CardDescription>
              Edit anything, then create it on Hunar. Placeholders in braces are filled per call
              from the job and candidate.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <AgentForm
              initial={draft}
              onSubmit={create}
              submitLabel="Create agent on Hunar"
              busy={createState.isLoading}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

const SOURCE_LABEL: Record<CandidateSource, string> = {
  manual: "Manual",
  csv: "CSV",
  mock: "Demo",
  pdl: "PDL",
  coresignal: "Coresignal",
  apollo: "Apollo",
};

function CandidatesTab({ job, onLaunched }: { job: Job; onLaunched: () => void }) {
  const candidatesPoll = useLiveInterval(10000);
  const { data: config } = useGetConfigQuery();
  const {
    data: candidates,
    error,
    isLoading,
    refetch,
  } = useGetCandidatesQuery({ jobId: job.id }, { pollingInterval: candidatesPoll });
  const [updateCandidate] = useUpdateCandidateMutation();
  const [deleteCandidate] = useDeleteCandidateMutation();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [addOpen, setAddOpen] = useState(false);
  const [csvOpen, setCsvOpen] = useState(false);
  const [launchOpen, setLaunchOpen] = useState(false);
  const [showSearch, setShowSearch] = useState(false);

  const list = useMemo(() => candidates ?? [], [candidates]);
  const selectedCandidates = list.filter((c) => selected.has(c.id));
  const allSelected = list.length > 0 && selected.size === list.length;
  const realDial = config && !config.safeDialMode;

  const toggle = (id: string, on: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  return (
    <div className="space-y-4">
      <CapabilityNotice capability="dialling" />
      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={() => setAddOpen(true)}>
          <UserPlus data-icon="inline-start" /> Add
        </Button>
        <Button variant="outline" size="sm" onClick={() => setCsvOpen(true)}>
          <FileUp data-icon="inline-start" /> Import CSV
        </Button>
        <Button
          variant={showSearch ? "secondary" : "outline"}
          size="sm"
          onClick={() => setShowSearch((s) => !s)}
        >
          <Search data-icon="inline-start" /> Find people
        </Button>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-muted-foreground text-xs">{selected.size} selected</span>
          <Button size="sm" disabled={selected.size === 0} onClick={() => setLaunchOpen(true)}>
            <PhoneOutgoing data-icon="inline-start" /> Start calls
          </Button>
        </div>
      </div>

      {showSearch && (
        <Card>
          <CardHeader>
            <CardTitle>Find people for this job</CardTitle>
            <CardDescription>
              Criteria are pre-filled from the job. Imported profiles become candidates you can
              call.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <PeopleSearchPanel
              key={job.id}
              jobId={job.id}
              initialCriteria={job.searchCriteria}
              onImported={() => setShowSearch(false)}
            />
          </CardContent>
        </Card>
      )}

      {isLoading && <TableSkeleton />}
      {error && <ErrorState error={error} onRetry={() => void refetch()} />}
      {candidates && candidates.length === 0 && !showSearch && (
        <EmptyState
          title="No candidates yet"
          description="Add one by hand, import a CSV, or search people-data providers using the job's criteria."
          action={
            <Button size="sm" onClick={() => setAddOpen(true)}>
              <Plus data-icon="inline-start" /> Add candidate
            </Button>
          }
        />
      )}
      {list.length > 0 && (
        <div className="surface overflow-x-auto rounded-xl">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8">
                  <Checkbox
                    aria-label="Select all"
                    checked={allSelected}
                    onCheckedChange={(on) =>
                      setSelected(on ? new Set(list.map((c) => c.id)) : new Set())
                    }
                  />
                </TableHead>
                <TableHead>Candidate</TableHead>
                <TableHead>Current role</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Last call</TableHead>
                {realDial && <TableHead>Real dial</TableHead>}
                <TableHead className="w-10" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.map((c) => (
                <CandidateRow
                  key={c.id}
                  candidate={c}
                  checked={selected.has(c.id)}
                  onCheck={(on) => toggle(c.id, on)}
                  realDial={Boolean(realDial)}
                  onToggleRealDial={async (on) => {
                    try {
                      await updateCandidate({ id: c.id, allowRealDial: on }).unwrap();
                    } catch (e) {
                      toast.error(getErrorMessage(e as never));
                    }
                  }}
                  onDelete={async () => {
                    try {
                      await deleteCandidate({ id: c.id, jobId: job.id }).unwrap();
                      toggle(c.id, false);
                    } catch (e) {
                      toast.error(getErrorMessage(e as never));
                    }
                  }}
                />
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <AddCandidateDialog jobId={job.id} open={addOpen} onOpenChange={setAddOpen} />
      <ImportCsvDialog jobId={job.id} open={csvOpen} onOpenChange={setCsvOpen} />
      <LaunchCallsDialog
        open={launchOpen}
        onOpenChange={setLaunchOpen}
        jobId={job.id}
        defaultAgentId={job.agentId}
        candidates={selectedCandidates}
        onLaunched={() => {
          setSelected(new Set());
          onLaunched();
        }}
      />
    </div>
  );
}

function CandidateRow({
  candidate: c,
  checked,
  onCheck,
  realDial,
  onToggleRealDial,
  onDelete,
}: {
  candidate: Candidate;
  checked: boolean;
  onCheck: (on: boolean) => void;
  realDial: boolean;
  onToggleRealDial: (on: boolean) => void;
  onDelete: () => void;
}) {
  return (
    <TableRow>
      <TableCell>
        <Checkbox
          aria-label={`Select ${c.name}`}
          checked={checked}
          onCheckedChange={(on) => onCheck(on)}
        />
      </TableCell>
      <TableCell>
        <div className="font-medium">{c.name}</div>
        <div className="text-muted-foreground text-xs">
          {[c.location, c.email].filter(Boolean).join(" · ")}
        </div>
      </TableCell>
      <TableCell className="text-sm">
        <div>{c.currentTitle ?? "—"}</div>
        <div className="text-muted-foreground text-xs">{c.currentCompany ?? ""}</div>
      </TableCell>
      <TableCell className="text-xs">
        {c.phone ? maskPhone(c.phone) : <span className="text-muted-foreground">none</span>}
      </TableCell>
      <TableCell>
        <Badge variant="outline">{SOURCE_LABEL[c.source] ?? c.source}</Badge>
      </TableCell>
      <TableCell>
        <StatusBadge status={c.latestCallStatus} />
      </TableCell>
      {realDial && (
        <TableCell>
          <Switch
            aria-label={`Allow real dial for ${c.name}`}
            checked={c.allowRealDial}
            disabled={!c.phone}
            onCheckedChange={(on) => onToggleRealDial(on)}
          />
        </TableCell>
      )}
      <TableCell>
        <Button variant="ghost" size="icon-xs" aria-label={`Remove ${c.name}`} onClick={onDelete}>
          <Trash2 />
        </Button>
      </TableCell>
    </TableRow>
  );
}

function CallsTab({ job }: { job: Job }) {
  const callsPoll = useLiveInterval(8000);
  const { data, error, isLoading, refetch } = useGetCallsQuery(
    { jobId: job.id, pageSize: 100 },
    { pollingInterval: callsPoll },
  );
  const [selected, setSelected] = useState<string | null>(null);
  if (isLoading) return <TableSkeleton />;
  if (error) return <ErrorState error={error} onRetry={() => void refetch()} />;
  const calls = data?.items ?? [];
  const ranked = [...calls].sort(
    (a, b) => (b.assessment?.fitScore ?? -1) - (a.assessment?.fitScore ?? -1),
  );
  return (
    <div className="space-y-3">
      {calls.length === 0 ? (
        <EmptyState
          icon={<PhoneOutgoing className="size-5" />}
          title="No calls for this job"
          description="Select candidates in the Candidates tab and start calls. Results refresh automatically."
        />
      ) : (
        <>
          <p className="text-muted-foreground text-xs">
            Ranked by fit score. Click a row for the recording, answers and timeline.
          </p>
          <CallsTable calls={ranked} onSelect={setSelected} />
        </>
      )}
      <CallDetailSheet callId={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
