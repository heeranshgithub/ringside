export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details: { requestId?: string | null } & Record<string, unknown>;
  };
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface Capability {
  key: string;
  label: string;
  /** ok = real credentials · degraded = a deliberate offline stand-in · missing = will refuse */
  state: "ok" | "degraded" | "missing";
  detail: string;
  envVar: string | null;
}

export interface AppConfig {
  env: string;
  /** Added after the first release: an older backend will not send it. */
  capabilities?: Capability[];
  safeDialMode: boolean;
  testPhoneNumbersMasked: string[];
  hunarEnabled: boolean;
  llmEnabled: boolean;
  llmModel: string;
  webhooksEnabled: boolean;
  pollerEnabled: boolean;
  pollerIntervalSeconds: number;
  providers: string[];
  accessCodeRequired: boolean;
  clientDialEnabled: boolean;
}
