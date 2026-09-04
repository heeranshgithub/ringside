"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useMemo } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Field } from "@/components/field";
import { useGetAgentOptionsQuery } from "@/features/agents/api";
import type { AgentDraft, ResultSchema } from "@/types/agent";

const schema = z.object({
  name: z.string().min(3, "At least 3 characters").max(64, "At most 64 characters"),
  personaName: z.string().min(3, "At least 3 characters").max(64),
  voicePersona: z.string().min(1, "Pick a voice"),
  language: z.string().min(1, "Pick a language"),
  introduction: z.string().min(3, "Required"),
  objective: z.string().min(3, "Required"),
  agentPrompt: z.string().min(20, "Write a real prompt"),
  resultPrompt: z.string().min(3, "Required"),
  resultSchemaText: z.string().refine(
    (t) => {
      try {
        const v: unknown = JSON.parse(t);
        return (
          typeof v === "object" && v !== null && !Array.isArray(v) && Object.keys(v).length > 0
        );
      } catch {
        return false;
      }
    },
    { message: "Must be a non-empty JSON object" },
  ),
});

export type AgentFormValues = z.infer<typeof schema>;

export interface AgentFormOutput {
  name: string;
  personaName: string;
  voicePersona: string;
  language: string;
  introduction: string;
  objective: string;
  agentPrompt: string;
  resultPrompt: string;
  resultSchema: ResultSchema;
}

const VAR_RE = /{(\w+)}/g;
const SUPPORTED = ["persona_name", "candidate_name", "job_role", "company", "location"];

export function extractVars(...texts: string[]): string[] {
  const found = new Set<string>();
  for (const t of texts) for (const m of t.matchAll(VAR_RE)) if (m[1]) found.add(m[1]);
  return [...found];
}

export function AgentForm({
  initial,
  onSubmit,
  submitLabel,
  busy,
}: {
  initial?: Partial<AgentDraft> & { resultSchema?: ResultSchema };
  onSubmit: (values: AgentFormOutput) => void | Promise<void>;
  submitLabel: string;
  busy?: boolean;
}) {
  const { data: options } = useGetAgentOptionsQuery();
  const form = useForm<AgentFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: initial?.name ?? "",
      personaName: initial?.personaName ?? "Neha",
      voicePersona: initial?.voicePersona ?? "NEHA",
      language: initial?.language ?? "ENGLISH",
      introduction: initial?.introduction ?? "",
      objective: initial?.objective ?? "",
      agentPrompt: initial?.agentPrompt ?? "",
      resultPrompt: initial?.resultPrompt ?? "",
      resultSchemaText: JSON.stringify(
        initial?.resultSchema ?? {
          summary: "string",
          interested: "boolean",
          recommendation: "string",
        },
        null,
        2,
      ),
    },
  });

  useEffect(() => {
    if (initial) {
      form.reset({
        name: initial.name ?? "",
        personaName: initial.personaName ?? "Neha",
        voicePersona: initial.voicePersona ?? "NEHA",
        language: initial.language ?? "ENGLISH",
        introduction: initial.introduction ?? "",
        objective: initial.objective ?? "",
        agentPrompt: initial.agentPrompt ?? "",
        resultPrompt: initial.resultPrompt ?? "",
        resultSchemaText: JSON.stringify(initial.resultSchema ?? {}, null, 2),
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset only when a new draft arrives
  }, [initial]);

  const watched = useWatch({
    control: form.control,
    name: ["introduction", "objective", "agentPrompt"],
  });
  const vars = useMemo(() => extractVars(...watched.map((w) => w ?? "")), [watched]);
  const unsupported = vars.filter((v) => !SUPPORTED.includes(v));
  const { errors } = form.formState;

  return (
    <form
      className="space-y-5"
      onSubmit={form.handleSubmit((v) =>
        onSubmit({
          name: v.name,
          personaName: v.personaName,
          voicePersona: v.voicePersona,
          language: v.language,
          introduction: v.introduction,
          objective: v.objective,
          agentPrompt: v.agentPrompt,
          resultPrompt: v.resultPrompt,
          resultSchema: JSON.parse(v.resultSchemaText) as ResultSchema,
        }),
      )}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Agent name" htmlFor="agent-name" error={errors.name?.message}>
          <Input id="agent-name" {...form.register("name")} />
        </Field>
        <Field
          label="Persona name (how it introduces itself)"
          htmlFor="agent-persona-name"
          error={errors.personaName?.message}
        >
          <Input id="agent-persona-name" {...form.register("personaName")} />
        </Field>
        <Controller
          control={form.control}
          name="voicePersona"
          render={({ field }) => (
            <Field label="Voice" htmlFor="agent-voice" error={errors.voicePersona?.message}>
              <Select value={field.value} onValueChange={(v) => field.onChange(v ?? "")}>
                <SelectTrigger id="agent-voice" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(options?.voicePersonas ?? ["NEHA", "ROY", "ZOE", "SAM", "MIRA", "EESHA"]).map(
                    (v) => (
                      <SelectItem key={v} value={v}>
                        {v}
                      </SelectItem>
                    ),
                  )}
                </SelectContent>
              </Select>
            </Field>
          )}
        />
        <Controller
          control={form.control}
          name="language"
          render={({ field }) => (
            <Field label="Language" htmlFor="agent-language" error={errors.language?.message}>
              <Select value={field.value} onValueChange={(v) => field.onChange(v ?? "")}>
                <SelectTrigger id="agent-language" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(options?.languages ?? ["ENGLISH", "HINDI"]).map((v) => (
                    <SelectItem key={v} value={v}>
                      {v}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          )}
        />
      </div>

      <Field
        label="Introduction (first thing the agent says)"
        htmlFor="agent-intro"
        error={errors.introduction?.message}
      >
        <Textarea id="agent-intro" rows={2} {...form.register("introduction")} />
      </Field>
      <Field label="Objective" htmlFor="agent-objective" error={errors.objective?.message}>
        <Textarea id="agent-objective" rows={2} {...form.register("objective")} />
      </Field>
      <Field
        label="Agent prompt"
        htmlFor="agent-prompt"
        error={errors.agentPrompt?.message}
        hint={
          <span>
            Variables detected:{" "}
            {vars.length
              ? vars.map((v) => <code key={v} className="mr-1">{`{${v}}`}</code>)
              : "none"}
            {unsupported.length > 0 && (
              <span className="text-amber-700 dark:text-amber-300">
                {" "}
                · unsupported: {unsupported.join(", ")} (only {SUPPORTED.join(", ")} are filled
                automatically)
              </span>
            )}
          </span>
        }
      >
        <Textarea
          id="agent-prompt"
          rows={10}
          className="font-mono text-xs"
          {...form.register("agentPrompt")}
        />
      </Field>
      <div className="grid gap-4 lg:grid-cols-2">
        <Field
          label="Result prompt (how to extract answers)"
          htmlFor="agent-result-prompt"
          error={errors.resultPrompt?.message}
        >
          <Textarea
            id="agent-result-prompt"
            rows={8}
            className="font-mono text-xs"
            {...form.register("resultPrompt")}
          />
        </Field>
        <Field
          label="Result schema (JSON: field → type)"
          htmlFor="agent-result-schema"
          error={errors.resultSchemaText?.message}
          hint='Flat object, e.g. {"summary": "string", "interested": "boolean"}'
        >
          <Textarea
            id="agent-result-schema"
            rows={8}
            className="font-mono text-xs"
            {...form.register("resultSchemaText")}
          />
        </Field>
      </div>
      <div className="flex justify-end">
        <Button type="submit" disabled={busy}>
          {busy ? "Saving…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
