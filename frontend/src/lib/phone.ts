/**
 * Client-side phone rules, mirroring `backend/app/core/phone.py`.
 *
 * This exists for feedback while typing, so someone sees "that is not a mobile number"
 * before they wait for a round trip. It is not a security boundary: the backend applies
 * the same rules again and is the only thing that decides what gets dialled. If the two
 * ever disagree, the backend is right.
 */

const E164 = /^\+[1-9]\d{7,14}$/;
const INDIA_MOBILE = /^\+91[6-9]\d{9}$/;

export type PhoneCheck = { ok: true; value: string } | { ok: false; error: string };

export function normalizePhone(raw: string, defaultCc = "+91"): PhoneCheck {
  const trimmed = raw.trim();
  if (!trimmed) return { ok: false, error: "Enter your mobile number" };

  let digits = trimmed.replace(/[^\d+]/g, "");
  digits = (digits.startsWith("+") ? "+" : "") + digits.replace(/\+/g, "");
  if (digits.startsWith("00")) digits = `+${digits.slice(2)}`;

  if (!digits.startsWith("+")) {
    const bare = digits.replace(/^0+/, "");
    if (bare.length === 10) digits = defaultCc + bare;
    else if (bare.length > 10) digits = `+${bare}`;
    else return { ok: false, error: "That is too short for a phone number" };
  }

  if (!E164.test(digits)) return { ok: false, error: "That is not a valid phone number" };

  const national = digits.startsWith("+91") ? digits.slice(3) : digits.replace("+", "");
  if (new Set(national).size === 1) {
    return { ok: false, error: "That is a single repeated digit" };
  }
  if (digits.startsWith("+91") && !INDIA_MOBILE.test(digits)) {
    return { ok: false, error: "Indian mobiles are ten digits starting with 6, 7, 8 or 9" };
  }
  return { ok: true, value: digits };
}

export function prettyPhone(e164: string): string {
  return INDIA_MOBILE.test(e164) ? `+91 ${e164.slice(3, 8)} ${e164.slice(8)}` : e164;
}
