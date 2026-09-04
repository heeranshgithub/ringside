import { api } from "@/lib/api";
import type { Page, AppConfig } from "@/types/common";
import type {
  Call,
  DashboardSummary,
  LaunchCallsInput,
  LaunchCallsResult,
  ListCallsQuery,
} from "@/types/call";

const callTags = (calls: Call[] | undefined) => [
  ...(calls ?? []).map(({ id }) => ({ type: "Call" as const, id })),
  { type: "Call" as const, id: "LIST" },
];

export const callsApi = api.injectEndpoints({
  endpoints: (build) => ({
    getCalls: build.query<Page<Call>, ListCallsQuery | void>({
      query: (q) => ({
        url: "/calls",
        params: {
          jobId: q?.jobId,
          candidateId: q?.candidateId,
          status: q?.status,
          page: q?.page ?? 1,
          pageSize: q?.pageSize ?? 20,
        },
      }),
      providesTags: (result) => callTags(result?.items),
    }),
    getCall: build.query<Call, string>({
      query: (id) => `/calls/${id}`,
      providesTags: (_r, _e, id) => [{ type: "Call", id }],
    }),
    launchCalls: build.mutation<LaunchCallsResult, LaunchCallsInput>({
      query: (body) => ({ url: "/calls/launch", method: "POST", body }),
      invalidatesTags: (_r, _e, arg) => [
        { type: "Call", id: "LIST" },
        { type: "Candidate", id: "LIST" },
        { type: "Job", id: arg.jobId },
        "Dashboard",
      ],
    }),
    syncAllCalls: build.mutation<{ synced: number; errors: number }, void>({
      query: () => ({ url: "/calls/sync", method: "POST" }),
      invalidatesTags: [
        { type: "Call", id: "LIST" },
        { type: "Candidate", id: "LIST" },
        "Dashboard",
      ],
    }),
    syncCall: build.mutation<Call, string>({
      query: (id) => ({ url: `/calls/${id}/sync`, method: "POST" }),
      invalidatesTags: (_r, _e, id) => [
        { type: "Call", id },
        { type: "Call", id: "LIST" },
        "Dashboard",
      ],
    }),
    assessCall: build.mutation<Call, string>({
      query: (id) => ({ url: `/calls/${id}/assess`, method: "POST" }),
      invalidatesTags: (_r, _e, id) => [
        { type: "Call", id },
        { type: "Call", id: "LIST" },
      ],
    }),
    transcribeCall: build.mutation<Call, string>({
      query: (id) => ({ url: `/calls/${id}/transcribe`, method: "POST" }),
      invalidatesTags: (_r, _e, id) => [
        { type: "Call", id },
        { type: "Call", id: "LIST" },
      ],
    }),
    getDashboard: build.query<DashboardSummary, void>({
      query: () => "/dashboard/summary",
      providesTags: ["Dashboard"],
    }),
    getConfig: build.query<AppConfig, void>({
      query: () => "/config",
      providesTags: ["Config"],
    }),
  }),
});

export const {
  useGetCallsQuery,
  useGetCallQuery,
  useLaunchCallsMutation,
  useSyncAllCallsMutation,
  useSyncCallMutation,
  useAssessCallMutation,
  useTranscribeCallMutation,
  useGetDashboardQuery,
  useGetConfigQuery,
} = callsApi;
