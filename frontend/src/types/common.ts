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

export interface AppConfig {
  env: string;
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
}
