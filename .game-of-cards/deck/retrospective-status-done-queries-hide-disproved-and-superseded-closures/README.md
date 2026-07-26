---
title: retrospective-status-done-queries-hide-disproved-and-superseded-closures
summary: "The retrospective skill gathers closure history with `goc --status done --json` at all three of its query sites, so `disproved` and `superseded` cards are structurally invisible to it — even though its own Step 3 instructs the agent to look for \"Cards closed with disproved or superseded\". On this deck that hides 13 of 495 closures and under-reports the 30-day velocity line as 67 instead of 69. The retro's most diagnostic population — the hypotheses that turned out wrong — never reaches the analysis."
status: open
stage: null
contribution: medium
created: "2026-07-26T12:44:16Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
draft: true
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — every terminal closure is reachable from the skill's closure queries
  - [ ] TDD: a regression test asserts no closure-gathering site in `goc/templates/skills/retrospective/SKILL.md` scopes to `--status done`, and that the terminal-status set it filters on is read from `engine.TERMINAL_STATUSES` rather than hand-listed
  - [ ] MECHANICAL: all three query sites in `retrospective/SKILL.md` (Context block, Step 1, Step 5) gather across every terminal status, and Step 3's disproved/superseded bullet is reachable from the population Step 1 produces
  - [ ] MECHANICAL: `deck/SKILL.md`'s "Recently closed cards" verb row no longer advertises a `done`-only command under a closure-wide label (`deck/SKILL.md` has ~90 bytes of headroom under its 10,000-byte cap in `tests/test_skill_body_size.py` — keep the edit inside it)
  - [ ] MECHANICAL: the five mirrors of `retrospective/SKILL.md` are back in sync — four via `python scripts/sync_plugin_assets.py`, the OpenClaw port via `python3 scripts/port_skills_to_openclaw.py`
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` green and `uv run goc validate` clean
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

`uv run python .game-of-cards/deck/retrospective-status-done-queries-hide-disproved-and-superseded-closures/reproduce.py`:

```
engine TERMINAL_STATUSES        : disproved, done, superseded
closures written to the deck    : 3
    disproved   probe-disproved-card  closed_at=2026-07-26T12:44:48Z
    done        probe-done-card  closed_at=2026-07-26T12:44:48Z
    superseded  probe-superseded-card  closed_at=2026-07-26T12:44:48Z

`goc --status done --json` yields: 1
    done        probe-done-card

closures the retrospective cannot see: 2
    probe-disproved-card
    probe-superseded-card

`--status done --json` occurrences in goc/templates/skills/retrospective/SKILL.md: 4
   across 3 query sites: Context block; Step 1 — Gather recent closures; Step 5 — Velocity feel
   (the Context block carries the bootstrap + bare-goc fallback pair)
   contradicted instruction (SKILL.md Step 3): "Cards closed with `disproved` or `superseded` — what was wrong?"

[FAIL] the skill's closure queries scope to `done`, so 2 of 3 closures are invisible to the retrospective that explicitly asks about them.
```

On this repo's own deck the same query gap hides 13 of 495 closures:

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

## Fix

1. `goc/templates/skills/retrospective/SKILL.md` — make all three
   closure-gathering sites span every terminal status.
   - Step 1 and Step 5 already post-process the JSON in Python, so the
     minimal change is `--status done` → `--status all` plus an
     explicit `status in {'done','disproved','superseded'}` filter
     beside the existing `closed_at` filter. (`--status all` also
     un-hides draft scaffolds — `goc/engine.py:2699` — but drafts carry
     `closed_at: null`, so the closure filter already drops them.)
   - The Context block has no post-processing, so switching it to
     `--status all` would flood the preview with the open queue. Use
     the engine-native closure query instead — `--closed-since`, which
     auto-extends `--status` to `all` and filters on `closed_at`, the
     same primitive `standup` uses.
2. `goc/templates/skills/deck/SKILL.md:87` — the row labels a
   `done`-only command "Recently closed cards". `--since` is welded to
   `done` by the engine (`goc/engine.py:3762`), so point the row at
   `--closed-since` rather than relabelling around the gap.
3. Regression test — assert the retrospective skill body contains no
   `--status done` closure query, and that the status set it filters on
   is derived from `engine.TERMINAL_STATUSES` rather than hand-listed,
   so a future status addition cannot silently re-open the gap.
4. Re-sync the five mirrors (`scripts/sync_plugin_assets.py` for the
   four claude/codex copies, `scripts/port_skills_to_openclaw.py` for
   the OpenClaw port).
