import { api } from "@/lib/api";
import type {
  Candidate,
  CreateCandidateInput,
  ImportCsvInput,
  ImportCsvResult,
  ImportPeopleInput,
  ProviderInfo,
  SearchPeopleInput,
  SearchPeopleResult,
  UpdateCandidateInput,
} from "@/types/candidate";

const candidateListTags = (jobId?: string) => [
  { type: "Candidate" as const, id: "LIST" },
  ...(jobId ? [{ type: "Job" as const, id: jobId }] : []),
];

export const candidatesApi = api.injectEndpoints({
  endpoints: (build) => ({
    getCandidates: build.query<Candidate[], { jobId?: string } | void>({
      query: (args) => ({
        url: "/candidates",
        params: args?.jobId ? { jobId: args.jobId } : undefined,
      }),
      providesTags: (result) => [
        ...(result ?? []).map(({ id }) => ({ type: "Candidate" as const, id })),
        { type: "Candidate", id: "LIST" },
      ],
    }),
    createCandidate: build.mutation<Candidate, CreateCandidateInput>({
      query: (body) => ({ url: "/candidates", method: "POST", body }),
      invalidatesTags: (_r, _e, arg) => [...candidateListTags(arg.jobId), "Dashboard"],
    }),
    importCsv: build.mutation<ImportCsvResult, ImportCsvInput>({
      query: (body) => ({ url: "/candidates/import-csv", method: "POST", body }),
      invalidatesTags: (_r, _e, arg) => [...candidateListTags(arg.jobId), "Dashboard"],
    }),
    updateCandidate: build.mutation<Candidate, UpdateCandidateInput>({
      query: ({ id, ...body }) => ({ url: `/candidates/${id}`, method: "PATCH", body }),
      invalidatesTags: (_r, _e, arg) => [{ type: "Candidate", id: arg.id }],
    }),
    deleteCandidate: build.mutation<void, { id: string; jobId: string }>({
      query: ({ id }) => ({ url: `/candidates/${id}`, method: "DELETE" }),
      invalidatesTags: (_r, _e, arg) => [...candidateListTags(arg.jobId), "Dashboard"],
    }),
    getProviders: build.query<ProviderInfo[], void>({
      query: () => "/search/providers",
    }),
    searchPeople: build.mutation<SearchPeopleResult, SearchPeopleInput>({
      query: (body) => ({ url: "/search/people", method: "POST", body }),
    }),
    importPeople: build.mutation<Candidate[], ImportPeopleInput>({
      query: (body) => ({ url: "/search/import", method: "POST", body }),
      invalidatesTags: (_r, _e, arg) => [...candidateListTags(arg.jobId), "Dashboard"],
    }),
  }),
});

export const {
  useGetCandidatesQuery,
  useCreateCandidateMutation,
  useImportCsvMutation,
  useUpdateCandidateMutation,
  useDeleteCandidateMutation,
  useGetProvidersQuery,
  useSearchPeopleMutation,
  useImportPeopleMutation,
} = candidatesApi;
