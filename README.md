# Atlas Fresh, Daily Apple Export Planner

One workspace for the daily Production and Commercial meeting. It reads today's farm
receipts and the client program, builds the farm to client export plan for the single
packing station, and shows what is short, who it hits and what falls back to the local
market. The committee still approves the plan: the product never contacts a farm or a
client and never writes anywhere.

Draft README. It is completed in milestone M6.

## Prerequisites

Python 3.11 or newer, Node.js 20 or newer, npm. Tested with Python 3.12 and Node 24.

## Start it

```
make setup    # python venv and backend dependencies, npm ci in frontend
make dev      # backend on :8000, frontend on :5173, open http://localhost:5173
make test     # backend tests
make build    # production build of the frontend
make start    # one server: FastAPI serves the API and the built frontend on :8000
```

Without make:

```
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd frontend && npm ci

cd backend && .venv/bin/python -m uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run build
```

No `.env` file is needed. The AI assistant defaults to off and the app works without it.

## Architecture

```
backend/app
  ingest/      read the workbook (read only) and validate it, reject and never repair
  domain/      Pydantic models, quality segments, compatibility rules
  planning/    the deterministic engine, KPIs, comparisons, risk links, invariants
  api/         FastAPI routes, error responses, a small in memory plan cache
frontend/src
  api/         typed client and types that mirror the server models
  lib/         formatting, the generated sentence, the selection model
  components/  header, cards, tabs, tables shared pieces
  views/       Production, Commercial, Allocations
```

The planning engine is a pure function: no file access, no globals, no clock, no
randomness. The same input always gives the same output, byte for byte.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | status and whether an AI provider is configured |
| POST | `/api/plan/seed` | read the workbook at `DATA_PATH`, validate it, return `{plan_id, source_file, source, plan}` |
| POST | `/api/assistant/ask` | explain one part of a plan the server still holds, or answer honestly that it cannot |

Errors always come back in one small shape and never carry a stack trace:
`422 {"error": "VALIDATION_FAILED", "errors": [...]}` for a bad workbook,
`500 {"error": "SERVER_ERROR", "message": "..."}` for anything else.

## Planning policy

1. Supply is the actual A/B/C/D tonnes of each farm, one balance per farm and segment.
   Expected values are only used for comparison.
2. Clients are processed by export price, highest first, ties broken by client id.
3. For one client only compatible supply counts. `EXACT X` takes segment X only.
   `MINIMUM X` takes X or any better quality.
4. That supply is sorted by the smallest quality upgrade first, then by farm id.
5. Tonnes are taken in 5 t steps until the demand is met, the compatible supply runs
   out, or the station capacity, which is shared by all clients, is reached.
6. Everything left goes to the local market, valued at the local ratio times the export
   reference price of its own segment.

A client is `COMPLETE`, `PARTIAL` or `UNSERVED`. A client that is short is marked
`STATION_CAPACITY_REACHED` when the station was already full, otherwise
`INSUFFICIENT_COMPATIBLE_SEGMENT`. Six invariants are checked on every run. If one
fails the server answers with an error instead of a plan.

## Assumptions

- A client price and every reference price must be greater than 0.
- A client with demand 0 is `COMPLETE` and receives nothing.
- When the station limit and the compatible supply run out at the same moment, the
  reason reported is `STATION_CAPACITY_REACHED`.
- The expected mix of a farm must add up to 1.0 with a tolerance of 1e-6, because Excel
  stores decimals as floats. That check runs only when all four shares are valid numbers
  between 0 and 1, so the message names the root cause instead of a knock on error.
- Expected daily capacity is only used for comparison. It may carry one decimal and does
  not need to be a 5 t step.
- `acceptance_mode` and `requested_segment`, and the `segment` column of the reference
  price table, are strict. Only `EXACT`, `MINIMUM` and `A`, `B`, `C`, `D` are accepted,
  in capital letters with no extra spaces. Nothing is trimmed or corrected. A number
  written as text in a numeric cell is rejected the same way.
- A missing farm name or client name is rejected (`NAME_MISSING`). The brief requires
  both fields but gives no code for them.
- Exactly one station row is expected. Zero or more than one is rejected.
- Clicking an id highlights and scrolls to the matching row in Production and
  Commercial, and sets the real filters in Allocations. In the two tables the
  surrounding rows are what explains the result, for example that C03 and C04 took the
  Segment B before C09, so hiding them would remove the answer. In Allocations the list
  is long and flat, so filtering is the useful action there.
- The assistant response carries two extra fields beyond the shape in the brief,
  `fallback_answer` and `fallback_citations`. When a model answer cannot be shown, the
  engine summary travels with the error so the screen can offer it without asking the
  server again. `answer` stays empty in that case, so nothing unchecked can be shown as
  an AI answer by mistake.
- Timing and the "Loaded at" line live in the UI and in a response header, never inside
  the plan body, so the plan stays byte for byte deterministic.
- The kit workbook arrived as `brief.xlsx` and was renamed to
  `Atlas_Fresh_Production_Commercial_Data.xlsx`, the name the brief uses. Its contents
  were not touched and it is always opened read only.

## The assistant

The assistant only explains a plan the engine already produced. It never changes an
allocation, never calculates a number and never confirms anything. It answers three
questions: which clients are at risk and why, which farm and segment gaps matter most,
and why tonnes go to the local market and what they are worth. Anything else gets
"This information is not available in today's inputs or plan."

Before an answer reaches the screen the server checks it: the JSON must parse, every
farm, client and segment id in the text and in the citations must exist in the plan,
every number must be present in the small context that was sent, and a supported answer
must cite at least one id. A single failure rejects the whole answer, and the screen says
so instead of showing it.

Every state is labelled honestly. "AI answer, checked against the plan" appears only on
validated model output. A summary written by the planning engine is always labelled
"Summary from the planning engine, no AI".

### Turning the AI on

It is off by default and the app is complete without it.

Free and local, with [Ollama](https://ollama.com):

```
ollama pull llama3.1
cp .env.example .env      # then set AI_PROVIDER=ollama
```

With an Anthropic key:

```
cp .env.example .env      # then set AI_PROVIDER=anthropic and ANTHROPIC_API_KEY
```

`AI_TIMEOUT_SECONDS` (20 by default) bounds every call. `.env` is never committed.

## Known limitations

Written in milestone M6, together with the next production steps.
