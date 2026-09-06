"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { AgentForm, type AgentFormOutput } from "@/components/agents/agent-form";
import { PageHeader } from "@/components/page-header";
import { ErrorState, PageSkeleton } from "@/components/states";
import {
  useDeleteAgentMutation,
  useGetAgentQuery,
  useUpdateAgentMutation,
} from "@/features/agents/api";
import { getErrorMessage } from "@/lib/errors";

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: agent, error, isLoading, refetch } = useGetAgentQuery(id);
  const [updateAgent, updateState] = useUpdateAgentMutation();
  const [deleteAgent] = useDeleteAgentMutation();
  const [confirmDelete, setConfirmDelete] = useState(false);

  if (isLoading) return <PageSkeleton />;
  if (error || !agent) return <ErrorState error={error} onRetry={() => void refetch()} />;

  const submit = async (values: AgentFormOutput) => {
    try {
      await updateAgent({ id: agent.id, ...values }).unwrap();
      toast.success("Agent updated on Hunar");
    } catch (e) {
      toast.error(getErrorMessage(e as never));
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={
          <Link href="/agents" className="hover:underline">
            Voice agents
          </Link>
        }
        title={agent.name}
        description={`${agent.voicePersona} · ${agent.language} · code ${agent.agentCode ?? "—"} · hunar id ${agent.hunarAgentId}`}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => void refetch()}>
              <RefreshCw data-icon="inline-start" /> Reload
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive"
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 data-icon="inline-start" /> Remove
            </Button>
            <ConfirmDialog
              open={confirmDelete}
              onOpenChange={setConfirmDelete}
              title="Remove this agent?"
              description="It is removed from the app only. Hunar has no delete, so the agent itself stays there."
              confirmLabel="Remove agent"
              pendingLabel="Removing…"
              onConfirm={async () => {
                await deleteAgent(agent.id).unwrap();
                router.push("/agents");
              }}
            />
          </>
        }
      />
      <Card>
        <CardHeader>
          <CardTitle>Prompts and schema</CardTitle>
          <CardDescription>
            Changes are pushed to Hunar and apply to new calls only.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AgentForm
            initial={{
              name: agent.name,
              personaName: agent.personaName ?? agent.voicePersona,
              voicePersona: agent.voicePersona,
              language: agent.language,
              introduction: agent.introduction,
              objective: agent.objective,
              agentPrompt: agent.agentPrompt,
              resultPrompt: agent.resultPrompt ?? "",
              resultSchema: agent.resultSchema,
            }}
            onSubmit={submit}
            submitLabel="Save to Hunar"
            busy={updateState.isLoading}
          />
        </CardContent>
      </Card>
    </div>
  );
}
