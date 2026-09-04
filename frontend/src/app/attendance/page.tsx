import type { Metadata } from "next";
import { PhoneMissed, Radio, ShieldAlert, Sun } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = { title: "Attendance without smartphones" };

function Step({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="bg-primary text-primary-foreground flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold">
        {n}
      </span>
      <div>
        <p className="font-medium">{title}</p>
        <p className="text-muted-foreground text-sm">{children}</p>
      </div>
    </li>
  );
}

export default function AttendancePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Assignment question 3"
        title="1,000 people, 100 sites, no smartphones"
        description="If there were no smartphones but LLMs and everything else existed, how would an HR team track attendance every day? Here is the system I would run."
      />

      <Card>
        <CardHeader>
          <CardTitle>The constraint, read carefully</CardTitle>
          <CardDescription>
            No apps and no smartphones. But feature phones, landlines, SMS, IVR, biometric punch
            machines, PCs at some sites, and LLMs that can listen, talk, read and reason all still
            exist.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>
            Attendance is a daily fact-collection problem with three hard parts:{" "}
            <strong>identity</strong> (is it really Ramesh?), <strong>presence</strong> (is he at
            the site, now?), and <strong>exceptions</strong> (late, half-day, swapped shift, on
            leave). Apps solved these with a GPS-tagged selfie. Without apps, the cheapest reliable
            channel in every one of the 100 locations is the phone network, and the thing an LLM
            adds is that a phone call no longer needs a human on the other end.
          </p>
          <p>
            So the design is <strong>voice-first, with a free fallback and a paper fallback</strong>
            , and an LLM doing the reconciliation work that a team of clerks used to do.
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PhoneMissed className="size-4" /> Layer 1 · Missed-call check-in
            </CardTitle>
            <CardDescription>
              Zero cost per worker, works on any ₹800 feature phone.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              Every worker registers one phone number with HR. Each site gets its own virtual
              number. To mark attendance you give a missed call to your site&apos;s number inside
              the shift-start window.
            </p>
            <p>
              The telephony provider posts the caller ID and timestamp; the system marks{" "}
              <em>present, on time</em> and sends a one-line SMS confirmation. Identity is the SIM
              plus the site-specific number; presence is inferred from the window and cross-checked
              later.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Radio className="size-4" /> Layer 2 · Voice AI roll-call
            </CardTitle>
            <CardDescription>The same voice-agent platform used in this app.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              Twenty minutes after the shift starts, a voice agent calls each site supervisor on the
              site landline or their registered phone. The supervisor reads the roll or just says
              what changed: &ldquo;everyone from the list is here except Suresh, Priya came at
              nine-thirty, we have two relievers from the Hosur site.&rdquo;
            </p>
            <p>
              The agent speaks the local language, confirms each fact back, and returns a structured
              result: per-worker status, late arrivals, replacements, and free-text notes, exactly
              like the result schema on a screening call.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldAlert className="size-4" /> Layer 3 · Verification
            </CardTitle>
            <CardDescription>Make cheating expensive, not impossible.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              Calling the <em>site landline</em> proves the supervisor is physically there. Random
              spot-check calls to two or three workers per site per week ask them to answer a
              question only someone on site would know (&ldquo;what colour is today&apos;s job
              card?&rdquo;).
            </p>
            <p>
              Where a biometric punch machine exists, its daily export is reconciled against the
              calls. An LLM reads all three streams and flags patterns: a supervisor who always
              reports a full house, a number that checks in from the wrong site, a worker present on
              paper but absent from every spot check.
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sun className="size-4" /> A day in the life
          </CardTitle>
          <CardDescription>What the HR team actually sees.</CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="space-y-4">
            <Step n={1} title="07:45 – 08:15 · Workers check in">
              Missed calls arrive at the 100 site numbers. Confirmations go back by SMS. By 08:15
              the dashboard already shows roughly 85% of the workforce as present.
            </Step>
            <Step n={2} title="08:20 · Agents call every supervisor">
              100 parallel voice calls, about three minutes each, in Hindi, Tamil, Kannada or
              whatever the site speaks. Each returns a structured roll-call. Sites that do not pick
              up are retried at 08:50 and 09:20 with the same retry logic this app uses.
            </Step>
            <Step n={3} title="09:30 · Reconciliation">
              An LLM merges missed calls, supervisor roll-calls and any biometric exports, resolves
              conflicts (a worker with a missed call but reported absent gets a callback), and
              writes a clean attendance table with a confidence flag per row.
            </Step>
            <Step n={4} title="10:00 · Exceptions only">
              HR gets one page: sites that never reported, workers absent three days running,
              replacements without approval, and anomalies the model flagged. Everything else is
              closed automatically. A voice agent calls the silent sites and the absentees so HR
              does not have to.
            </Step>
            <Step n={5} title="Month end · Payroll">
              The attendance table feeds payroll directly. Because every row has an evidence trail
              (call recording, caller ID, biometric row), disputes are settled by replaying the
              source rather than by argument.
            </Step>
          </ol>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Why this and not something else</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              <strong>Not SMS-only:</strong> typing structured codes on a keypad has a high error
              rate and no proof of location. SMS stays as the receipt channel.
            </p>
            <p>
              <strong>Not biometrics everywhere:</strong> machines cost money, break, and need a PC
              and power at every site. Use them where they already exist; do not make the system
              depend on them.
            </p>
            <p>
              <strong>Not a human call centre:</strong> 100 supervisor calls a day is a small team
              of clerks with sick days and inconsistent notes. Voice agents make the same call, the
              same way, at 08:20 sharp, and hand back JSON.
            </p>
            <p>
              <strong>Paper as the last fallback:</strong> a site with no phone signal keeps a
              signed sheet; a photo from any camera or a fax is read by a vision LLM and lands in
              the same table, flagged as low-confidence.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Rough cost and risk</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p>
              <strong>Cost:</strong> about 100 supervisor calls × 3 minutes plus perhaps 60
              exception and spot-check calls a day, so roughly 500 voice-minutes a day. Missed calls
              and SMS are close to free. That is a fraction of the salary of the clerks it replaces.
            </p>
            <p>
              <strong>Failure modes:</strong> shared SIMs (mitigated by spot checks and landline
              calls), supervisors colluding (mitigated by anomaly detection and unannounced worker
              calls), and network outages (mitigated by the paper fallback and retries).
            </p>
            <p>
              <strong>What I would prototype first:</strong> the supervisor roll-call agent. It is
              the same shape as the screening agent in this app, and the Site Attendance Clerk agent
              already visible in the shared Hunar org shows other people reached the same
              conclusion.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
