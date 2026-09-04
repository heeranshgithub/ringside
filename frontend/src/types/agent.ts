export type ResultSchema = Record<string, unknown>;

export interface Agent {
  id: string;
  hunarAgentId: string;
  agentCode: string | null;
  name: string;
  language: string;
  voicePersona: string;
  personaName: string | null;
  introduction: string;
  objective: string;
  agentPrompt: string;
  resultPrompt: string | null;
  resultSchema: ResultSchema;
  customVariables: string[];
  jobId: string | null;
  status: string;
  source: string;
  createdAt: string;
  updatedAt: string;
}

export interface AgentDraft {
  name: string;
  personaName: string;
  voicePersona: string;
  language: string;
  introduction: string;
  objective: string;
  agentPrompt: string;
  resultPrompt: string;
  resultSchema: ResultSchema;
  llmUsed: boolean;
}

export interface CreateAgentInput {
  jobId?: string | null;
  name: string;
  language: string;
  voicePersona: string;
  personaName?: string | null;
  introduction: string;
  objective: string;
  agentPrompt: string;
  resultPrompt: string;
  resultSchema: ResultSchema;
  source?: string;
}

export interface UpdateAgentInput {
  id: string;
  name?: string;
  language?: string;
  voicePersona?: string;
  personaName?: string | null;
  introduction?: string;
  objective?: string;
  agentPrompt?: string;
  resultPrompt?: string;
  resultSchema?: ResultSchema;
  jobId?: string | null;
}

export interface AgentOptions {
  voicePersonas: string[];
  languages: string[];
}
