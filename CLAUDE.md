# CLAUDE.md

Project guide for Claude Code. Read this whole file before doing anything. It is the single source of truth for this repository. When this file and your own ideas disagree, follow this file. When this file and the brief (`docs/brief.pdf`) disagree, follow the brief and tell Abdellah.

---

## 0. Quick facts

| Item | Value |
|---|---|
| Project | Atlas Fresh, Daily Apple Export Planner |
| Why | Weekend technical assessment for Qarizmi (AI Product Engineer pre-hire internship) |
| Candidate | Abdellah |
| Deadline | Submit before 18 September 2026 |
| Time box | 10 to 12 hours total. Stop and document what remains. Working beats perfect. |
| Stack | Python 3.11+ / FastAPI / Pydantic v2 / openpyxl / pytest on the server. React 18 / TypeScript / Vite / Tailwind CSS on the client. |
| Paid services | None required. The AI assistant must work honestly with no API key. |
| Input | `data/Atlas_Fresh_Production_Commercial_Data.xlsx` (authoritative, never modified) |

### How to talk to Abdellah

- Use plain, simple language. Avoid jargon. If a technical word is needed, explain it in a few words.
- Do not use em dashes in any text you write (docs, README, comments, UI copy, commit messages). Use commas, periods, colons or parentheses instead.
- Keep updates short: what you did, what you checked, what is next.

---

## 1. The business problem in plain words

Atlas Fresh is a fictional apple company.

- **20 farms** (F01 to F20) grow apples.
- Apples are sorted into **4 quality segments**: A (best), B, C, D (worst).
- **1 export station** (STATION-01) can pack at most **500 t per day** for export.
- **10 export clients** (C01 to C10). Each client has a maximum demand in tonnes, a quality rule and a price per tonne.
- Any apple not exported goes to the **local market** and is worth only **10% of the reference export price of its segment**. This is a big loss, so it must be very visible.

Before the season, two separate plans exist:

1. Commercial sold a client program (demand, quality rule, price).
2. Production set an expected daily capacity and A/B/C/D mix per farm.

No farm is assigned to any client in the data. **Building the daily farm to client assignment is part of the job.**

Every day, reality differs from plan. On the snapshot day, farms were expected to deliver 600 t and delivered 560 t. Segment A is 11.7 t below plan (the hardest quality). B and C are below plan. D is above plan. The station can only export 500 t.

Today, Production and Commercial meet and compare spreadsheets by hand. **Our product replaces that manual preparation with one clear decision support workspace.** The committee still approves the plan. The product never contacts farms or clients, never confirms execution and never writes to an external system.

Success means: a non technical manager understands the situation in under 1 minute and can trace any allocation or shortage in under 3 minutes, without anyone narrating.

---

## 2. Evaluation (what matters most)

| Area | Points | Meaning for us |
|---|---|---|
| User experience and product judgment | **40** | Clarity, speed, the link between Production and Commercial, feedback states, accessibility, sensible trade offs |
| Data and planning correctness | 25 | Exact policy, compatibility, hard limits, reasons, baseline, local value, no hard coding |
| Full stack engineering and tests | 15 | Server validation, API design, architecture, errors, types, tests, build |
| Grounded AI assistant | 10 | Correct boundary, evidence IDs, minimal context, validation, honest fallback |
| Delivery and ownership | 10 | Clean start, README, walkthrough, AI disclosure, honest scope |

The mandatory user journey is worth more than infrastructure or visual effects. **Spend effort on the UI and correctness, not on extras.**

Email criteria from Qarizmi (also apply): understanding of business constraints, technical choices and their justification, code and UX quality, reproducibility, transparency about what works, what does not, and what we would do with more time.

---

## 3. Explicit non requirements (do NOT build these)

- No authentication, roles, audit workflow or database persistence.
- No full season forecasting, ML training, vector database, RAG corpus or autonomous action.
- No logistics, freight, weather, packaging, variety, calibre, ERP, email or messaging integration.
- No multi product, multi station, multi day optimizer, manual allocation editor or capacity scenario UI.
- No microservices, Kubernetes, event bus, mobile app or spreadsheet clone.
- No paid service. Docker, CI and live deployment are bonuses only, done last if time remains.
- No generic mathematical optimizer. Implement the exact deterministic policy in section 5.
- No hidden data cleaning. The workbook is clean. Invalid input is rejected, never repaired.

If you feel tempted to add something outside this scope, stop and ask Abdellah.

---

## 4. Input workbook: exact layout

File: `data/Atlas_Fresh_Production_Commercial_Data.xlsx`. Open it **read only** (`openpyxl.load_workbook(path, read_only=True, data_only=True)`). Never write to it.

Row 1 is a title, row 2 is a note, row 3 is blank. **Headers are on row 4. Data starts on row 5.** Do not rely only on fixed row numbers: find the header row by looking for the expected column names in the first rows, then read data rows until the first fully empty row. Missing sheets or columns are validation errors.

### Sheet `Read Me`
Business rules and public baseline checks. Not parsed by the app.

### Sheet `Farms` (headers A4:K4, 20 data rows)
| Column | Type | Rule |
|---|---|---|
| farm_id | text | Required, unique |
| farm_name | text | Required |
| expected_daily_capacity_t | number | Non negative, at most one decimal |
| expected_A_pct, expected_B_pct, expected_C_pct, expected_D_pct | decimal fraction | Each between 0 and 1, sum = 1.0 per farm (tolerance 1e-6) |
| actual_A_t, actual_B_t, actual_C_t, actual_D_t | number | Non negative multiple of 5 |

### Sheet `Clients` (headers A4:F4, 10 data rows)
| Column | Type | Rule |
|---|---|---|
| client_id | text | Required, unique |
| client_name | text | Required |
| acceptance_mode | text | `EXACT` or `MINIMUM` |
| requested_segment | text | `A`, `B`, `C` or `D` |
| demand_t | number | Non negative multiple of 5 |
| export_price_per_t_eur | number | Positive (assumption: price must be > 0, document it) |

### Sheet `Station`
- Station table: headers A4:C4 (`station_id`, `export_conditioning_capacity_t`, `local_market_ratio`), one data row on row 5 (`STATION-01`, `500`, `0.1`).
  - capacity: positive multiple of 5 (0 or negative is "invalid capacity").
  - local_market_ratio: between 0 and 1.
- Reference price table: header row with `segment`, `reference_export_price_per_t_eur` (currently A16:B16), rows below for A=1500, B=1250, C=1000, D=750. Find the header by name, not by fixed row.
  - Must contain A, B, C and D exactly once each (missing or duplicate segment is an error).
  - Price positive.

---

## 5. Deterministic planning policy (implement EXACTLY)

This is the heart of correctness. Do not change the order of steps. Do not use an LLM anywhere in this logic.

**Quality order:** A > B > C > D. Represent as rank A=0, B=1, C=2, D=3.

**Compatibility:**
- `EXACT X`: accepts segment X only.
- `MINIMUM X`: accepts X or any better segment. Example: `MINIMUM B` accepts B or A.
- **Quality upgrade** of a supply for a client = `rank(requested) - rank(supply)`. 0 means no upgrade. For `MINIMUM C`, prefer C (upgrade 0), then B (1), then A (2).

**Steps:**

1. Validate everything in section 6. If any error exists, do not plan. Return all errors.
2. Quantities: actual A/B/C/D, demand and station capacity are non negative multiples of 5 t. Expected daily capacity may have one decimal.
3. Build available supply from each farm's **actual** A/B/C/D tonnes, one balance per (farm_id, segment). Planned values are only for comparison, never for allocation.
4. Sort clients by `export_price_per_t_eur` descending, break ties by `client_id` ascending.
5. For the current client, keep only compatible (farm, segment) supply with a positive balance.
6. Sort that supply by smallest quality upgrade first, then `farm_id` ascending.
7. Allocate in 5 t steps until one of these happens: client demand is met, compatible supply is exhausted, or station capacity is reached. Station capacity is **shared across all clients** (running total).
8. After all clients: every unexported actual tonne goes to the local market. Local value = residual tonnes x local_market_ratio x reference export price **of the residual fruit's segment**. Reference prices never affect client order or export revenue.
9. Return allocation rows, farm/segment balances, client statuses, shortage reasons and KPIs. Same input always gives the same output.

**Client status:**
- `COMPLETE`: allocated = demand.
- `PARTIAL`: 0 < allocated < demand.
- `UNSERVED`: allocated = 0 (and demand > 0).
- "At risk" = PARTIAL or UNSERVED.
- Edge case: a client with demand 0 is COMPLETE (document as assumption).

**Shortage reason (only for PARTIAL or UNSERVED):**
- If station capacity is exhausted (remaining capacity < 5 t) when this client stops: `STATION_CAPACITY_REACHED`. Capacity takes priority if both happen at once.
- Otherwise: `INSUFFICIENT_COMPATIBLE_SEGMENT`.

**Allocation rows:** merge consecutive 5 t steps into one row per (farm_id, segment, client_id). Each row has: farm_id, segment, client_id, tonnes, quality_upgrade (0..3), price_per_t, revenue_eur, and the processing order (client rank, then row order) so the trace is readable.

**Use exact arithmetic.** Tonnes can be integers internally after validation (multiples of 5). Use `Decimal` for mix fractions, expected tonnes, ratios and money. Round only for display.

### KPI definitions
- Expected segment tonnes (per farm) = expected_daily_capacity_t x expected_segment_pct.
- Segment variance = actual - expected.
- Expected plan total = sum of expected_daily_capacity_t.
- Actual received = sum of all actual tonnes.
- Export volume = sum of allocated tonnes.
- Export rate = export volume / actual received (guard divide by zero: return null and show "n/a").
- Station utilization = export volume / station capacity.
- Local volume = actual received - export volume.
- Export revenue = sum of allocated tonnes x served client price.
- Local value = sum over residual (farm, segment) of tonnes x ratio x segment reference price.
- Total value = export revenue + local value.
- At risk clients = count of PARTIAL + UNSERVED.
- Useful extra (label clearly as indicative): value lost to local = local volume at reference price minus local value.

### Invariants (calculate on every run, return them, and test them)
1. export volume <= station capacity
2. each client allocated <= demand
3. each (farm, segment) allocated <= actual
4. every allocation row is compatible with its client rule
5. export volume + local volume = actual received
6. every allocation and demand is a multiple of 5

If an invariant fails at runtime, return a server error (500) with a clear message. It must never be silently shown as a valid plan.

---

## 6. Server side validation (reject, never repair)

Collect **all** errors in one pass and return them together. Each error object:

```json
{
  "code": "MIX_SUM_INVALID",
  "sheet": "Farms",
  "row": 11,
  "entity_id": "F07",
  "field": "expected_*_pct",
  "message": "Farms, row 11, farm F07: expected mix adds up to 0.90. It must add up to 1.0."
}
```

Messages must be actionable: name the sheet, the row, the farm or client ID and what to fix.

Required checks (at least these codes):

| Code | When |
|---|---|
| SHEET_MISSING | Farms, Clients or Station sheet not found |
| COLUMN_MISSING | A required header is missing |
| ID_MISSING | Empty farm_id or client_id |
| ID_DUPLICATE | Same farm_id or client_id twice |
| VALUE_NOT_NUMBER | A numeric cell is text or empty |
| MODE_INVALID | acceptance_mode not EXACT or MINIMUM |
| SEGMENT_INVALID | requested_segment not A/B/C/D |
| MIX_OUT_OF_RANGE | A mix fraction < 0 or > 1 |
| MIX_SUM_INVALID | Mix fractions do not sum to 1.0 |
| QUANTITY_NEGATIVE | Negative tonnes, demand or capacity |
| QUANTITY_NOT_5T_STEP | Actual, demand or station capacity not a multiple of 5 |
| CAPACITY_DECIMALS | expected_daily_capacity_t has more than one decimal |
| CAPACITY_INVALID | Station capacity missing, 0 or negative |
| RATIO_INVALID | local_market_ratio outside 0..1 |
| PRICE_INVALID | Client price or reference price missing or <= 0 |
| REFERENCE_PRICE_MISSING | A, B, C or D missing in the reference price table |
| REFERENCE_PRICE_DUPLICATE | A segment appears twice |

Float cells from Excel: convert with `Decimal(str(value))`. For the multiple of 5 check, the value must be a whole number and `value % 5 == 0`.

Keep source data and computed results separate in code and in the API response (`source` vs `plan`).

---

## 7. Public baseline (verify against this, never hard code it in app code)

These values must come out of the engine when it runs on the supplied workbook. They are allowed **only in tests**. Evaluators will change inputs, so every number in the UI must be calculated.

### Headline
| Metric | Value |
|---|---|
| Expected plan | 600.0 t |
| Actual received | 560.0 t |
| Station capacity | 500.0 t |
| Actual A / B / C / D | 90 / 160 / 180 / 130 t |
| Expected A / B / C / D | 101.7 / 168.3 / 207.9 / 122.1 t |
| Segment variance A / B / C / D | -11.7 / -8.3 / -27.9 / +7.9 t |
| Export volume | 500.0 t |
| Export rate | 89.3% |
| Local volume | 60.0 t |
| Export revenue | EUR 549,500 |
| Local value | EUR 4,500 |
| Total value | EUR 554,000 |
| At risk clients | 3 |

### Clients (in processing order)
| Order | Client | Rule | Price | Demand | Allocated | Status | Reason |
|---|---|---|---|---|---|---|---|
| 1 | C01 | EXACT A | 1500 | 50 | 50 | COMPLETE | |
| 2 | C02 | MINIMUM A | 1450 | 50 | 40 | PARTIAL | INSUFFICIENT_COMPATIBLE_SEGMENT |
| 3 | C03 | EXACT B | 1250 | 60 | 60 | COMPLETE | |
| 4 | C04 | MINIMUM B | 1200 | 70 | 70 | COMPLETE | |
| 5 | C09 | EXACT B | 1150 | 50 | 30 | PARTIAL | INSUFFICIENT_COMPATIBLE_SEGMENT |
| 6 | C05 | EXACT C | 1000 | 60 | 60 | COMPLETE | |
| 7 | C06 | MINIMUM C | 950 | 70 | 70 | COMPLETE | |
| 8 | C10 | EXACT C | 900 | 50 | 50 | COMPLETE | |
| 9 | C07 | EXACT D | 750 | 50 | 50 | COMPLETE | |
| 10 | C08 | MINIMUM D | 700 | 50 | 20 | PARTIAL | STATION_CAPACITY_REACHED |

### Local residual (all Segment D)
| Farm | Segment | Tonnes | Local value |
|---|---|---|---|
| F15 | D | 5 | EUR 375 |
| F16 | D | 20 | EUR 1,500 |
| F19 | D | 5 | EUR 375 |
| F20 | D | 30 | EUR 2,250 |

### Expected allocation rows (43 rows, no quality upgrades in the baseline)
Use this as a test oracle. Format: farm, segment, client, tonnes, revenue EUR.

```
F01 A C01 25 37500    F02 A C01 20 30000    F03 A C01  5  7500
F03 A C02 15 21750    F04 A C02 15 21750    F05 A C02  5  7250    F07 A C02  5  7250
F01 B C03  5  6250    F02 B C03  5  6250    F03 B C03 10 12500    F04 B C03 10 12500
F05 B C03 25 31250    F06 B C03  5  6250
F06 B C04 20 24000    F07 B C04 15 18000    F08 B C04 20 24000    F09 B C04  5  6000
F11 B C04  5  6000    F17 B C04  5  6000
F17 B C09 20 23000    F18 B C09 10 11500
F06 C C05  5  5000    F07 C C05  5  5000    F08 C C05 10 10000    F09 C C05 25 25000
F10 C C05 15 15000
F10 C C06  5  4750    F11 C C06 25 23750    F12 C C06 25 23750    F13 C C06  5  4750
F14 C C06  5  4750    F15 C C06  5  4750
F15 C C10  5  4500    F16 C C10  5  4500    F17 C C10  5  4500    F18 C C10 15 13500
F19 C C10 20 18000
F10 D C07  5  3750    F12 D C07  5  3750    F13 D C07 20 15000    F14 D C07 20 15000
F14 D C08  5  3500    F15 D C08 15 10500
```

Note: the baseline has **no quality upgrades** (MINIMUM clients are fully served by their exact segment or run out). The upgrade logic must still be implemented and tested with synthetic data, and the UI must still show the upgrade column ("none" when 0).

### Farm variances (for UI sanity checks)
Biggest gaps today: F20 C -18.9 / D +21.9, F18 B -12.4, F13 D -8.0, F07 B -7.4, F01 A -6.5, F19 C -6.4, F04 A -6.0. Farms below total plan: F01, F04, F06, F07, F09, F10, F12, F13, F15, F16, F18, F19. Farms above: F05, F08, F11, F14, F17, F20. F02, F03 on plan.

### Why the 3 clients are at risk (the story the UI must make obvious)
- **C02** (MINIMUM A, short 10 t): Segment A is 11.7 t below plan. A farms F01 (-6.5), F04 (-6.0) and F03 (-1.0) missed their A target. C01 pays more for A, so it is served first.
- **C09** (EXACT B, short 20 t): Segment B is 8.3 t below plan (F18 -12.4, F07 -7.4, F06 -3.0, F09 -1.8). C03 and C04 pay more and take B first. C09 cannot accept A or C.
- **C08** (MINIMUM D, short 30 t): not a quality problem. The station reached 500 t. 60 t of D (F15, F16, F19, F20) stay unexported and go local for EUR 4,500 instead of about EUR 45,000 at reference price.

The server should compute these links (see `risk_links` in section 8) so the UI and the assistant can show them. Do not hard code this text.

---

## 8. Architecture

Simple monorepo. One FastAPI server, one React client. No database. Stateless except a small in memory cache of the last computed plans (keyed by input hash) for the assistant.

```
atlas-fresh-planner/
  CLAUDE.md
  README.md
  AI_USAGE.md                  # AI tools used, what was verified, time spent, omissions
  Makefile                     # setup, dev, test, build, start
  .env.example                 # AI_PROVIDER=none, keys empty, never commit .env
  .gitignore
  data/
    Atlas_Fresh_Production_Commercial_Data.xlsx   # read only seed
  docs/
    brief.pdf
    README_original.md
  backend/
    requirements.txt           # fastapi, uvicorn[standard], pydantic, openpyxl, httpx, python-multipart, pytest
    app/
      main.py                  # FastAPI app, CORS for dev, serves frontend/dist in prod
      config.py                # settings from env (DATA_PATH, AI_PROVIDER, keys, timeouts)
      api/
        routes_plan.py
        routes_assistant.py
        errors.py              # error response models and handlers
      domain/
        models.py              # Pydantic models: Farm, Client, Station, ReferencePrice, SourceData
        segments.py            # quality order, compatibility, upgrade helpers
      ingest/
        workbook_reader.py     # openpyxl read only, header finding, raw rows
        validation.py          # all checks, returns list[ValidationError] or SourceData
      planning/
        engine.py              # pure function: plan(source: SourceData) -> PlanResult
        kpis.py
        comparison.py          # expected vs actual by farm and segment
        risk_links.py          # link client risk to segment/farm variances and capacity
        invariants.py
      assistant/
        questions.py           # the 3 supported question ids
        context.py             # build minimal structured context per question
        providers.py           # NoneProvider, AnthropicProvider, OllamaProvider (httpx, timeout)
        grounding.py           # parse JSON output, check IDs and numbers, reject unknown
        fallback.py            # deterministic summaries, clearly labelled
    tests/
      conftest.py              # seed path, helper to copy workbook to tmp and edit a cell
      test_baseline.py
      test_ordering.py
      test_compatibility.py
      test_limits_and_residual.py
      test_validation.py
      test_api.py
      test_assistant.py
  frontend/
    package.json
    vite.config.ts             # proxy /api to http://localhost:8000
    src/
      main.tsx
      App.tsx
      api/client.ts            # fetch wrapper, typed errors, timeout
      api/types.ts             # mirrors backend Pydantic models
      lib/format.ts            # tonnes, EUR, percent formatting
      components/...
      views/Overview.tsx
      views/ProductionView.tsx
      views/CommercialView.tsx
      views/AllocationsView.tsx
      views/AssistantPanel.tsx
```

The planning engine must be a **pure function** (no file access, no globals, no time, no randomness). This makes it easy to test and guarantees determinism.

### API design

All routes under `/api`. JSON only. Types are Pydantic models and mirrored in `frontend/src/api/types.ts`.

| Method | Route | Purpose |
|---|---|---|
| GET | `/api/health` | `{status: "ok", ai_provider: "none" \| "anthropic" \| "ollama", ai_configured: bool}` |
| POST | `/api/plan/seed` | Load the seed workbook from `DATA_PATH`, validate, plan. |
| POST | `/api/plan/upload` | Optional (do after mandatory work): multipart `.xlsx`, same pipeline. Lets evaluators try a modified or invalid file from the UI. Limit size to 2 MB. Never save the file to disk permanently. |
| POST | `/api/assistant/ask` | `{plan_id, question_id}` or `{plan_id, question_text}`. Returns a grounded answer or honest fallback. |

Responses for plan routes:

- **200** valid:
  ```
  {
    plan_id,                 # sha256 of normalized source data
    source: { farms, clients, station, reference_prices },     # parsed input, unchanged
    plan: {
      kpis,
      segment_comparison: [ {segment, expected_t, actual_t, variance_t, exported_t, local_t} ],
      farm_comparison: [ {farm_id, farm_name, expected_total_t, actual_total_t, variance_total_t,
                          segments: {A:{expected_t, actual_t, variance_t, exported_t, local_t}, ...}} ],
      clients: [ {client_id, client_name, processing_order, mode, requested_segment, accepted_segments,
                  price_per_t, demand_t, allocated_t, remaining_t, revenue_eur, status, reason} ],
      allocations: [ {row_id, processing_order, farm_id, segment, client_id, tonnes, quality_upgrade,
                      price_per_t, revenue_eur} ],
      residuals: [ {farm_id, segment, tonnes, reference_price_per_t, local_value_eur} ],
      risk_links: [ {client_id, reason, shortfall_t, segments_involved, farms_below_plan: [{farm_id, segment, variance_t}],
                     served_before: [client_ids that consumed compatible supply first]} ],
      invariants: [ {name, passed, detail} ]
    }
  }
  ```
- **422** invalid input: `{ "error": "VALIDATION_FAILED", "errors": [ ...section 6 objects... ] }`
- **500** server problem: `{ "error": "SERVER_ERROR", "message": "..." }` with no stack trace to the client.

No timestamps inside `plan` (keeps output byte for byte deterministic). Put any timing in response headers or logs only.

---

## 9. The workspace UI (40 points, give it the most care)

One coherent product, not a set of technical screens. Language: English (match the brief). Friendly, business words: "tonnes", "clients at risk", "going to local market", not "residual supply balance".

### Layout at a glance
1. **Header bar:** product name, data health badge (Valid, 20 farms, 10 clients, 1 station / or Errors: N), "Reload today's data" button, optional "Upload workbook" (after mandatory work).
2. **Decision summary (top, always visible):** KPI cards in this order: Planned vs actual (600 t vs 560 t, -40 t), Station use (500 / 500 t, 100%), Export rate (89.3%), Going local (60 t, EUR 4,500), Export revenue, Total value, Clients at risk (3). Below the cards, one plain sentence generated from data, for example: "560 t arrived versus 600 t planned. The station is full at 500 t. 3 clients are short and 60 t of Segment D go to the local market."
3. **"What changed and who it hits" section (the key connection):** one card per segment A/B/C/D showing expected, actual, variance, exported, local, and the at risk clients linked to it (from `risk_links`). Plus a capacity card linking C08 and the local residual. Clicking a client or farm here jumps to the filtered detail.
4. **Tabs** (real ARIA tabs, arrow key navigation):
   - **Production:** 20 farms table. Columns: farm, expected capacity, actual total, variance, A/B/C/D actual with variance shown next to each (sign plus small arrow, not only color), local tonnes. Sort by biggest negative variance. Highlight farms with local tonnes.
   - **Commercial:** 10 clients table in processing order. Columns: order, client, rule (for example "MINIMUM B, accepts A or B"), price, demand, allocated, remaining, revenue, status badge (text plus icon, not only color), reason in plain words ("Not enough Segment B today" / "Station full at 500 t"). Short progress bar for allocated vs demand.
   - **Allocations:** all rows with farm, segment, client, tonnes, upgrade ("none" or "+1 level"), price, revenue. Filters for farm, client, segment (plain selects). Footer totals. A final group "Local market" listing residual rows with value.
5. **Assistant panel** (right side on 1440 px, collapsible drawer or bottom section on 1024 px).

### Traceability
- Clicking a client row opens a small detail panel: which farms and segments served it, tonnes, revenue, and if at risk, why (from `risk_links`).
- Clicking a farm row opens detail: expected vs actual per segment, where each segment went (clients or local).
- Every ID shown (F07, C09, Segment B) is a clickable link that sets the matching filter. The assistant citations use the same links.

### States (all mandatory)
- **Empty:** no plan loaded yet. Clear call to action "Load today's data".
- **Loading:** skeletons for KPI cards and tables, button disabled with "Loading...".
- **Validation error:** replace the workspace with a clear panel: "The workbook has N problems. Nothing was calculated." List each error (sheet, row, ID, message). Buttons: "Reload today's data" (seed) and, if upload exists, "Upload a corrected file". Never show a partial plan.
- **Server error or network failure:** message in plain words, "Try again" button, keep the last valid plan visible but clearly marked as "Last successful plan" if one exists.
- Status messages use `aria-live="polite"`.

### Accessibility and layout
- Fully usable with keyboard: tab order, visible focus ring, Enter/Space on clickable rows, Escape closes panels.
- Semantic tables (`<table>`, `<th scope>`), labels on filters, buttons are `<button>`.
- Do not rely on color alone for status or variance (use text, sign, icon).
- Check color contrast (WCAG AA).
- Design and test at **1024 px** and **1440 px** width. No horizontal page scroll; wide tables scroll inside their own container with a sticky header.
- Number formatting: tonnes with one decimal where needed ("11.7 t"), EUR with thousands separators ("EUR 549,500"), percent with one decimal.

Charts, drag and drop, multiple pages: optional. A simple bar for planned vs actual per segment is nice if time allows (plain SVG or Recharts), but tables and cards come first.

---

## 10. Grounded planning assistant (read only)

The assistant **explains** the plan the engine already produced. It never calculates, changes allocations, confirms execution or writes anything.

### Supported questions (preset buttons)
1. `at_risk_clients`: Which clients are at risk and why?
2. `segment_gaps`: Which farm/segment gaps matter most today?
3. `local_residual`: Why are the tonnes going local and what is their estimated value? (Do not hard code "60 t" in the question label; use the computed number.)

Also a small free text box. Free text that does not match a supported topic, or whose answer is not in the data, must return "This information is not available in today's inputs or plan."

### Provider paths
Config from env (`.env.example` documents all):
- `AI_PROVIDER=none` (default): no model call.
- `AI_PROVIDER=anthropic` with `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` (default `claude-haiku-4-5-20251001`). Call the Messages API with httpx.
- `AI_PROVIDER=ollama` with `OLLAMA_URL` (default `http://localhost:11434`) and `OLLAMA_MODEL` (default `llama3.1`). Free local path.
- `AI_TIMEOUT_SECONDS` (default 20).

Implement at least one real path (Ollama and/or Anthropic). Both share the same interface: `generate(system: str, context: dict, question: str) -> str`.

### Minimal context
Build a small JSON context per question from the plan only. Examples:
- `at_risk_clients`: at risk clients (id, rule, demand, allocated, shortfall, reason), their `risk_links`, station capacity and export volume.
- `segment_gaps`: segment comparison, top farm/segment negative and positive variances (for example top 8 by absolute value), linked at risk clients.
- `local_residual`: residual rows, local value, ratio, reference prices of involved segments, capacity status, C08 style capacity links.
Do not send the full workbook or all 43 allocation rows unless the question needs them.

### Required output format from the model
System prompt tells the model: use only the context, never compute new numbers, cite IDs, answer in 3 to 6 short sentences, respond with JSON only:
```json
{ "answer": "text", "citations": ["C02", "F01", "Segment A"], "unavailable": false }
```

### Grounding validation (server side, before anything reaches the UI)
1. Strip code fences, parse JSON. Invalid JSON -> `INVALID_OUTPUT` state.
2. Every ID in `citations` and every ID found in `answer` by regex (`\bF\d{2}\b`, `\bC\d{2}\b`, `Segment [ABCD]`) must exist in the plan. Unknown ID -> reject the whole answer (`INVALID_OUTPUT`, reason "unknown ID").
3. Every number in `answer` must match a number present in the context (normalize "549,500", "89.3%", "11.7 t"). Unmatched number -> reject.
4. A supported answer must have at least one citation.
5. `unavailable: true` -> show the honest "not available" message.

### Assistant response to the UI
```
{ "mode": "ai" | "deterministic_summary" | "unavailable" | "error",
  "provider": "anthropic" | "ollama" | "none",
  "answer": "...",
  "citations": [ {"id": "C02", "type": "client"} ],
  "error_code": null | "NO_KEY" | "TIMEOUT" | "PROVIDER_ERROR" | "INVALID_OUTPUT" }
```

### Honest states in the UI
- No key or no local model: banner "AI is not configured. Showing a deterministic summary generated by the planning engine (no AI)." Then the summary from `fallback.py`, clearly labelled.
- Timeout or provider error: "The AI provider did not answer (timeout). No AI answer is shown." plus a button to show the deterministic summary.
- Invalid output: "The AI answer was rejected because it mentioned data that is not in today's plan." plus deterministic summary option.
- Never display fake AI text. The label "AI answer" appears only for validated model output.

---

## 11. Tests

Run with `make test` (or `cd backend && python -m pytest -q`). Build invalid workbooks inside tests by copying the seed to `tmp_path` with openpyxl and editing one cell. Do not commit extra binary fixtures. Engine tests can also build `SourceData` objects directly in Python.

Minimum set (4 to 6 meaningful policy tests plus assistant checks):

1. **Baseline** (`test_baseline.py`): engine on the seed workbook matches every number in section 7: KPIs, 10 client statuses and reasons, 43 allocation rows, residual rows. Also run twice and assert identical output (determinism).
2. **Ordering** (`test_ordering.py`): clients processed by price descending, tie broken by client_id. Synthetic case where a lower client_id with equal price wins scarce supply.
3. **Compatibility and best fit** (`test_compatibility.py`): EXACT never receives other segments. MINIMUM receives same or better. Smallest upgrade first, then farm_id. Synthetic case that produces a real upgrade (for example MINIMUM C with no C supply gets B before A).
4. **Hard limits and reasons** (`test_limits_and_residual.py`): all invariants hold on seed and on modified inputs (for example capacity 450, demand changes). `STATION_CAPACITY_REACHED` vs `INSUFFICIENT_COMPATIBLE_SEGMENT`. UNSERVED client case.
5. **Local residual** (same file): export + local = actual, local value uses the residual segment's reference price, changing a reference price changes local value but not export revenue or client order.
6. **Input changes change outputs**: changing a valid input (capacity to 450, a farm's actual A) changes KPIs. Proves no hard coding.
7. **Validation** (`test_validation.py`, parametrized): duplicate farm ID, missing client ID, invalid mode, invalid segment, mix sum 0.9, mix fraction 1.2, negative actual, actual 12 t (not a 5 t step), capacity 0, missing reference price for C. Each returns the right code, sheet and entity ID, and planning does not run.
8. **API** (`test_api.py`): `/api/plan/seed` returns 200 with expected shape. Invalid workbook returns 422 with errors. Error response never leaks a stack trace.
9. **Assistant** (`test_assistant.py`, use a fake provider, no network):
   - Grounded check: fake provider returns JSON citing C02, C09, C08 with numbers from context -> accepted, `mode="ai"`.
   - Unknown ID check: answer cites C99 or F42 -> rejected, `INVALID_OUTPUT`.
   - Provider failure check: provider raises timeout -> `mode="error"`, `error_code="TIMEOUT"`, no answer text shown as AI.
   - No key -> `mode="deterministic_summary"`, labelled.
   - Unsupported question -> `mode="unavailable"`.

Frontend tests are optional. If time allows, a couple of Vitest tests for `format.ts` and the validation error view.

---

## 12. Commands and reproducibility

Prerequisites: Python 3.11+, Node.js 20+, npm, make (document raw commands too for people without make).

```
make setup   # python -m venv backend/.venv, pip install -r backend/requirements.txt, npm ci in frontend
make dev     # backend: uvicorn app.main:app --reload --port 8000 ; frontend: vite on 5173 with /api proxy
make test    # backend pytest (and frontend tests if any)
make build   # npm run build (tsc + vite build) -> frontend/dist
make start   # production like: FastAPI serves frontend/dist and /api on http://localhost:8000
```

Rules:
- A clean clone must work using only README commands. Test this at the end: fresh clone into a temp folder, run setup, test, build, start.
- Commit `package-lock.json`. Pin Python dependency versions in `requirements.txt`.
- `.env` is gitignored. `.env.example` is committed with empty keys. The app runs with no `.env` at all (AI_PROVIDER defaults to none).
- `DATA_PATH` defaults to `data/Atlas_Fresh_Production_Commercial_Data.xlsx` relative to repo root.
- Bonus only, at the very end: Dockerfile + docker-compose, GitHub Actions running tests, live deployment.

---

## 13. Deliverables checklist

- [ ] Git repository with source code and **meaningful commit history** (small commits per milestone, clear messages).
- [ ] `README.md` (concise) with: what it is, prerequisites, one clean start path, test and build commands, architecture (short diagram or list), API summary, planning policy summary, assumptions, known limitations, next three production steps, how to enable AI (Ollama or API key).
- [ ] `AI_USAGE.md`: AI tools used (Claude Code, Claude chat), how they were used, what Abdellah verified by hand (baseline numbers, invariants, UI states), approximate time spent, intentional omissions.
- [ ] Automated tests for policy, constraints, validation and assistant boundaries.
- [ ] 3 to 5 minute walkthrough video aimed at Production and Commercial users (outline in section 15).
- [ ] Optional live URL (never replaces clean clone reproducibility).
- [ ] Reply email to Qarizmi before 18 September 2026: repo URL (plus access if private), video URL, optional live URL, time spent.
- [ ] No credentials, API keys or real client data anywhere in the repo or video.

### Acceptance checklist from the brief (all must pass)
| ID | Pass condition |
|---|---|
| A | App shows 600 t expected, 560 t actual, A/B/C/D totals and 500 t capacity |
| B | Calculates 500 t export, 60 t local, 89.3% export rate and all public values |
| C | C02 and C09 partial for segment shortage, C08 partial because station capacity reached |
| D | Every exported tonne resolves to one farm, segment and client; every residual resolves to local |
| E | No demand, farm segment balance or station capacity exceeded |
| F | Invalid IDs, modes, segments, mix, quantities or capacity rejected server side |
| G | Supported answers cite real IDs; unsupported questions and provider failure are honest |
| H | A manager identifies gaps, at risk clients and local impact without narration |
| I | Clean clone starts, tests and builds using only documented commands |

---

## 14. Work plan and milestones (commit after each)

Track rough hours in `AI_USAGE.md` as you go. Target total 10 to 12 h.

**M0. Scaffold (0.5 h)**
- [ ] Repo structure, `.gitignore`, `.env.example`, Makefile, backend and frontend skeletons, `/api/health`, Vite proxy.
- [ ] Copy kit files into `data/` and `docs/`.
- Commit: `chore: scaffold FastAPI backend and React frontend`

**M1. Ingest and validation (1.5 h)**
- [ ] `workbook_reader.py` with header detection, read only.
- [ ] Pydantic domain models.
- [ ] `validation.py` with all codes in section 6 and actionable messages.
- [ ] `test_validation.py`.
- Commit: `feat(ingest): read and validate workbook with actionable errors`

**M2. Planning engine (1.5 h)**
- [ ] `segments.py`, `engine.py` (pure), `comparison.py`, `kpis.py`, `invariants.py`, `risk_links.py`.
- [ ] Tests 1 to 6 from section 11. Baseline must match section 7 exactly.
- Commit: `feat(planning): deterministic allocation policy with KPIs and invariants`

**M3. API (0.5 h)**
- [ ] `/api/plan/seed`, error handlers (422, 500), plan cache by `plan_id`.
- [ ] `test_api.py`.
- Commit: `feat(api): plan endpoint with validation and error responses`

**M4. Workspace UI (4 to 4.5 h)**
- [ ] API client and types, format helpers.
- [ ] Empty, loading, validation error, server error states.
- [ ] Decision summary and generated sentence.
- [ ] Segment "what changed and who it hits" cards.
- [ ] Production, Commercial, Allocations tabs with filters and click to trace.
- [ ] Client and farm detail panels.
- [ ] Keyboard and ARIA pass, check at 1024 px and 1440 px.
- Commits per view, for example `feat(ui): decision summary and segment impact cards`

**M5. Assistant (1.5 h)**
- [ ] Questions, context builder, providers (none + Ollama and/or Anthropic), grounding, fallback.
- [ ] `/api/assistant/ask` and the panel with all honest states.
- [ ] `test_assistant.py`.
- Commit: `feat(assistant): grounded read only explanations with honest fallback`

**M6. Delivery (1 to 1.5 h)**
- [ ] README, AI_USAGE.md.
- [ ] Clean clone test.
- [ ] Record video.
- Commit: `docs: README, AI usage note and limitations`

**Stretch (only if time remains, in this order):** upload endpoint and UI, small segment chart, Dockerfile, CI, live deploy.

If running late, cut from the bottom of the stretch list first, then simplify visuals. Never cut: correct engine, validation, the 4 mandatory states, the Production to Commercial link, assistant honesty, README.

---

## 15. Walkthrough video outline (3 to 5 min, for Production and Commercial users)

1. (30 s) The problem: daily committee, spreadsheets, 600 t planned, 560 t arrived, 500 t station.
2. (60 s) Decision summary: read the top cards and sentence. 3 clients at risk, 60 t local.
3. (60 s) Production view: Segment A and B gaps, which farms missed. F20 D surplus.
4. (60 s) Commercial view and trace: C02, C09 short on quality, C08 short on capacity. Click C09 to see which farms served it and why C03 and C04 came first.
5. (30 s) Local market: the 60 t D by farm and their EUR 4,500 value versus export value.
6. (30 s) Assistant: ask a question, show citations, show honest no key state.
7. (30 s) Robustness: load an invalid workbook or show a validation error; mention tests, limits and next steps.

---

## 16. Rules for Claude Code while working

1. Follow the milestones in order. Do not start UI work before the engine matches the baseline.
2. Run tests after every meaningful change. Do not mark a milestone done with failing tests.
3. Never hard code baseline numbers, IDs or explanations in app code. Only tests may contain them.
4. Never use an LLM for choosing farms or clients, computing quantities, enforcing limits or producing KPIs.
5. Never modify files in `data/`.
6. Keep dependencies minimal. Allowed without asking: fastapi, uvicorn, pydantic, openpyxl, httpx, python-multipart, pytest, react, react-dom, typescript, vite, tailwindcss, and optionally @tanstack/react-query and recharts. Ask Abdellah before adding anything else.
7. Type everything: Pydantic models on the server, TypeScript strict mode on the client. No `any` unless justified in a comment.
8. Small focused commits with clear messages (conventional style). Meaningful history is graded.
9. Never commit secrets. Never print API keys in logs.
10. When something is ambiguous, pick the simplest reasonable choice, write it under "Assumptions" in the README, and tell Abdellah.
11. Keep `AI_USAGE.md` honest: note what Claude generated and what Abdellah reviewed or changed.
12. Respect the time box. If a task is growing, stop, report, and propose a smaller version.
13. Plain language and no em dashes in all written text (see section 0).

### Known assumptions to document in README
- Client price must be > 0; reference prices must be > 0.
- Demand 0 client is COMPLETE with no allocation.
- If capacity and supply run out at the same time, reason is `STATION_CAPACITY_REACHED`.
- Mix sum tolerance is 1e-6 (Excel stores decimals as floats).
- Expected capacity is only for comparison and may have one decimal; it is not required to be a 5 t step.
- The brief's README refers to `Qarizmi_Universal_Weekend_Technical_Assessment.pdf`; the kit file is named `Qarizmi_Atlas_Fresh_Weekend_Technical_Assessment.pdf` (same brief). Stored as `docs/brief.pdf`.