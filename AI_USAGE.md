# AI usage

Honest note on how this project was built.

## Tools

- **Claude (chat, claude.ai)** to understand the brief, to draft `CLAUDE.md` together
  with Abdellah, and to review screenshots and progress along the way.
- **Claude Code (Opus 5)** in the terminal, driven by that `CLAUDE.md`. It wrote the
  backend, the tests and the frontend, ran the test suite, and took screenshots of the
  running app with headless Chrome to check the layout.
- The product itself runs with no AI key. The planning engine is plain deterministic
  Python and never calls a model.

## How the work was split

`CLAUDE.md` was drafted with Claude chat and reviewed by Abdellah: the business rules,
the exact planning policy, the evaluation weights and the milestone plan. Abdellah then
reviewed each milestone and gave the next direction. Claude Code implemented the
milestones and reported what it checked.

| Milestone | Built by Claude Code | Reviewed or decided by Abdellah |
|---|---|---|
| M0 scaffold | repo layout, Makefile, `.env.example`, FastAPI health route, Vite and Tailwind setup | approved the stack and the layout |
| M1 ingest and validation | workbook reader with header detection, all validation codes, 27 tests | asked for strict `acceptance_mode` and `requested_segment` after seeing the first version normalise case and spaces |
| M2 planning engine | pure engine, KPIs, comparisons, risk links, invariants, 48 tests | asked for the baseline to be proven value by value against section 7 before any UI work |
| M3 API | plan endpoint, error handlers, plan cache, 10 tests | asked for the capacity 450 check on a temporary copy |
| M4 workspace UI | API client, the four states, decision summary, segment impact section, the three tabs | reworked the top of the page himself in the brief he gave: order of the cards, the sentence at the top, colour rules, the "needs attention" grouping; chose to keep highlight and scroll in the tables and filters only in Allocations; specified the two gap lines of the planned versus actual card |
| UI review rounds | the reworked decision summary, the segment impact section, the tabs, then neutral cards with status carried by a badge | drove every round: card order and grouping, the colour rule, the two gap lines, the badge wording, no wrapping in the Commercial table |
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
- **The assistant was run against a real model.** Google Gemini `gemini-3.6-flash`,
  on the free tier, answered all three questions. Ten of the ten answers that reached
  the model passed the grounding checks, in 2 to 3 seconds each. An eleventh burst of
  calls hit the free tier quota and returned the honest provider error state, which is
  the correct behaviour.
- **Ollama could not be used on this machine.** llama3.1 (8B, 4.9 GB) was installed on
  an Apple M2 with 8 GB of memory. A trivial 29 token prompt took 2 minutes 25 seconds,
  all three questions ran past the timeout, and the machine froze and had to be
  restarted. Ollama and the model were removed. The one thing it did show is that the
  timeout state works with a real provider behind it.
- **Three real defects were found by testing against a real model**, and none of them
  were fixed by weakening a check:
  1. The first model answered with valid JSON that was cut in half. The cause was the
     model spending 767 of its 800 token output budget on internal thinking. Fixed in
     the provider by raising the budget and turning thinking off, which also made it
     three times faster. The provider now also reports a truncated answer as a provider
     limit instead of letting it fail later as unreadable JSON.
  2. A correct answer was rejected for citing "segment C" in lower case. The parser now
     reads the label in any case, which means it also validates segment mentions it
     used to skip, so it checks more than before, not less.
  3. A correct answer was rejected for writing "27.9 t below plan" when the plan holds
     a variance of -27.9. The number rule now accepts the magnitude of a context
     number as well as the number itself, and nothing else: no sums, no rounding, no
     percentages. Every number in an answer still has to trace back to one the server
     produced. **This is the only change to a check and it is worth a second opinion.**
- **A test isolation bug was found at the same time.** The suite read the developer's
  own `.env`, so once a real key was configured the no-key tests failed. Tests now run
  on the shipped defaults whatever the machine has configured.
- **Abdellah opened the app in a browser** at both widths after each UI step and gave
  the corrections that are in the commit history.

## Time spent

**12 hours in total**, which is the upper end of the 10 to 12 hour time box in the brief.

This is the figure Abdellah reported. No time is estimated in this file. An earlier
version carried a per milestone table of hours that Claude Code had guessed rather than
measured, and it was wrong, so it was removed.

## Intentional omissions

Listed with the reasons in `README.md`. In short, and on purpose: no client and farm
detail panels, no upload endpoint, no authentication, no database, no chart, no Docker
and no CI.
