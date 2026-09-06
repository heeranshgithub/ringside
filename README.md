# Ringside

A voice-first hiring assistant built on [Hunar.AI](https://hunar.ai) voice agents. Paste a job
description, get a screening agent, add or find candidates, let the agent call them, and read the
answers, recording and fit score on a dashboard.

**Live demo:** https://main.d23gnufxfmvins.amplifyapp.com

The demo sits behind a shared access code, which is in the same email as this link. It can place real
phone calls, so the gate is the point.

- **Frontend** Next.js 16 (App Router), React 19, TypeScript, Redux Toolkit + RTK Query, Tailwind v4, shadcn/ui
- **Backend** Python 3.12, FastAPI, Pydantic v2, motor (MongoDB), httpx, structlog
- **Voice** Hunar Voice Agents external API
- **LLM** any OpenRouter model (default `anthropic/claude-sonnet-5`, audio via `google/gemini-2.5-flash`)
- **People search** People Data Labs, Coresignal, Apollo.io, and a seeded demo provider

## The three parts of the assignment

| # | Ask | Where it lives |
|---|-----|----------------|
| 1 | AI hiring assistant on Hunar voice agents | `/jobs/new` -> job -> **Agent** tab -> **Candidates** -> **Start calls** -> **Calls** |
| 2 | People search and reach-out with a dashboard | `/search`, and every job's Calls tab |
| 3 | Attendance for 1,000 people at 100 sites, no smartphones | [QUESTION-3.md](QUESTION-3.md) |

## How it works

```
JD ──► LLM parse ──► Job (criteria, screening questions)
                       │
                       ├──► LLM drafts agent ──► POST /agents (Hunar) ──► mirrored in Mongo
                       │
                       ├──► candidates: manual · CSV · PDL/Coresignal/Apollo/demo search
                       │
                       └──► POST /calls (Hunar) per candidate ──► webhooks + poller keep the mirror fresh
                                                                  └──► LLM assesses result → fit score
```

## Decisions worth defending

**Nobody gets called who did not ask to be.** The Hunar key is shared and the search providers return
real people, so the server decides what is dialable, never the browser. A call resolves to one of two
numbers: the candidate's own, only when `SAFE_DIAL_MODE=false` *and* that candidate was cleared in the
UI; or a number the visitor proved is theirs. Anything else and the candidate is skipped rather than
dialled. There is deliberately no operator-configured fallback number underneath, because a fallback is
what turns "safe by default" into "safe until someone misconfigures it".

**Ownership is proved by a call, not a claim.** A visitor nominates their number, the agent rings it
once and reads a four-digit code, and only then do screening calls go there. That single call is the
only time this product dials a number nobody vouched for, so it needs a consent tick, it is capped at
three per number, five per session and ten in total per rolling day, it is refused outright if it could
not ring inside Hunar's calling window, and it lands in a `dial_audit` trail alongside every screening
call and which tier its number came from. The feature refuses to arm unless `APP_ACCESS_CODE` is also
set, so a leaked URL alone can never ring anyone.

**A missing key refuses; it never pretends.** Without `HUNAR_API_KEY` or `OPENROUTER_API_KEY` the app
returns a 503 naming the variable to set. There is no rule-based parser to fall back to and no flag to
enable one, so job parsing, agent drafting, scoring and transcription fail loudly with a named cause
(`llm_quota_exhausted`, `llm_credential_rejected`, `credential_missing`). An invented fit score sitting
next to a real recording is indistinguishable from a real one, which is exactly why it is not allowed to
exist. The simulators live in `tests/`, outside `app/`, so no misconfiguration can reach them.
`GET /api/config` publishes a capability report and the UI turns it into a banner on the screens that
need the key.

**Own data only.** The org behind the API key holds other applicants' agents and calls. The app never
lists the org; it stores the IDs it created and fetches by ID.

**Signed webhooks, with a poller as the safety net.** Hunar posts to `/webhooks/hunar` with an
HMAC-SHA256 signature over `"{timestamp}." + body`, keyed by the API key. A webhook is applied only if
that verifies, and every delivery is stored with its `signature_valid` flag either way. The one bypass is
running with no `HUNAR_API_KEY` at all, where there is no secret to check against and the app refuses to
place calls anyway. The poller is
the fallback: every 30 seconds it asks Mongo, not Hunar, which calls are unfinished, plus completed ones
still missing a recording for up to 15 minutes, then re-fetches at most 50 of them by ID. With nothing
in flight it makes no upstream requests at all, so local runs work without a public URL.

**camelCase on the wire, snake_case everywhere else.** One Pydantic base model does the conversion at
the boundary. Mongo documents are plain snake_case and never leave the service layer unconverted.

## Access and live updates

With `APP_ACCESS_CODE` set, every `/api/*` route returns 401 without the `X-Access-Code` header. Exactly
two routes sit outside the gate, each protected another way: `GET /health`, which the platform calls
before any credential exists, and `POST /webhooks/hunar`, which Hunar cannot send our header to and which
the signature protects instead. `backend/tests/test_access_gate.py` asserts that set across the whole
OpenAPI surface, so mounting a new router outside the gate fails the suite rather than shipping quietly.

State reaches the browser over server-sent events on `GET /api/events`, which carry notifications rather
than state: an event names the call that moved and the browser refetches it normally, so a dropped frame
costs seconds of staleness rather than a wrong screen. Polling drops to 60 seconds while the stream is
connected. The fan-out is in-process, so a second instance would only reach its own browsers; that is the
point to move to Redis pub/sub.

## Run it locally

Node 22 with pnpm 11, Python 3.12 with [uv](https://docs.astral.sh/uv/), and a MongoDB
(`docker run -d -p 27017:27017 mongo:7` is enough).

```bash
# backend
cd backend
cp .env.example .env            # fill HUNAR_API_KEY; the rest are optional
uv sync
uv run uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
cp .env.local.example .env.local
pnpm install
pnpm dev
```

Open http://localhost:3000. Interactive API docs are at http://localhost:8000/docs, outside production.

Hunar cannot reach `localhost`, so local runs poll by default. `uv run python scripts/tunnel.py` opens a
cloudflared tunnel and writes `PUBLIC_BASE_URL` into `backend/.env` if you want real webhook pushes.

### Quality gates

```bash
cd backend  && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest
cd frontend && pnpm lint && pnpm typecheck && pnpm build
```

The backend suite runs fully offline against an in-memory Mongo and a fake Hunar client.
`.github/workflows/ci.yml` runs both suites on every push to `main` and `dev`, and on a green push to
`main` it also builds `backend/Dockerfile` and pushes it to ECR, which App Runner redeploys.

## Configuration

One `Settings` class reads everything from the environment (`backend/app/core/config.py`), and
`backend/.env.example` is the full annotated list. The ones that decide behaviour:

| Variable | Default | Purpose |
|---|---|---|
| `HUNAR_API_KEY` | — | Hunar key, and the HMAC secret for webhooks |
| `SAFE_DIAL_MODE` | `true` | Candidates are never dialled on their own numbers |
| `ALLOW_CLIENT_DIAL_TARGET` | `true` | Lets a visitor verify their own phone. Inert unless `APP_ACCESS_CODE` is set |
| `APP_ACCESS_CODE` | — | When set, every `/api/*` route requires it |
| `PUBLIC_BASE_URL` | — | When set, calls are created with webhook callbacks |
| `OPENROUTER_API_KEY`, `LLM_MODEL` | — | Parsing, drafting, scoring, transcription |
| `PDL_API_KEY`, `PDL_SANDBOX` | —, `true` | Sandbox costs no credits and is the default |
| `CORESIGNAL_MAX_COLLECT` | `10` | Each profile collected costs 20 credits, so this caps the spend |

Also `MONGODB_URI`, `APOLLO_API_KEY`, `CORS_ORIGINS` and the dial-verification limits. The frontend needs
only `NEXT_PUBLIC_API_BASE_URL`.

## API

Forty routes, all under `/api` and speaking camelCase, except `GET /health` and `POST /webhooks/hunar`
which sit outside the gate. The areas are jobs, agents, candidates, search, calls, dial-target, events
and dashboard. Errors always look like
`{"error": {"code": ..., "message": ..., "details": {"requestId": ...}}}`. Browse the full surface at
`/docs` when running locally.

Two Hunar limits are worth knowing because they were measured against the live API rather than published
in its schema: `earliest_call_time` cannot be before `08:00`, and `last_call_time` cannot be after
`21:00`. `GuardrailsInput` validates both and returns a 422 naming the field, rather than relaying a bare
platform error.

## People-search providers

The assignment names four. **Proxycurl shut down on 4 July 2025** after LinkedIn sued it, so three remain,
and they differ more in billing than in data. **People Data Labs** is the default: 100 searches a month
self-serve, plus a sandbox returning synthetic records with an identical schema at zero credits.
**Coresignal** searches free and charges 20 credits per profile collected. **Apollo** searches free but
gates API access to paid plans and masks last names. All four adapters are wired and
`GET /search/providers` reports which are configured; the Coresignal adapter is written from its published
docs and has never been run against a live key, which its own docstring says out loud.

Because safe-dial means a sourced candidate is never called on their own number, a provider is judged here
on whether its *search* is real and affordable, never on whether it sells contact data.

## Deploy

Running in `ap-south-1`: the backend on **AWS App Runner** from `backend/Dockerfile`, the frontend on
**AWS Amplify Hosting** with app root `frontend/` and `frontend/amplify.yml` as the build spec, and the
database on **MongoDB Atlas**. Point `NEXT_PUBLIC_API_BASE_URL` at the App Runner URL, add the Amplify
origin to `CORS_ORIGINS`, and set `PUBLIC_BASE_URL` to the service URL so webhooks arrive.

## Repository layout

`backend/app` splits into `core` (settings, the camelCase boundary, errors, db, event bus), `integrations`
(hunar, the four people-search adapters, llm), `modules` (jobs, agents, candidates, search, calls, dial,
events, webhooks, dashboard, each a router plus service plus schemas) and `workers` (the call poller). The
simulators live in `backend/tests`, deliberately outside `app`.

`frontend/src` splits into `app` (routes, all ten segments carrying `loading.tsx` and `error.tsx`),
`features` (RTK Query endpoints, one file per domain), `components` (with shadcn primitives in
`components/ui`) and `types` (wire types mirroring the Pydantic DTOs).

---

**Question 3** of the assignment, on tracking attendance for 1,000 people across 100 sites without
smartphones, is answered in [QUESTION-3.md](QUESTION-3.md).
