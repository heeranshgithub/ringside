# Ringside

Ringside is a voice-first hiring assistant and people-search outreach tool built on [Hunar.AI](https://hunar.ai) voice agents.
Paste a job description, get a screening agent, add or discover candidates, let the agent call them, and read
the structured answers, recording, transcript and fit score on a dashboard.

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Redux Toolkit + RTK Query, Tailwind v4, shadcn/ui
- **Backend:** Python 3.12, FastAPI, Pydantic v2, motor (MongoDB), httpx, structlog
- **Voice:** Hunar Voice Agents external API (agents, calls, webhooks)
- **LLM:** any OpenRouter model (default `anthropic/claude-sonnet-5`; audio transcription via a Gemini flash model)
- **People search:** People Data Labs, Coresignal, Apollo.io, plus a seeded demo provider

## The three parts of the assignment

| # | Ask | Where it lives |
|---|-----|----------------|
| 1 | AI Hiring Assistant using Hunar voice agents | `/jobs/new` → job → **Agent** tab (LLM drafts the agent) → **Candidates** → **Start calls** → **Calls** tab |
| 2 | People search & reach-out with a results dashboard | `/search` (JD → criteria → provider search → import → call) and every job's Calls tab |
| 3 | Attendance for 1,000 people at 100 sites with no smartphones | `/attendance` (a written design, also summarised [below](#question-3-attendance-without-smartphones)) |

## How it works

```
JD ──► LLM parse ──► Job (criteria, screening questions)
                       │
                       ├──► LLM drafts agent ──► POST /agents (Hunar) ──► mirrored in Mongo
                       │
                       ├──► candidates: manual · CSV · PDL/Coresignal/Apollo/demo search
                       │
                       └──► POST /calls (Hunar) per candidate  ──► webhooks + poller keep our mirror in sync
                                                                   └──► LLM assesses result → fit score
```

Key design decisions:

- **Safe dial.** The Hunar key is a shared org key and the search providers return real people, so the set
  of reachable numbers is decided by the server, never by the browser. A call resolves to one of three, in order:
  the candidate's own number (only when `SAFE_DIAL_MODE=false` **and** that candidate was cleared in the UI),
  a number the visitor proved is theirs, or `TEST_PHONE_NUMBERS[0]`. The agent still uses the candidate's real
  name, role and company, so the demo is realistic without cold-calling strangers.
- **Bring your own phone.** With `ALLOW_CLIENT_DIAL_TARGET=true`, a visitor can nominate their own number and
  hear the agent themselves. Ownership is proved by a call rather than a claim: the agent rings the number once,
  reads a four-digit code, and only then will screening calls go there. That single call is the one place the
  product dials a number nobody has vouched for, so it is capped per number and per session, needs an explicit
  consent tick, and is written to a `dial_audit` trail alongside every screening call and where its number came
  from. The flag **refuses to arm without `APP_ACCESS_CODE`**, so a leaked URL alone can never ring anyone.
- **Own-data only.** The org behind the API key contains other people's agents and calls. The app never lists the org;
  it stores the IDs it created and fetches by ID.
- **Webhooks and polling.** Hunar posts signed webhooks (HMAC-SHA256, secret = API key) to `/webhooks/hunar`.
  A webhook is only applied when its signature verifies; the only exception is running with no API key at
  all, where the fake client is in use and there is no secret to check against.
  A background poller is the fallback: every 30 s it asks Mongo for calls that are not in a terminal state
  (plus completed ones still waiting on a recording or result, for up to 15 minutes) and re-fetches just
  those from `GET /calls/{id}`. It makes **no upstream requests when nothing is in flight**, and never more
  than 50 per tick. So the app works locally without a public URL, and survives a dropped webhook in
  production.

### What is reachable without the access code

Exactly two routes, and both are protected another way:

| Route | Why it cannot be gated | What protects it |
| --- | --- | --- |
| `GET /health` | the platform's health check runs before any credential exists | returns nothing sensitive |
| `POST /webhooks/hunar` | Hunar cannot send a header we invented | HMAC-SHA256 signature over the body |

`tests/test_access_gate.py` asserts that set over the whole OpenAPI surface, so mounting a new router
outside the gated one fails the suite rather than shipping quietly.

### Live updates

Three hops carry a call's state, and each is push where it can be:

| Hop | Mechanism |
| --- | --- |
| Hunar → backend | signed webhooks when `PUBLIC_BASE_URL` is set, otherwise a 30 s poller |
| backend → browser | server-sent events on `GET /api/events` |
| fallback | RTK Query refetch, which drops to 60 s while the stream is connected |

The stream carries notifications, not state. An event names the call that moved and the
browser refetches it through the normal API, so a dropped frame costs a few seconds of
staleness rather than a wrong screen. It is an in-process fan-out, which means a second
backend instance would only reach the browsers connected to it; that is the point to move
to Redis pub/sub.

### Receiving real webhooks locally

Hunar cannot reach `localhost`, so local runs poll by default. To get real pushes:

```bash
cd backend && uv run python scripts/tunnel.py     # opens a cloudflared tunnel
# writes PUBLIC_BASE_URL into backend/.env, then restart the backend
```

Quick tunnels get a new hostname each run, so the script rewrites the variable every time and clears it
on exit. While the tunnel is open the backend is publicly reachable, so set `APP_ACCESS_CODE` to keep
`/api` gated; `/webhooks/hunar` stays open by necessity and is protected by the signature check.
- **camelCase on the wire, snake_case everywhere else.** One Pydantic base model does the conversion. Mongo documents
  are plain snake_case and never leave the service layer unconverted.
- **Sourced numbers are never dialled.** Safe-dial means a candidate found through a people-search
  provider is called on the test number, not on their own. So a provider is judged on whether its
  *search* is real and affordable, never on whether it sells contact data, and the contact-data tier
  of every provider is irrelevant here. Cold-calling strangers pulled from a B2B database to
  demonstrate a product is not something this repo does.
- **A missing key refuses; it never pretends.** Without `HUNAR_API_KEY` the app will not create agents or
  place calls, it returns a 503 naming the variable to set. Without `OPENROUTER_API_KEY` the LLM features
  do the same. The in-memory simulators still exist and the tests inject them, but nothing reaches them by
  forgetting to configure something, because a simulator that returns real-looking ids is the worst kind of
  failure: it reports success and changes nothing. `GET /api/config` publishes a capability report and the
  UI turns it into a banner on every screen that needs the key.
- **No LLM fallback exists at all.** There is no rule-based parser to fall into, and no flag to enable one.
  Without a key, or when the OpenRouter account runs out of credit or gets rate limited, job parsing, agent
  drafting, scoring and transcription refuse with an error that names the cause (`llm_quota_exhausted`,
  `llm_credential_rejected`, `credential_missing`). An invented fit score sitting next to a real recording
  is indistinguishable from a real one, which is exactly why it is not allowed to exist. Tests inject
  `tests/stub_llm.py`, which deliberately lives outside `app/` so no misconfiguration can reach it.

## Run it locally

Prerequisites: Node ≥ 20 with pnpm ≥ 10, Python ≥ 3.12 with [uv](https://docs.astral.sh/uv/), a MongoDB
(`docker run -d -p 27017:27017 mongo:7` is enough).

```bash
# backend
cd backend
cp .env.example .env            # fill HUNAR_API_KEY and TEST_PHONE_NUMBERS; the rest are optional
uv sync
uv run uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
cp .env.local.example .env.local  # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
pnpm install
pnpm dev
```

Open http://localhost:3000. Backend API docs are at http://localhost:8000/docs (dev only).

### Quality gates

```bash
cd backend  && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest
cd frontend && pnpm lint && pnpm typecheck && pnpm build
```

The backend suite runs fully offline against an in-memory Mongo and a fake Hunar client. CI runs both suites on every
push (`.github/workflows/ci.yml`).

## Configuration

All backend configuration is environment variables read by one `Settings` class (`backend/app/core/config.py`).
See `backend/.env.example` for the full list. The ones that matter:

| Variable | Purpose |
|----------|---------|
| `HUNAR_API_KEY` | Hunar Voice Agents key. Also the HMAC secret for webhooks. |
| `TEST_PHONE_NUMBERS` | Comma-separated E.164 numbers. The first one receives every safe-dial call. |
| `SAFE_DIAL_MODE` | `true` (default) routes all calls to the test number. |
| `PUBLIC_BASE_URL` | Public HTTPS URL of the backend. When set, calls are created with webhook callbacks. |
| `MONGODB_URI`, `MONGODB_DB` | MongoDB connection. |
| `OPENROUTER_API_KEY`, `LLM_MODEL`, `LLM_AUDIO_MODEL` | LLM for JD parsing, agent drafting, scoring and transcription. |
| `PDL_API_KEY`, `PDL_SANDBOX` | People Data Labs. Sandbox mode costs no credits and is the default. |
| `CORESIGNAL_API_KEY`, `CORESIGNAL_MAX_COLLECT` | Coresignal. Each profile shown costs 20 credits, so the cap is a spend limit. |
| `APOLLO_API_KEY` | Apollo.io. API access is gated to their paid plans. |
| `APP_ACCESS_CODE` | Optional shared code. When set, **every `/api/*` route** returns 401 without it; the UI prompts once and stores it. Required for client dialling. |
| `ALLOW_CLIENT_DIAL_TARGET` | Lets a visitor verify and use their own number. Off by default. |
| `CORS_ORIGINS` | Comma-separated allowed origins (Amplify preview domains are allowed by regex). |

The frontend needs only `NEXT_PUBLIC_API_BASE_URL`.

## Deploy

- **Backend → AWS App Runner** from the `backend/Dockerfile` (push to ECR, create a service on port 8000, set the
  environment variables above, and set `PUBLIC_BASE_URL` to the service URL so webhooks work).
- **Frontend → AWS Amplify Hosting** with the app root set to `frontend/`; `frontend/amplify.yml` is the build spec.
  Set `NEXT_PUBLIC_API_BASE_URL` to the App Runner URL and add the Amplify URL to the backend's `CORS_ORIGINS`.
- **Database → MongoDB Atlas** (or any Mongo); set `MONGODB_URI`.

## Hunar constraints worth knowing

Measured against the live API, not documented in its OpenAPI schema:

| Rule | Value |
|---|---|
| `earliest_call_time` minimum | `08:00` |
| `last_call_time` maximum | `21:00` |

A window outside that is rejected with a 400 before Hunar even looks up the agent, so
"call at any time" is not on offer. `GuardrailsInput` validates it on our side and returns a
422 naming the field, rather than relaying a bare platform error to the user.

## Choosing a people-search provider

The assignment names four. One is gone and the rest differ more in billing than in data.

| Provider | Free tier | What a search costs | Notes |
|---|---|---|---|
| **People Data Labs** *(default)* | 100 searches/month, self-serve | 1 credit per profile returned | A **sandbox** serves synthetic records with an identical schema at zero credits. Contact fields are boolean flags on the free tier, which does not matter here. |
| **Coresignal** | 7-day trial, 2,000 credits | Search is free and returns ids; each profile collected costs 20 | 100 profiles in the trial, then $49/month. `CORESIGNAL_MAX_COLLECT` caps what one search can spend. |
| **Apollo.io** | Search costs no credits | API access is gated to paid plans | Results are masked: last names render as `Do***e` and contacts arrive as booleans. Verify you can create a key before planning around it. |
| **Proxycurl** | — | — | **Shut down 4 July 2025** after LinkedIn sued. The team now runs a company-data product; person search is gone. |

PDL is the default because the sandbox makes development free and 100 real searches a month is
more than a demo needs. Set `PDL_SANDBOX=false` only for the recorded run.

## API surface (backend)

All routes are under `/api` and speak camelCase JSON. Errors always look like
`{"error": {"code": "...", "message": "...", "details": {"requestId": "..."}}}`.

| Area | Routes |
|------|--------|
| Jobs | `POST /jobs/parse`, `GET/POST /jobs`, `GET/PATCH/DELETE /jobs/{id}` |
| Agents | `GET /agents/options`, `POST /agents/draft`, `GET/POST /agents`, `POST /agents/import`, `GET/PATCH/DELETE /agents/{id}`, `POST /agents/{id}/refresh` |
| Candidates | `GET/POST /candidates`, `POST /candidates/import-csv`, `PATCH/DELETE /candidates/{id}` |
| People search | `GET /search/providers`, `POST /search/people`, `POST /search/import` |
| Calls | `GET /calls`, `POST /calls/launch`, `POST /calls/sync`, `GET /calls/{id}`, `POST /calls/{id}/sync`, `POST /calls/{id}/assess`, `POST /calls/{id}/transcribe` |
| Live | `GET /api/events` (server-sent events) |
| Dial target | `GET /dial-target`, `GET /dial-target/current`, `POST /dial-target/start`, `POST /dial-target/{id}/confirm`, `DELETE /dial-target` |
| Meta | `GET /config`, `GET /dashboard/summary`, `GET /health`, `POST /webhooks/hunar` (no access code, HMAC-verified) |

## Repository layout

```
backend/
  app/core            settings, base models (camelCase boundary), errors, db, deps
  app/integrations    hunar (client + fake + webhook HMAC), people (apollo, pdl, mock), llm (OpenRouter, refusing null object)
  app/modules         jobs, agents, candidates, search, calls, webhooks, dashboard (router + service + schemas)
  app/workers         background call poller
  tests               offline test suite
frontend/
  src/app             routes (each segment has loading.tsx and error.tsx)
  src/features        RTK Query endpoints, one file per domain
  src/components      UI (shadcn primitives in components/ui)
  src/types           wire types mirroring the Pydantic DTOs
```

## Question 3: attendance without smartphones

No apps, but feature phones, landlines, SMS, IVR, biometric punch machines and LLMs all exist. Attendance is a daily
fact-collection problem with three hard parts: identity, presence, and exceptions. The cheapest reliable channel at all
100 sites is the phone network, and an LLM means a phone call no longer needs a human on the other end. The design:

1. **Missed-call check-in (free).** Each worker registers one number; each site gets a virtual number. A missed call
   inside the shift window marks you present and triggers an SMS receipt.
2. **Voice-AI roll-call.** Twenty minutes after shift start a voice agent calls every site supervisor on the site landline,
   in the local language, and turns "everyone is here except Suresh, Priya came at 9:30" into a structured per-worker
   record, exactly like the screening agent in this app.
3. **Verification.** Landline calls prove the supervisor is on site; random spot-check calls to workers ask questions
   only someone on site can answer; biometric exports, where they exist, are reconciled against the calls; an LLM
   flags anomalies (always-full-house supervisors, numbers checking in from the wrong site).
4. **Reconciliation and exceptions.** By 09:30 an LLM merges the streams into one table with a confidence flag per row.
   HR sees one page: silent sites, three-day absentees, unapproved replacements. Agents call the silent sites so HR
   does not have to. Paper sheets photographed or faxed are read by a vision model as the last fallback.

Roughly 500 voice-minutes a day for 1,000 people, a fraction of the clerical cost it replaces. The full write-up,
including why not SMS-only or biometrics-everywhere, is on the `/attendance` page of the app.
