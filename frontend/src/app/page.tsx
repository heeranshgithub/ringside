"use client";

import Link from "next/link";
import { ArrowRight, BriefcaseBusiness, PhoneCall, RefreshCw, Search, Users } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CallDetailSheet } from "@/components/calls/call-detail-sheet";
import { CallsTable } from "@/components/calls/calls-table";
import { PageHeader } from "@/components/page-header";
import { EmptyState, ErrorState, PageSkeleton } from "@/components/states";
import { StatusBadge } from "@/components/status-badge";
import { useGetDashboardQuery, useSyncAllCallsMutation } from "@/features/calls/api";
import { useGetJobsQuery } from "@/features/jobs/api";
import { getErrorMessage } from "@/lib/errors";
import { formatDuration, titleCase } from "@/lib/format";

function Stat({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl tabular-nums">{value}</CardTitle>
      </CardHeader>
      {hint && <CardContent className="text-muted-foreground -mt-2 text-xs">{hint}</CardContent>}
    </Card>
  );
}

export default function DashboardPage() {
  const { data, error, isLoading, refetch } = useGetDashboardQuery(undefined, {
    pollingInterval: 15000,
  });
  const { data: jobs } = useGetJobsQuery();
  const [syncAll, syncState] = useSyncAllCallsMutation();
  const [selected, setSelected] = useState<string | null>(null);

  if (isLoading) return <PageSkeleton />;
  if (error || !data) return <ErrorState error={error} onRetry={() => void refetch()} />;

  const jobTitles = Object.fromEntries((jobs ?? []).map((j) => [j.id, j.title]));
  const engagedRate = data.completed ? Math.round((data.engaged / data.completed) * 100) : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Screen candidates and reach out to sourced talent with Hunar voice agents. Answers land here as structured data."
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              disabled={syncState.isLoading}
              onClick={async () => {
                try {
                  const r = await syncAll().unwrap();
                  toast.success(`Synced ${r.synced} call${r.synced === 1 ? "" : "s"}`);
                } catch (e) {
                  toast.error(getErrorMessage(e as never));
                }
              }}
            >
              <RefreshCw
                data-icon="inline-start"
                className={syncState.isLoading ? "animate-spin" : ""}
              />
              Sync pending
            </Button>
            <Button size="sm" nativeButton={false} render={<Link href="/jobs/new" />}>
              New job
              <ArrowRight data-icon="inline-end" />
            </Button>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label="Jobs"
          value={data.jobs}
          hint={`${data.agents} voice agent${data.agents === 1 ? "" : "s"}`}
        />
        <Stat label="Candidates" value={data.candidates} />
        <Stat
          label="Calls"
          value={data.callsTotal}
          hint={`${data.pending} pending · ${data.completed} completed`}
        />
        <Stat
          label="Engagement"
          value={`${engagedRate}%`}
          hint={
            data.avgDurationSeconds
              ? `avg ${formatDuration(data.avgDurationSeconds)} per completed call`
              : "no completed calls yet"
          }
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="grid content-start gap-3 sm:grid-cols-2 lg:col-span-2">
          {(
            [
              {
                href: "/jobs/new",
                icon: BriefcaseBusiness,
                title: "AI hiring assistant",
                body: "Paste a job description. We draft a screening agent, you add candidates, the agent calls and scores them.",
              },
              {
                href: "/search",
                icon: Search,
                title: "People search & reach-out",
                body: "Turn the job description into search criteria, pull profiles from Apollo, PDL or the demo dataset, and dial them.",
              },
            ] as const
          ).map(({ href, icon: Icon, title, body }) => (
            <Link
              key={href}
              href={href}
              className="border-border bg-card hover:border-tint/40 group flex flex-col rounded-xl border p-5 transition-colors"
            >
              <span
                className="text-tint mb-3 grid size-9 place-items-center rounded-lg"
                style={{ background: "color-mix(in oklab, var(--tint) 12%, transparent)" }}
              >
                <Icon className="size-4.5" />
              </span>
              <span className="text-[15px] font-semibold tracking-[-0.01em]">{title}</span>
              <p className="text-muted-foreground mt-1.5 text-[13px] leading-relaxed">{body}</p>
              <span className="text-muted-foreground group-hover:text-tint mt-auto flex items-center gap-1.5 pt-5 text-[13px] font-medium transition-colors">
                Start here
                <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
              </span>
            </Link>
          ))}
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Pipeline</CardTitle>
            <CardDescription>Calls by lifecycle and verdict</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="space-y-1.5">
              {Object.entries(data.callsByLifecycle).map(([k, v]) => (
                <div key={k} className="flex items-center justify-between">
                  <StatusBadge status={k} />
                  <span className="tabular-nums">{v}</span>
                </div>
              ))}
              {Object.keys(data.callsByLifecycle).length === 0 && (
                <p className="text-muted-foreground text-xs">No calls yet.</p>
              )}
            </div>
            {Object.keys(data.recommendationCounts).length > 0 && (
              <div className="border-t pt-3">
                {Object.entries(data.recommendationCounts).map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between py-0.5">
                    <span className="text-muted-foreground text-xs">{titleCase(k)}</span>
                    <span className="tabular-nums">{v}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-base font-semibold">
            <PhoneCall className="size-4" /> Recent calls
          </h2>
          <Button variant="ghost" size="sm" nativeButton={false} render={<Link href="/calls" />}>
            View all <ArrowRight data-icon="inline-end" />
          </Button>
        </div>
        {data.recentCalls.length === 0 ? (
          <EmptyState
            icon={<Users className="size-5" />}
            title="No calls yet"
            description="Create a job, add a candidate and start a call. With safe-dial on, it rings your own test number."
            action={
              <Button size="sm" nativeButton={false} render={<Link href="/jobs/new" />}>
                Create a job
              </Button>
            }
          />
        ) : (
          <CallsTable
            calls={data.recentCalls}
            onSelect={setSelected}
            showJob
            jobTitles={jobTitles}
          />
        )}
      </section>
      <CallDetailSheet callId={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
