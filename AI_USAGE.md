# AI usage

Honest note on how this project was built.

## Tools

- **Claude Code (Opus 5)** in the terminal, driven by `CLAUDE.md` in this repository.
  It wrote the backend, the tests and the frontend, ran the test suite, and took
  screenshots of the running app with headless Chrome to check the layout.
- No other AI tool was used. The product itself runs with no AI key: the planning engine
  is plain deterministic Python and never calls a model.

## How the work was split

Abdellah wrote `CLAUDE.md` (the brief, the policy, the evaluation weights and the
milestone plan), then reviewed each milestone and gave the next direction. Claude Code
implemented the milestones and reported what it checked.

| Milestone | Built by Claude Code | Reviewed or decided by Abdellah |
|---|---|---|
| M0 scaffold | repo layout, Makefile, `.env.example`, FastAPI health route, Vite and Tailwind setup | approved the stack and the layout |
| M1 ingest and validation | workbook reader with header detection, all validation codes, 27 tests | asked for strict `acceptance_mode` and `requested_segment` after seeing the first version normalise case and spaces |
| M2 planning engine | pure engine, KPIs, comparisons, risk links, invariants, 48 tests | asked for the baseline to be proven value by value against section 7 before any UI work |
| M3 API | plan endpoint, error handlers, plan cache, 10 tests | asked for the capacity 450 check on a temporary copy |
| M4 workspace UI | API client, the four states, decision summary, segment impact section, the three tabs | reworked the top of the page himself in the brief he gave: order of the cards, the sentence at the top, colour rules, the "needs attention" grouping; chose to keep highlight and scroll in the tables and filters only in Allocations |

## What was verified, and how

- **The baseline** is checked by `backend/tests/test_baseline.py` against every number in
  section 7 of `CLAUDE.md`: the KPIs, the 10 client statuses and reasons, the 43
  allocation rows with revenue, the 4 residual rows and the farm variances. It also runs
  the engine twice and compares the output byte for byte.
- **No hard coding**: no baseline number or id appears anywhere in `backend/app`. Tests
  change the capacity, a reference price, the local ratio and a farm's actual tonnes and
  assert that the outputs move.
- **Validation** is checked by building broken workbooks in a temporary folder from the
  seed file, one edited cell at a time, so no extra binary fixture is committed.
- **The layout and the keyboard** were checked with headless Chrome at 1024 px and
  1440 px: tab keys and arrow keys, roving tabindex, panels labelled by their tab, no
  horizontal page scroll, every id a real button, every table with `th scope`.
- **Abdellah opened the app in a browser** at both widths after each UI step and gave
  the corrections that are in the commit history.

## Time spent

Approximate, measured across the working session.

| Part | Hours |
|---|---|
| M0 scaffold | 0.5 |
| M1 ingest and validation | 1.5 |
| M2 planning engine | 1.5 |
| Strict validation change | 0.25 |
| M3 API | 0.5 |
| M4 workspace UI, in three reviewed steps | 3.0 |
| Total so far | about 7.25 |

## Intentional omissions

Listed in full in `README.md` at milestone M6. So far, and on purpose: no authentication,
no database, no upload endpoint yet, no detail panels yet, no chart, no Docker, no CI.
