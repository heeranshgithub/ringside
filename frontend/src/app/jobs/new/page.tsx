"use client";

import { useRouter } from "next/navigation";
import { Sparkles, Wand2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ChipsInput } from "@/components/chips-input";
import { CapabilityNotice } from "@/components/capability-notice";
import { Field } from "@/components/field";
import { PageHeader } from "@/components/page-header";
import { useGetConfigQuery } from "@/features/calls/api";
import { useCreateJobMutation, useParseJobMutation } from "@/features/jobs/api";
import { getErrorMessage } from "@/lib/errors";
import type { ParsedJob, SearchCriteria } from "@/types/job";

const SAMPLE_JD = `Senior Frontend Engineer (Next.js) — Northline Labs, Bengaluru

We are hiring a Senior Frontend Engineer to own our recruiter-facing dashboard. You will work with React 19, Next.js App Router, TypeScript and Tailwind, partnering with a Python backend team.

Must have: 5+ years building production React apps, strong TypeScript, experience with data-heavy UIs and state management (Redux Toolkit or similar), and comfort owning features end to end.
Nice to have: Playwright, design-system experience, prior startup experience.

Hybrid (3 days in office, Bengaluru). CTC 30–45 LPA. Immediate joiners preferred; notice period up to 60 days acceptable.`;

const emptyCriteria: SearchCriteria = {
  titles: [],
  locations: [],
  skills: [],
  seniorities: [],
  keywords: "",
};

export default function NewJobPage() {
  const router = useRouter();
  const { data: config } = useGetConfigQuery();
  const [parse, parseState] = useParseJobMutation();
  const [create, createState] = useCreateJobMutation();
  const [description, setDescription] = useState("");
  const [parsed, setParsed] = useState<ParsedJob | null>(null);
  const [form, setForm] = useState({
    title: "",
    company: "",
    location: "",
    seniority: "",
    employmentType: "",
    salaryRange: "",
    summary: "",
    mustHaves: [] as string[],
    niceToHaves: [] as string[],
    questionsText: "",
    criteria: emptyCriteria,
  });

  const analyse = async () => {
    try {
      const p = await parse({ description }).unwrap();
      setParsed(p);
      setForm({
        title: p.title,
        company: p.company ?? "",
        location: p.location ?? "",
        seniority: p.seniority ?? "",
        employmentType: p.employmentType ?? "",
        salaryRange: p.salaryRange ?? "",
        summary: p.summary,
        mustHaves: p.mustHaves,
        niceToHaves: p.niceToHaves,
        questionsText: p.screeningQuestions.join("\n"),
        criteria: p.searchCriteria,
      });
      toast.success(p.llmUsed ? "Analysed with the LLM" : "Analysed with the rule-based parser");
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  };

  const submit = async () => {
    try {
      const job = await create({
        title: form.title.trim(),
        company: form.company.trim() || null,
        location: form.location.trim() || null,
        description,
        employmentType: form.employmentType.trim() || null,
        seniority: form.seniority.trim() || null,
        salaryRange: form.salaryRange.trim() || null,
        summary: form.summary,
        mustHaves: form.mustHaves,
        niceToHaves: form.niceToHaves,
        screeningQuestions: form.questionsText
          .split("\n")
          .map((q) => q.trim())
          .filter(Boolean),
        searchCriteria: form.criteria,
      }).unwrap();
      toast.success("Job created");
      router.push(`/jobs/${job.id}?tab=agent`);
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  };

  const canCreate = form.title.trim().length >= 2 && description.trim().length >= 20;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Step 1 of 3"
        title="New job"
        description="Paste the job description. The assistant extracts the essentials, drafts screening questions and builds people-search criteria."
      />
      <CapabilityNotice capability="llm" />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>Job description</CardTitle>
            <CardDescription>
              {config?.llmEnabled
                ? `Analysed with ${config.llmModel} via OpenRouter.`
                : "No LLM key configured: a rule-based parser will be used."}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              aria-label="Job description"
              rows={18}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Paste the full job description here…"
            />
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={analyse}
                disabled={parseState.isLoading || description.trim().length < 20}
              >
                <Sparkles
                  data-icon="inline-start"
                  className={parseState.isLoading ? "animate-pulse" : ""}
                />
                {parseState.isLoading ? "Analysing…" : "Analyse"}
              </Button>
              <Button variant="outline" onClick={() => setDescription(SAMPLE_JD)}>
                <Wand2 data-icon="inline-start" /> Use sample JD
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Extracted details</CardTitle>
            <CardDescription>
              {parseState.isLoading
                ? "Analysing… these fields are locked until it finishes."
                : parsed
                  ? "Review and edit before creating the job."
                  : "Fill these in manually or analyse the description first."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/*
              The analysis overwrites every field in here, so anything typed while it is in
              flight would be silently thrown away. A fieldset disables the whole group at
              once — chip inputs and the submit button included — rather than threading a
              `disabled` prop through a dozen controls.
            */}
            <fieldset disabled={parseState.isLoading} className="group min-w-0 space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="Title" htmlFor="job-title" className="sm:col-span-2">
                  <Input
                    id="job-title"
                    value={form.title}
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                  />
                </Field>
                <Field label="Company" htmlFor="job-company">
                  <Input
                    id="job-company"
                    value={form.company}
                    onChange={(e) => setForm({ ...form, company: e.target.value })}
                  />
                </Field>
                <Field label="Location" htmlFor="job-location">
                  <Input
                    id="job-location"
                    value={form.location}
                    onChange={(e) => setForm({ ...form, location: e.target.value })}
                  />
                </Field>
                <Field label="Seniority" htmlFor="job-seniority">
                  <Input
                    id="job-seniority"
                    value={form.seniority}
                    onChange={(e) => setForm({ ...form, seniority: e.target.value })}
                  />
                </Field>
                <Field label="Salary range" htmlFor="job-salary">
                  <Input
                    id="job-salary"
                    value={form.salaryRange}
                    onChange={(e) => setForm({ ...form, salaryRange: e.target.value })}
                  />
                </Field>
              </div>
              <Field label="Summary" htmlFor="job-summary">
                <Textarea
                  id="job-summary"
                  rows={2}
                  value={form.summary}
                  onChange={(e) => setForm({ ...form, summary: e.target.value })}
                />
              </Field>
              <Field label="Must-haves" htmlFor="job-must">
                <ChipsInput
                  id="job-must"
                  value={form.mustHaves}
                  onChange={(mustHaves) => setForm({ ...form, mustHaves })}
                  placeholder="Add a requirement and press Enter"
                />
              </Field>
              <Field label="Nice-to-haves" htmlFor="job-nice">
                <ChipsInput
                  id="job-nice"
                  value={form.niceToHaves}
                  onChange={(niceToHaves) => setForm({ ...form, niceToHaves })}
                  placeholder="Optional"
                />
              </Field>
              <Field
                label="Screening questions (one per line)"
                htmlFor="job-questions"
                hint="These become the voice agent's script."
              >
                <Textarea
                  id="job-questions"
                  rows={6}
                  value={form.questionsText}
                  onChange={(e) => setForm({ ...form, questionsText: e.target.value })}
                />
              </Field>
              <div className="space-y-3 rounded-lg border p-3">
                <p className="text-sm font-medium">People-search criteria</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Field label="Titles" htmlFor="crit-titles">
                    <ChipsInput
                      id="crit-titles"
                      value={form.criteria.titles}
                      onChange={(titles) =>
                        setForm({ ...form, criteria: { ...form.criteria, titles } })
                      }
                      placeholder="Frontend Engineer"
                    />
                  </Field>
                  <Field label="Locations" htmlFor="crit-locations">
                    <ChipsInput
                      id="crit-locations"
                      value={form.criteria.locations}
                      onChange={(locations) =>
                        setForm({ ...form, criteria: { ...form.criteria, locations } })
                      }
                      placeholder="Bengaluru"
                    />
                  </Field>
                  <Field label="Skills" htmlFor="crit-skills">
                    <ChipsInput
                      id="crit-skills"
                      value={form.criteria.skills}
                      onChange={(skills) =>
                        setForm({ ...form, criteria: { ...form.criteria, skills } })
                      }
                      placeholder="react"
                    />
                  </Field>
                  <Field label="Keywords" htmlFor="crit-keywords">
                    <Input
                      id="crit-keywords"
                      value={form.criteria.keywords}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          criteria: { ...form.criteria, keywords: e.target.value },
                        })
                      }
                    />
                  </Field>
                </div>
              </div>
              <div className="flex justify-end">
                <Button onClick={submit} disabled={!canCreate || createState.isLoading}>
                  {createState.isLoading ? "Creating…" : "Create job"}
                </Button>
              </div>
            </fieldset>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
