# Ringside

Ringside is a voice-first hiring assistant and people-search outreach tool built on [Hunar.AI](https://hunar.ai) voice agents.
Paste a job description, get a screening agent, add or discover candidates, let the agent call them, and read
the structured answers, recording, transcript and fit score on a dashboard.

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, Redux Toolkit + RTK Query, Tailwind v4, shadcn/ui
- **Backend:** Python 3.12, FastAPI, Pydantic v2, motor (MongoDB), httpx, structlog
- **Voice:** Hunar Voice Agents external API (agents, calls, webhooks)
- **LLM:** any OpenRouter model (default `anthropic/claude-sonnet-5`; audio transcription via a Gemini flash model)
- **People search:** Apollo.io, People Data Labs, plus a seeded demo provider

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
                       ├──► candidates: manual · CSV · Apollo/PDL/demo search
                       │
                       └──► POST /calls (Hunar) per candidate  ──► webhooks + poller keep our mirror in sync
                                                                   └──► LLM assesses result → fit score
```

Key design decisions:

- **Safe dial.** The Hunar key is a shared org key and the search providers return real people. Every outbound call is
  routed to `TEST_PHONE_NUMBERS[0]` unless `SAFE_DIAL_MODE=false` **and** the candidate was explicitly cleared in the UI.
  The agent still uses the candidate's real name, role and company, so the demo is realistic without cold-calling strangers.
- **Own-data only.** The org behind the API key contains other people's agents and calls. The app never lists the org;
  it stores the IDs it created and fetches by ID.
- **Webhooks and polling.** Hunar posts signed webhooks (HMAC-SHA256, secret = API key) to `/webhooks/hunar`. A
  background poller also syncs every non-terminal call every 30 s, so the app works locally without a public URL and
  survives missed webhooks in production.
- **camelCase on the wire, snake_case everywhere else.** One Pydantic base model does the conversion. Mongo documents
  are plain snake_case and never leave the service layer unconverted.
- **Degrades gracefully.** No OpenRouter key → rule-based JD parsing, template agents and heuristic scoring.
  No Hunar key → an in-memory fake that completes calls with sample results. No provider keys → the demo dataset.

## Run it locally

Prerequisites: Node ≥ 20 with pnpm ≥ 10, Python ≥ 3.12 with [uv](https://docs.astral.sh/uv/), a MongoDB
(`docker run -d -p 27017:27017 mongo:7` is enough).

```bash
# backend
cd backend
cp .env.example .env            # fill HUNAR_API_KEY, TEST_PHONE_NUMBERS, optionally OPENROUTER_API_KEY / APOLLO_API_KEY / PDL_API_KEY
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
| `APOLLO_API_KEY`, `PDL_API_KEY` | People-search providers. The demo provider is always available. |
| `APP_ACCESS_CODE` | Optional shared code; when set the UI asks for it and sends it as `X-Access-Code`. |
| `CORS_ORIGINS` | Comma-separated allowed origins (Amplify preview domains are allowed by regex). |

The frontend needs only `NEXT_PUBLIC_API_BASE_URL`.

## Deploy

- **Backend → AWS App Runner** from the `backend/Dockerfile` (push to ECR, create a service on port 8000, set the
  environment variables above, and set `PUBLIC_BASE_URL` to the service URL so webhooks work).
- **Frontend → AWS Amplify Hosting** with the app root set to `frontend/`; `frontend/amplify.yml` is the build spec.
  Set `NEXT_PUBLIC_API_BASE_URL` to the App Runner URL and add the Amplify URL to the backend's `CORS_ORIGINS`.
- **Database → MongoDB Atlas** (or any Mongo); set `MONGODB_URI`.

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
| Meta | `GET /config`, `GET /dashboard/summary`, `GET /health`, `POST /webhooks/hunar` (unauthenticated, HMAC-verified) |

## Repository layout

```
backend/
  app/core            settings, base models (camelCase boundary), errors, db, deps
  app/integrations    hunar (client + fake + webhook HMAC), people (apollo, pdl, mock), llm (OpenRouter + rule-based)
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
