export type CallStatus =
  | "NOT_STARTED"
  | "SCHEDULED"
  | "INITIATED"
  | "RINGING"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "NOT_CONNECTED"
  | "CANCELLED"
  | "FAILED";

export type LifecycleStatus =
  "NOT_STARTED" | "IN_PROGRESS" | "NOT_CONNECTED" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface CallEvent {
  at: string;
  kind: string;
  status: string | null;
  source: string;
  note: string | null;
}

export interface Transcript {
  language: string;
  turns: { speaker: string; text: string }[];
  text: string;
}

export interface Assessment {
  fitScore: number;
  recommendation: string;
  headline: string;
  strengths: string[];
  concerns: string[];
  nextStep: string;
}

export interface Call {
  id: string;
  hunarCallId: string;
  requestId: string | null;
  jobId: string;
  candidateId: string;
  agentId: string;
  hunarAgentId: string;
  calleeName: string;
  targetNumber: string | null;
  dialedNumber: string;
  safeDial: boolean;
  customData: Record<string, string>;
  status: CallStatus;
  lifecycleStatus: LifecycleStatus;
  engagementStatus: string | null;
  answeredBy: string | null;
  callEndedBy: string | null;
  durationSeconds: number | null;
  userSpeechDuration: number | null;
  recordingUrl: string | null;
  result: Record<string, unknown>;
  transcript: Transcript | null;
  assessment: Assessment | null;
  retryCount: number | null;
  retriesLeft: number | null;
  nextRetryScheduledAt: string | null;
  startedAt: string | null;
  endedAt: string | null;
  lastSyncedAt: string | null;
  events: CallEvent[];
  createdAt: string;
  updatedAt: string;
}

export interface LaunchCallsInput {
  jobId: string;
  candidateIds: string[];
  agentId?: string | null;
  guardrails?: { allowedDays: string[]; earliestCallTime: string; lastCallTime: string };
  retry?: { maxRetryCount: number; retryIntervalHours: number };
}

export interface LaunchCallsResult {
  calls: Call[];
  skipped: { candidateId: string; reason: string }[];
}

export interface ListCallsQuery {
  jobId?: string;
  candidateId?: string;
  status?: CallStatus[];
  page?: number;
  pageSize?: number;
}

export interface DashboardSummary {
  jobs: number;
  agents: number;
  candidates: number;
  callsTotal: number;
  callsByStatus: Record<string, number>;
  callsByLifecycle: Record<string, number>;
  engaged: number;
  completed: number;
  pending: number;
  avgDurationSeconds: number | null;
  recommendationCounts: Record<string, number>;
  recentCalls: Call[];
}
