import { api } from "@/lib/api";
import type { CreateJobInput, Job, ParsedJob, ParseJobInput, UpdateJobInput } from "@/types/job";

export const jobsApi = api.injectEndpoints({
  endpoints: (build) => ({
    parseJob: build.mutation<ParsedJob, ParseJobInput>({
      query: (body) => ({ url: "/jobs/parse", method: "POST", body }),
    }),
    getJobs: build.query<Job[], void>({
      query: () => "/jobs",
      providesTags: (result) => [
        ...(result ?? []).map(({ id }) => ({ type: "Job" as const, id })),
        { type: "Job", id: "LIST" },
      ],
    }),
    getJob: build.query<Job, string>({
      query: (id) => `/jobs/${id}`,
      providesTags: (_r, _e, id) => [{ type: "Job", id }],
    }),
    createJob: build.mutation<Job, CreateJobInput>({
      query: (body) => ({ url: "/jobs", method: "POST", body }),
      invalidatesTags: [{ type: "Job", id: "LIST" }, "Dashboard"],
    }),
    updateJob: build.mutation<Job, UpdateJobInput>({
      query: ({ id, ...body }) => ({ url: `/jobs/${id}`, method: "PATCH", body }),
      invalidatesTags: (_r, _e, arg) => [
        { type: "Job", id: arg.id },
        { type: "Job", id: "LIST" },
      ],
    }),
    deleteJob: build.mutation<void, string>({
      query: (id) => ({ url: `/jobs/${id}`, method: "DELETE" }),
      invalidatesTags: [{ type: "Job", id: "LIST" }, "Dashboard", { type: "Call", id: "LIST" }],
    }),
  }),
});

export const {
  useParseJobMutation,
  useGetJobsQuery,
  useGetJobQuery,
  useCreateJobMutation,
  useUpdateJobMutation,
  useDeleteJobMutation,
} = jobsApi;
