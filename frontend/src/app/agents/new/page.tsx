"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AgentForm, type AgentFormOutput } from "@/components/agents/agent-form";
import { CapabilityNotice } from "@/components/capability-notice";
import { PageHeader } from "@/components/page-header";
import { useCreateAgentMutation } from "@/features/agents/api";
import { getErrorMessage } from "@/lib/errors";

const STARTER = {
  name: "Hiring Screener",
  personaName: "Neha",
  voicePersona: "NEHA",
  language: "ENGLISH",
  introduction:
    "Hi {candidate_name}, this is {persona_name} calling from the hiring team at {company} about the {job_role} role. Is this a good time for a two-minute chat?",
  objective:
    "Screen the candidate for the {job_role} role at {company} and collect structured hiring signals.",
  agentPrompt:
    "You are {persona_name}, a polite and efficient recruiting assistant for {company}. You are calling {candidate_name} about the {job_role} role based in {location}. Ask one question at a time, confirm key facts by repeating them, keep the call under four minutes and speak simply. If the candidate is busy or not interested, thank them and end the call politely.\n\nQuestions to cover:\n- Are you open to new opportunities right now?\n- How many years of relevant experience do you have?\n- Which city are you based in, and are you open to relocating to {location}?\n- What is your current and expected salary?\n- What is your notice period or earliest joining date?",
  resultPrompt:
    'From the conversation, extract a JSON object matching the schema. Use "unknown" when a fact was not discussed. recommendation must be hire_now, maybe, reject or unknown.',
  resultSchema: {
    summary: "string",
    interested: "boolean",
    years_experience: "string",
    current_location: "string",
    open_to_relocation: "boolean",
    current_ctc: "string",
    expected_ctc: "string",
    notice_period_days: "string",
    recommendation: "string",
  },
};

export default function NewAgentPage() {
  const router = useRouter();
  const [createAgent, { isLoading }] = useCreateAgentMutation();
  const submit = async (values: AgentFormOutput) => {
    try {
      const a = await createAgent({ ...values, source: "manual" }).unwrap();
      toast.success("Agent created on Hunar");
      router.push(`/agents/${a.id}`);
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  };
  return (
    <div className="space-y-6">
      <PageHeader
        title="New voice agent"
        description="Write the prompts by hand. Placeholders in braces are filled per call."
      />
      <CapabilityNotice capability="hunar" />
      <Card>
        <CardHeader>
          <CardTitle>Agent definition</CardTitle>
          <CardDescription>
            Supported placeholders: persona_name, candidate_name, job_role, company, location.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AgentForm
            initial={STARTER}
            onSubmit={submit}
            submitLabel="Create agent on Hunar"
            busy={isLoading}
          />
        </CardContent>
      </Card>
    </div>
  );
}
