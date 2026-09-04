import { api } from "@/lib/api";
import type {
  Agent,
  AgentDraft,
  AgentOptions,
  CreateAgentInput,
  UpdateAgentInput,
} from "@/types/agent";

export const agentsApi = api.injectEndpoints({
  endpoints: (build) => ({
    getAgentOptions: build.query<AgentOptions, void>({
      query: () => "/agents/options",
    }),
    draftAgent: build.mutation<AgentDraft, { jobId: string }>({
      query: (body) => ({ url: "/agents/draft", method: "POST", body }),
    }),
    getAgents: build.query<Agent[], { jobId?: string } | void>({
      query: (args) => ({
        url: "/agents",
        params: args?.jobId ? { jobId: args.jobId } : undefined,
      }),
      providesTags: (result) => [
        ...(result ?? []).map(({ id }) => ({ type: "Agent" as const, id })),
        { type: "Agent", id: "LIST" },
      ],
    }),
    getAgent: build.query<Agent, string>({
      query: (id) => `/agents/${id}`,
      providesTags: (_r, _e, id) => [{ type: "Agent", id }],
    }),
    createAgent: build.mutation<Agent, CreateAgentInput>({
      query: (body) => ({ url: "/agents", method: "POST", body }),
      invalidatesTags: (result) => [
        { type: "Agent", id: "LIST" },
        "Dashboard",
        ...(result?.jobId ? [{ type: "Job" as const, id: result.jobId }] : []),
      ],
    }),
    importAgent: build.mutation<Agent, { hunarAgentId: string; jobId?: string | null }>({
      query: (body) => ({ url: "/agents/import", method: "POST", body }),
      invalidatesTags: (result) => [
        { type: "Agent", id: "LIST" },
        ...(result?.jobId ? [{ type: "Job" as const, id: result.jobId }] : []),
      ],
    }),
    updateAgent: build.mutation<Agent, UpdateAgentInput>({
      query: ({ id, ...body }) => ({ url: `/agents/${id}`, method: "PATCH", body }),
      invalidatesTags: (result, _e, arg) => [
        { type: "Agent", id: arg.id },
        { type: "Agent", id: "LIST" },
        ...(result?.jobId ? [{ type: "Job" as const, id: result.jobId }] : []),
      ],
    }),
    deleteAgent: build.mutation<void, string>({
      query: (id) => ({ url: `/agents/${id}`, method: "DELETE" }),
      invalidatesTags: [
        { type: "Agent", id: "LIST" },
        { type: "Job", id: "LIST" },
      ],
    }),
  }),
});

export const {
  useGetAgentOptionsQuery,
  useDraftAgentMutation,
  useGetAgentsQuery,
  useGetAgentQuery,
  useCreateAgentMutation,
  useImportAgentMutation,
  useUpdateAgentMutation,
  useDeleteAgentMutation,
} = agentsApi;
