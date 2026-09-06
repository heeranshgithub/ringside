/** Mirrors ProviderName in the backend, plus the two ways a person is added by hand. */
export type CandidateSource = "manual" | "csv" | "mock" | "pdl" | "coresignal" | "apollo";

export interface Candidate {
  id: string;
  jobId: string;
  name: string;
  phone: string | null;
  email: string | null;
  currentTitle: string | null;
  currentCompany: string | null;
  location: string | null;
  skills: string[];
  source: CandidateSource;
  sourceRef: string | null;
  linkedinUrl: string | null;
  summary: string | null;
  yearsExperience: number | null;
  allowRealDial: boolean;
  latestCallId: string | null;
  latestCallStatus: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateCandidateInput {
  jobId: string;
  name: string;
  phone?: string | null;
  email?: string | null;
  currentTitle?: string | null;
  currentCompany?: string | null;
  location?: string | null;
  skills?: string[];
  summary?: string | null;
  yearsExperience?: number | null;
  allowRealDial?: boolean;
}

export interface UpdateCandidateInput {
  id: string;
  name?: string;
  phone?: string | null;
  email?: string | null;
  currentTitle?: string | null;
  currentCompany?: string | null;
  location?: string | null;
  skills?: string[];
  summary?: string | null;
  yearsExperience?: number | null;
  allowRealDial?: boolean;
}

export interface ImportCsvInput {
  jobId: string;
  csvText: string;
}

export interface ImportCsvResult {
  created: Candidate[];
  skipped: string[];
}

export interface Person {
  source: string;
  sourceRef: string;
  name: string;
  firstName: string | null;
  lastName: string | null;
  phone: string | null;
  email: string | null;
  currentTitle: string | null;
  currentCompany: string | null;
  location: string | null;
  skills: string[];
  linkedinUrl: string | null;
  summary: string | null;
  yearsExperience: number | null;
}

export interface SearchPeopleInput {
  provider: string;
  criteria: {
    titles: string[];
    locations: string[];
    skills: string[];
    seniorities: string[];
    keywords: string;
    limit: number;
  };
}

export interface SearchPeopleResult {
  provider: string;
  results: Person[];
}

export interface ImportPeopleInput {
  jobId: string;
  people: Person[];
}

export interface ProviderInfo {
  name: string;
  configured: boolean;
  label: string;
  note: string;
  /** When set, the server clamps a search to this many records and the picker follows. */
  maxResults: number | null;
}
