export interface DialTarget {
  id: string | null;
  phoneMasked: string;
  phonePretty: string | null;
  verified: boolean;
  expiresAt: string | null;
  attemptsLeft: number | null;
}

export interface DialCapability {
  enabled: boolean;
  reason: string | null;
  verifyCallsLeftToday: number | null;
}

export interface StartVerificationInput {
  phone: string;
  consent: boolean;
}

export interface ConfirmVerificationInput {
  id: string;
  code: string;
}
