"use client";

import { Check, PhoneCall, RotateCcw, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/field";
import {
  useConfirmVerificationMutation,
  useGetDialCapabilityQuery,
  useGetDialTargetQuery,
  useReleaseDialTargetMutation,
  useStartVerificationMutation,
} from "@/features/dial/api";
import { formatClockDay } from "@/lib/format";
import { getErrorMessage } from "@/lib/errors";
import { normalizePhone, prettyPhone } from "@/lib/phone";
import { cn } from "@/lib/utils";

/**
 * Nominate your own phone as this session's safe-dial target.
 *
 * The number is proved by a call, not a claim: the agent rings it once, reads a four-digit
 * code, and only then will screening calls go there. Validation here is for feedback; the
 * backend applies the same rules again and is the one that decides.
 */
export function DialTargetCard({ className }: { className?: string }) {
  const { data: capability } = useGetDialCapabilityQuery();
  const { data: target } = useGetDialTargetQuery();
  const [start, startState] = useStartVerificationMutation();
  const [confirm, confirmState] = useConfirmVerificationMutation();
  const [release] = useReleaseDialTargetMutation();

  const [phone, setPhone] = useState("");
  const [consent, setConsent] = useState(false);
  const [code, setCode] = useState("");
  const [pending, setPending] = useState<{ id: string; masked: string } | null>(null);

  if (!capability?.enabled) return null;

  const normalized = normalizePhone(phone);
  const phoneError = phone.trim() && !normalized.ok ? normalized.error : undefined;
  // Hunar holds a call placed outside its window until morning. A verification code expires
  // in ten minutes, so a held call is not a slow success — it is a silent failure. The form
  // says so instead of letting someone press a button that cannot ring.
  const shut = capability.withinCallingWindow === false;
  const canStart = normalized.ok && consent && !startState.isLoading && !shut;

  if (target?.verified) {
    return (
      <div className={cn("surface space-y-3 p-4", className)}>
        <div className="flex items-start gap-2.5">
          <ShieldCheck className="text-done mt-0.5 size-4 shrink-0" />
          <div className="min-w-0">
            <p className="text-[14px] font-medium">Calls will ring your phone</p>
            <p className="text-muted-foreground mt-0.5 text-[13px]">
              Every screening call from this browser goes to{" "}
              <span className="text-foreground font-medium">{target.phonePretty}</span>, never to
              the candidate. Verified for this session.
            </p>
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={async () => {
            await release().unwrap();
            setPending(null);
            setPhone("");
            setConsent(false);
            toast.success("Number released");
          }}
        >
          <RotateCcw data-icon="inline-start" />
          Use a different number
        </Button>
      </div>
    );
  }

  if (pending) {
    return (
      <div className={cn("surface space-y-3 p-4", className)}>
        <div>
          <p className="text-[14px] font-medium">Enter the code we just read out</p>
          <p className="text-muted-foreground mt-0.5 text-[13px]">
            We called {pending.masked} and read a four-digit code. It expires in ten minutes.
          </p>
        </div>
        <form
          className="flex items-end gap-2"
          onSubmit={async (e) => {
            e.preventDefault();
            try {
              await confirm({ id: pending.id, code: code.trim() }).unwrap();
              setPending(null);
              setCode("");
              toast.success("Number verified. Calls will ring your phone.");
            } catch (err) {
              toast.error(getErrorMessage(err as never));
            }
          }}
        >
          <Field label="Code" htmlFor="dial-code" className="w-32">
            <Input
              id="dial-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={4}
              placeholder="1234"
              className="font-mono tracking-[0.3em]"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            />
          </Field>
          <Button type="submit" disabled={code.trim().length < 4 || confirmState.isLoading}>
            <Check data-icon="inline-start" />
            {confirmState.isLoading ? "Checking…" : "Verify"}
          </Button>
          <Button type="button" variant="ghost" onClick={() => setPending(null)}>
            Cancel
          </Button>
        </form>
      </div>
    );
  }

  return (
    <div className={cn("surface space-y-3 p-4", className)}>
      <div>
        <p className="text-[14px] font-medium">Try it on your own phone</p>
        <p className="text-muted-foreground mt-0.5 text-[13px]">
          We will call you once with a code. After that, every screening call from this browser
          rings your number, so you can hear the agent yourself. Candidates are never dialled.
        </p>
      </div>

      {shut ? (
        // Neutral, not amber: amber is reserved for a call that is ringing (DESIGN.md rule 4).
        // This is a closed sign, not an alarm.
        <p className="border-hairline text-muted-foreground bg-muted/40 rounded-lg border px-3 py-2 text-xs">
          Hunar only places calls between {capability.callingWindow.replace("-", " and ")}{" "}
          {capability.callingTimezone === "Asia/Kolkata" ? "IST" : capability.callingTimezone}. The
          next call can ring at{" "}
          <span className="font-medium">{formatClockDay(capability.windowOpensAt)}</span>.
        </p>
      ) : null}

      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!normalized.ok) return;
          try {
            const created = await start({ phone: normalized.value, consent }).unwrap();
            setPending({ id: created.id ?? "", masked: created.phoneMasked });
            toast.success("Calling you now with a code");
          } catch (err) {
            toast.error(getErrorMessage(err as never));
          }
        }}
      >
        <Field
          label="Your mobile number"
          htmlFor="dial-phone"
          error={phoneError}
          hint={
            normalized.ok
              ? `We will call ${prettyPhone(normalized.value)}`
              : shut
                ? "Indian mobile, with or without +91. Up to 3 calls per number per day."
                : `Indian mobile, with or without +91. Rings between ${capability.callingWindow.replace("-", " and ")} IST; up to 3 calls per number per day.`
          }
        >
          <Input
            id="dial-phone"
            inputMode="tel"
            autoComplete="tel"
            placeholder="Enter a 10-digit mobile number"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </Field>

        <label className="flex cursor-pointer items-start gap-2.5 text-[13px]">
          <Checkbox
            className="mt-0.5"
            checked={consent}
            onCheckedChange={(next) => setConsent(Boolean(next))}
          />
          <span className="text-muted-foreground">
            This is my own number and I agree to receive an automated call on it.
          </span>
        </label>

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={!canStart}>
            <PhoneCall data-icon="inline-start" />
            {startState.isLoading ? "Calling…" : "Call me with a code"}
          </Button>
          {capability.verifyCallsLeftToday !== null && (
            <span className="text-muted-foreground text-xs">
              {capability.verifyCallsLeftToday === 0
                ? "No verification calls left today"
                : `${capability.verifyCallsLeftToday} verification call${
                    capability.verifyCallsLeftToday === 1 ? "" : "s"
                  } left today`}
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
