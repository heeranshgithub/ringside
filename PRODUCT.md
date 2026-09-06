# Product


## Platform

web

## Users

In-house recruiters at a desk, on a laptop or external monitor, during office hours. They run several open
jobs at once and check call results between meetings. Secondary audience (confirmed): people evaluating the
product and the author's craft as a portfolio piece; they arrive at the dashboard cold.

## Product Purpose

Ringside is a voice-first hiring assistant. A recruiter pastes a job description; the product drafts a phone
screening agent, gathers candidates (manual, CSV, or people-search providers), has a Hunar.AI voice agent call
each candidate, and returns structured answers, a recording, an optional transcript, and a fit score on a
dashboard. Success: the recruiter knows who to interview without making a single call themselves.

## Positioning

The recruiter watches from ringside while the agent does the talking. The mechanism a neighbouring ATS cannot
truthfully copy: the job description becomes the agent's script, the agent's structured result schema, and the
people-search criteria in one step, and every call comes back as ranked, evidenced data rather than notes.

## Operating Context

- Workflow: JD → job (screening questions, search criteria) → agent (reviewed, then created on Hunar) →
  candidates → start calls → calls tab (live status, recording, answers, assessment, timeline).
- Calls run asynchronously; status arrives by webhook and a 30 s poller. Retries and calling windows are
  Hunar concepts the recruiter sets at launch.
- Safe-dial: a call reaches the candidate's own number only when real dialling is on and that candidate is
  cleared; otherwise it reaches a number the visitor verified by answering a call, and if there is none the
  candidate is skipped. There is no operator-configured fallback number. The UI must make the dial target
  unmistakable.
- Providers: People Data Labs, Coresignal, Apollo.io, and a seeded demo dataset. Availability depends on keys.

## Capabilities and Constraints

- Stack is fixed: Next.js App Router, React 19, TypeScript, Redux Toolkit + RTK Query, Tailwind v4, shadcn/ui
  (Base UI primitives). shadcn stays the component base; primitives are restyled, not replaced.
- Behaviour, routes, and copy are preserved by the redesign. Composition and visual world may change.
- Light and dark themes are both required; the default follows the visitor's system preference.
- Terminology: job, agent, candidate, call, assessment, safe-dial, calling window, retries.
- No transcript from the voice API; transcripts are produced on demand by an LLM and may be absent.
- Undecided: whether a public marketing page will exist. Out of scope for now.

## Brand Commitments

- Name: Ringside. Mark: a voice waveform bent into a ring, twelve radial ticks; see `src/components/logo.tsx`
  and the mark section of DESIGN.md.
- Anti-goals confirmed by the owner: not a generic SaaS dashboard; not playful or gimmicky (no mascots, heavy
  gradients, animation for its own sake); not corporate-cold enterprise grey; not dark-only "AI startup" neon.
- Built on Hunar.AI voice agents; credited, not co-branded.

## Evidence on Hand

- Working product with real call data shape: recordings (public WAV URLs), structured result objects, engagement
  and answered-by flags, retry state, event timeline. See `backend/app/modules/calls/schemas.py`.
- Demo dataset of 36 synthetic candidates (`backend/app/integrations/people/mock.py`), labelled as demo in the UI.
- No customer names, testimonials, pricing, or benchmarks exist. Do not invent them.

## Product Principles

1. The dial target is never ambiguous: safe or real is visible wherever a call can start.
2. Every screen answers "what happened on the calls" faster than "how do I configure this".
3. Async state is honest: pending, scheduled, retrying, and completed look different at a glance.
4. Evidence over verdict: the score is always one click from the recording and the answers that produced it.
5. Degrade visibly: a missing key or provider is shown, never silently faked.
