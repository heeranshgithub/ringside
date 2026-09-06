export type JobStatus = "draft" | "active" | "closed";

export interface SearchCriteria {
  titles: string[];
  locations: string[];
  skills: string[];
  seniorities: string[];
  keywords: string;
}

export interface Job {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  description: string;
  employmentType: string | null;
  seniority: string | null;
  salaryRange: string | null;
  summary: string;
  mustHaves: string[];
  niceToHaves: string[];
  screeningQuestions: string[];
  searchCriteria: SearchCriteria;
  agentId: string | null;
  status: JobStatus;
  candidateCount: number;
  callCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface ParsedJob {
  title: string;
  company: string | null;
  location: string | null;
  employmentType: string | null;
  seniority: string | null;
  salaryRange: string | null;
  summary: string;
  mustHaves: string[];
  niceToHaves: string[];
  screeningQuestions: string[];
  searchCriteria: SearchCriteria;
}

export interface ParseJobInput {
  description: string;
}

export interface CreateJobInput {
  title: string;
  company?: string | null;
  location?: string | null;
  description: string;
  employmentType?: string | null;
  seniority?: string | null;
  salaryRange?: string | null;
  summary?: string;
  mustHaves?: string[];
  niceToHaves?: string[];
  screeningQuestions?: string[];
  searchCriteria?: SearchCriteria;
}

export interface UpdateJobInput extends Partial<CreateJobInput> {
  id: string;
  agentId?: string | null;
  status?: JobStatus;
}
