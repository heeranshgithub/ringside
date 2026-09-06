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
  /** Hunar only dials inside a fixed daily window; outside it a call is held until morning. */
  callingWindow: string;
  callingTimezone: string;
  withinCallingWindow: boolean;
  windowOpensAt: string | null;
}

export interface StartVerificationInput {
  phone: string;
  consent: boolean;
}

export interface ConfirmVerificationInput {
  id: string;
  code: string;
}
