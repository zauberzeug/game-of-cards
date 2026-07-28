---
title: retrospective-status-done-queries-hide-disproved-and-superseded-closures
summary: "The retrospective skill gathers closure history with `goc --status done --json` at all three of its query sites, so `disproved` and `superseded` cards are structurally invisible to it — even though its own Step 3 instructs the agent to look for \"Cards closed with disproved or superseded\". On this deck that hides 13 of 495 closures and under-reports the 30-day velocity line as 67 instead of 69. The retro's most diagnostic population — the hypotheses that turned out wrong — never reaches the analysis."
status: done
stage: null
contribution: medium
created: "2026-07-26T12:44:16Z"
closed_at: "2026-07-26T12:57:15Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` extracts the `goc ... --json` queries the skill body prescribes, runs each against a probe deck holding one closure per terminal status, and exits zero only when all three are reachable — verified red on the pre-fix body (`1/3 closures · HIDES probe-disproved-card, probe-superseded-card`) and green after
  - [x] TDD: `tests/test_retrospective_closure_scope.py` asserts (a) no closure query in `retrospective/SKILL.md` narrows `--status` below `all` unless it windows on `--closed-since`, (b) the `TERMINAL = {...}` literal the skill body filters on equals `engine.TERMINAL_STATUSES` so a fourth terminal status turns the test red, (c) `deck/SKILL.md`'s closed-cards verb row is not `done`-only — all three fail on the pre-fix content
  - [x] MECHANICAL: all three query sites in `retrospective/SKILL.md` gather across every terminal status — Context block via `--closed-since 90d`, Steps 1 and 5 via `--status all` plus a terminal filter — and Step 1 now emits each card's `status`, so Step 3's disproved/superseded bullet is answerable from the population it receives
  - [x] MECHANICAL: `deck/SKILL.md`'s "Recently closed cards" verb row points at `goc --closed-since 7d` instead of the `done`-only `--since` form (file at 9,917 B, inside the 10,000 B cap in `tests/test_skill_body_size.py`)
  - [x] MECHANICAL: the five mirrors of `retrospective/SKILL.md` and `deck/SKILL.md` are back in sync — four via `scripts/sync_plugin_assets.py` (8 files), the OpenClaw port via `scripts/port_skills_to_openclaw.py`; both `--check` drift guards green
  - [x] PROCESS: `uv run python -m unittest discover -s tests` green (786 tests) and `uv run goc validate` clean
worker: {who: "claude[bot]", where: main}
---

# retrospective-status-done-queries-hide-disproved-and-superseded-closures

## Location

- `goc/templates/skills/retrospective/SKILL.md:17` — Context block
- `goc/templates/skills/retrospective/SKILL.md:39` — Step 1, "Gather recent closures"
- `goc/templates/skills/retrospective/SKILL.md:119` — Step 5, "Velocity feel"
- `goc/templates/skills/deck/SKILL.md:87` — "Recently closed cards" verb row
- `goc/engine.py:2316` — `TERMINAL_STATUSES = frozenset({"done", "disproved", "superseded"})`

## What's broken

The `retrospective` skill exists to look backwards at closed work. All
three of its closure-gathering queries scope to a single status:

```
!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b --status done --json; else goc --status done --json; fi 2>&1 | head -100`
```

```bash
# Read the last N done cards sorted by closed_at
goc --status done --json 2>/dev/null | \
```

```bash
goc --status done --json 2>/dev/null | \
  python3 -c "
...
counts = {7: 0, 14: 0, 30: 0}
```

But `done` is not the closure set. The engine names the closure set
explicitly, and says so in a comment that pointedly separates it from
the schema enum (`goc/engine.py:2310-2316`):

> `TERMINAL_STATUSES` is NOT a schema enum: "terminal" is a semantic subset

```python
TERMINAL_STATUSES = frozenset({"done", "disproved", "superseded"})
```

So the skill's own Step 3 asks a question its Step 1 population can
never answer:

> - Cards closed with `disproved` or `superseded` — what was wrong?

That instruction is unreachable. A `disproved` card never appears in
`--status done --json`, so the retro's first and most diagnostic
failure-pattern probe — the hypotheses that turned out to be wrong —
silently returns nothing on every run, in every consuming repo.

Step 5 inherits the same scope and therefore mis-states a number it
presents as fact:

> Velocity: `<N>` cards/7d · `<N>` cards/14d · `<N>` cards/30d

The sibling `standup` skill already does this correctly — it reaches
for the engine-native window filter, which auto-extends `--status` to
`all` (`goc/engine.py:3749-3757`) and so spans every terminal status:

```bash
goc --json --closed-since 24h --slim 2>/dev/null | python3 -c "
```

`--status` accepts one status or `all`; there is no `--status closed`
alias, so a client-side filter against `TERMINAL_STATUSES` (or the
`--closed-since` window) is the only way to express "closures".

## Empirical evidence

`reproduce.py` reads the `goc ... --json` invocations out of the skill
body rather than hard-coding them, so it measures whatever the skill
actually prescribes. Against the **pre-fix** body (`git show
HEAD:goc/templates/skills/retrospective/SKILL.md`):

```
engine TERMINAL_STATUSES : disproved, done, superseded
closure queries found in SKILL.md: 1
  goc --status done --json         → 1/3 closures · HIDES probe-disproved-card, probe-superseded-card

closures written to the probe deck: 3
    disproved   probe-disproved-card
    done        probe-done-card
    superseded  probe-superseded-card

Step 3 of the skill asks: "Cards closed with `disproved` or `superseded` — what was wrong?"

   goc --status done --json: hides probe-disproved-card, probe-superseded-card
[FAIL] 1 of 1 closure queries scope below the engine's terminal set, so the population Step 3 asks about never reaches the analysis.
```

Against the shipped body — `uv run python .game-of-cards/deck/retrospective-status-done-queries-hide-disproved-and-superseded-closures/reproduce.py`:

```
engine TERMINAL_STATUSES : disproved, done, superseded
closure queries found in goc/templates/skills/retrospective/SKILL.md: 2
  goc --closed-since 90d --json    → 3/3 closures · reaches every terminal status
  goc --status all --json          → 3/3 closures · reaches every terminal status
...
[OK] every closure query in the skill body reaches all 3 terminal statuses.
```

On this repo's own deck the pre-fix query gap hid 13 of 495 closures:

```
total terminal closures: 495
done-only closures:      482
velocity  7d: true=15  reported=15  (missing 0)
velocity 14d: true=24  reported=24  (missing 0)
velocity 30d: true=69  reported=67  (missing 2)
velocity 90d: true=495 reported=482 (missing 13)
```

The 13 invisible closures are exactly the ones a retrospective wants
most — eight `disproved` rebuttals and five `superseded` reframings,
including `kickoff-skill-descriptions-load-in-sessions-that-never-kick-off`
(2026-07-11) and
`heaviest-skills-re-load-full-methodology-briefing-per-card-cycle`
(2026-07-07), both well inside a default 10-card window.

## Why it matters

Cards closed as `disproved` or `superseded` are the deck's record of
being wrong: a hypothesis that did not survive contact with the code,
or a framing that got replaced. A retrospective that reads only `done`
cards sees only the successes and reports a rosier picture than the
history supports — which is the precise inversion of what the skill is
for. The velocity line compounds it by presenting an understated count
as a measured fact.

This is the consumer that
[record-closure-date-for-disproved-and-superseded-cards](../record-closure-date-for-disproved-and-superseded-cards/)
missed. That card changed `closed_at` from a `done`-only stamp to a
per-terminal-exit stamp *precisely* so per-outcome closure dates would
be queryable, and its DoD called for a sweep of the consumers
("`--since` filter … and any other `closed_at` consumers still behave
correctly with the broader population; document any filters that
should remain done-only"). The `retrospective` skill was never swept,
and it is not a filter that should remain done-only.

Same "done ≠ terminal" conflation as
[closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded](../closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded/),
at a different site: that one is in the engine's closure-integration
guard, this one is in a shipped skill body. Two instances, not yet a
family — fixing this site does not need the architectural card.

## Fix (shipped)

1. `goc/templates/skills/retrospective/SKILL.md` — all three
   closure-gathering sites now span every terminal status.
   - **Steps 1 and 5** already post-processed the JSON in Python, so
     they moved to `--status all` plus an explicit
     `TERMINAL = {'done', 'disproved', 'superseded'}` filter beside the
     existing `closed_at` filter. (`--status all` also un-hides draft
     scaffolds — `goc/engine.py:2699` — but drafts carry
     `closed_at: null`, so the closure filter drops them.) Step 1 also
     emits each card's `status` so Step 3 can name the outcome.
   - **The Context block** has no post-processing, so `--status all`
     there would have flooded the preview with the open queue. It uses
     the engine-native closure query instead — `--closed-since 90d`,
     which auto-extends `--status` to `all` and filters on `closed_at`
     (`goc/engine.py:3749-3757`), the same primitive `standup` uses.
     90d comfortably spans the widest window Step 5 reports.
   - A short paragraph above Step 1 states the invariant, so the next
     editor knows why the query is not `--status done`.
2. `goc/templates/skills/deck/SKILL.md` — the verb row now reads
   `goc --closed-since 7d` / "Recently closed cards (any terminal
   status)". `--since` is welded to `done` by the engine
   (`goc/engine.py:3762`), so the row had to change command, not label.
3. `tests/test_retrospective_closure_scope.py` — three guards: no
   closure query narrows `--status` below `all` unless it windows on
   `--closed-since`; the `TERMINAL = {...}` literal equals
   `engine.TERMINAL_STATUSES` (so a fourth terminal status turns the
   test red rather than silently dropping out); `deck/SKILL.md`'s
   closed-cards row is not `done`-only.
4. Five mirrors re-synced — `scripts/sync_plugin_assets.py` for the
   four claude/codex copies, `scripts/port_skills_to_openclaw.py` for
   the OpenClaw port. Both `--check` drift guards green.

## Not covered here

The OpenClaw port of this skill carries an unrelated, pre-existing
defect visible in the same diff: the porter rewrites `$ARGUMENTS` to
the bare phrase `the user's argument`, and Step 1 interpolates it
inside a single-quoted Python literal — `n = int('the user's
argument'.strip() or '10')` — which is a syntax error. Filed
separately as
[openclaw-porter-arguments-substitution-breaks-single-quoted-python-literals](../openclaw-porter-arguments-substitution-breaks-single-quoted-python-literals/);
it lives in `scripts/port_skills_to_openclaw.py`, not in this skill
body.
