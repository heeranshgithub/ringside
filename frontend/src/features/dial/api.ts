import { api } from "@/lib/api";
import type {
  ConfirmVerificationInput,
  DialCapability,
  DialTarget,
  StartVerificationInput,
} from "@/types/dial";

export const dialApi = api.injectEndpoints({
  endpoints: (build) => ({
    getDialCapability: build.query<DialCapability, void>({
      query: () => "/dial-target",
      providesTags: [{ type: "DialTarget", id: "CAPABILITY" }],
    }),
    getDialTarget: build.query<DialTarget | null, void>({
      query: () => "/dial-target/current",
      providesTags: [{ type: "DialTarget", id: "CURRENT" }],
    }),
    startVerification: build.mutation<DialTarget, StartVerificationInput>({
      query: (body) => ({ url: "/dial-target/start", method: "POST", body }),
      invalidatesTags: [{ type: "DialTarget", id: "CAPABILITY" }],
    }),
    confirmVerification: build.mutation<DialTarget, ConfirmVerificationInput>({
      query: ({ id, code }) => ({
        url: `/dial-target/${id}/confirm`,
        method: "POST",
        body: { code },
      }),
      invalidatesTags: [{ type: "DialTarget", id: "CURRENT" }, "Config"],
    }),
    releaseDialTarget: build.mutation<void, void>({
      query: () => ({ url: "/dial-target", method: "DELETE" }),
      invalidatesTags: [{ type: "DialTarget", id: "CURRENT" }],
    }),
  }),
});

export const {
  useGetDialCapabilityQuery,
  useGetDialTargetQuery,
  useStartVerificationMutation,
  useConfirmVerificationMutation,
  useReleaseDialTargetMutation,
} = dialApi;
