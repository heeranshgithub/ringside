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
  /**
   * Hunar only dials inside a fixed daily window; outside it a call is held until morning.
   *
   * Optional on purpose. Amplify ships the frontend in about two minutes and App Runner takes
   * nearer five, so for a few minutes after every deploy this browser is talking to the
   * previous backend. A field added on both sides at once is still absent in that window.
   */
  callingWindow?: string;
  callingTimezone?: string;
  withinCallingWindow?: boolean;
  windowOpensAt?: string | null;
}

export interface StartVerificationInput {
  phone: string;
  consent: boolean;
}

export interface ConfirmVerificationInput {
  id: string;
  code: string;
}
