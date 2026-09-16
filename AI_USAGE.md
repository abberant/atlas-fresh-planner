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
| M4 workspace UI | API client, the four states, decision summary, segment impact section, the three tabs | reworked the top of the page himself in the brief he gave: order of the cards, the sentence at the top, colour rules, the "needs attention" grouping; chose to keep highlight and scroll in the tables and filters only in Allocations; specified the two gap lines of the planned versus actual card |
| M5 assistant | three questions, minimal context per question, the none, Ollama and Anthropic providers, grounding checks, engine summaries, the panel and its honest states, 28 tests | asked for section 10 to be followed exactly, for citations to reuse the clickable ids, and for the panel to sit on the right at 1440 px and collapse at 1024 px |

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
- **The assistant boundary** is checked by 28 tests with a fake provider and no network:
  a grounded answer is accepted, an answer naming C99 or F42 is rejected, an invented
  number is rejected, an answer with no citation is rejected, a timeout and a provider
  failure stay honest, the default no key path returns the engine summary, and an
  unsupported question never reaches a provider at all.
- **The real HTTP path** of the Ollama provider was exercised once against a local stub
  server, to check that a validated answer reaches the screen labelled as an AI answer,
  and once against a dead port, to check the provider error state.
- **Abdellah opened the app in a browser** at both widths after each UI step and gave
  the corrections that are in the commit history.

## Time spent

**About 1 hour of Abdellah's time so far.**

That is the number that matters for this assessment, and it is the one he reported.
The work went fast because `CLAUDE.md` was written first, so each milestone was one
instruction and one review instead of a conversation.

An earlier version of this file carried a per milestone table of hours. Claude Code had
estimated those numbers rather than measured them, and they were wrong. They are removed.
No time is estimated here.

## Intentional omissions

Listed with the reasons in `README.md`. In short, and on purpose: no client and farm
detail panels, no upload endpoint, no authentication, no database, no chart, no Docker
and no CI.
