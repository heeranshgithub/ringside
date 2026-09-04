"use client";

import Link from "next/link";
import { ArrowRight, Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PeopleSearchPanel } from "@/components/candidates/people-search-panel";
import { Field } from "@/components/field";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/states";
import { useGetJobsQuery } from "@/features/jobs/api";

export default function SearchPage() {
  const { data: jobs, error, isLoading, refetch } = useGetJobsQuery();
  const [jobId, setJobId] = useState<string>("");
  const [imported, setImported] = useState(0);
  const job = jobs?.find((j) => j.id === jobId) ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="People search & reach-out"
        title="Find people, then let the agent call them"
        description="Pick a job (its description was already turned into search criteria), search a provider, add matches as candidates, then start calls. Answers show up on the job's Calls tab."
        actions={
          <Button variant="outline" nativeButton={false} render={<Link href="/jobs/new" />}>
            <Plus data-icon="inline-start" /> New job from a JD
          </Button>
        }
      />
      {isLoading && <TableSkeleton rows={2} />}
      {error && <ErrorState error={error} onRetry={() => void refetch()} />}
      {jobs && jobs.length === 0 && (
        <EmptyState
          title="Create a job first"
          description="The search criteria come from a job description. Paste one and the assistant extracts titles, locations and skills."
          action={
            <Button nativeButton={false} render={<Link href="/jobs/new" />}>
              <Plus data-icon="inline-start" /> New job
            </Button>
          }
        />
      )}
      {jobs && jobs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>1 · Choose the job</CardTitle>
            <CardDescription>
              Search criteria and the calling agent come from this job.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Field label="Job" htmlFor="search-job">
              <Select value={jobId} onValueChange={(v) => setJobId(v ?? "")}>
                <SelectTrigger id="search-job" className="w-full sm:w-96">
                  <SelectValue placeholder="Select a job" />
                </SelectTrigger>
                <SelectContent>
                  {jobs.map((j) => (
                    <SelectItem key={j.id} value={j.id}>
                      {j.title}
                      {j.company ? ` · ${j.company}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          </CardContent>
        </Card>
      )}
      {job && (
        <Card>
          <CardHeader>
            <CardTitle>2 · Search and add candidates</CardTitle>
            <CardDescription>
              {job.agentId
                ? "This job already has a voice agent."
                : "This job has no agent yet; you can create one on the job page before calling."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <PeopleSearchPanel
              key={job.id}
              jobId={job.id}
              initialCriteria={job.searchCriteria}
              onImported={(n) => setImported((c) => c + n)}
            />
          </CardContent>
        </Card>
      )}
      {job && imported > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>3 · Reach out</CardTitle>
            <CardDescription>
              {imported} candidate{imported === 1 ? "" : "s"} added. Select them on the job page and
              start calls.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              nativeButton={false}
              render={<Link href={`/jobs/${job.id}?tab=${job.agentId ? "candidates" : "agent"}`} />}
            >
              Go to {job.agentId ? "candidates" : "agent setup"}{" "}
              <ArrowRight data-icon="inline-end" />
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
