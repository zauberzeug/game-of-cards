---
title: standup-next-up-shows-two-cards-not-three-whenever-any-card-is-active
summary: "Section 5 of the standup skill promises \"the top 3 open `human_gate: none` cards by value score\" but ships `goc --ready | head -5`, a line budget that assumes two lines of table chrome. The engine prepends a conditional one-line `ACTIVE:` banner to stdout whenever any card is claimed outside the open queue, so the budget becomes three lines of chrome and two rows. Standup then under-reports the pull queue by one card in exactly the situation it is built for, at any deck size — unlike the overflow failure the head-N umbrella card tracks."
status: done
stage: null
contribution: medium
created: "2026-09-16T05:18:55Z"
closed_at: "2026-09-16T05:24:52Z"
human_gate: none
advances:
  - skill-context-blocks-truncate-deck-output-hiding-active-cards-and-breaking-json
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — Section 5's command yields 3 rows on both scratch decks (with and without an active card). It exits 1 on the pre-fix template.
  - [x] TDD: a regression test under `tests/` extracts the Section 5 bash block from `goc/templates/skills/standup/SKILL.md` AND from all five shipped mirrors and executes it against a scratch deck that holds an active card, asserting the promised 3 rows. It must fail on today's tree.
  - [x] MECHANICAL: only `goc/templates/skills/standup/SKILL.md` is hand-edited; the five mirrors are regenerated (`python scripts/sync_plugin_assets.py`, `python3 scripts/port_skills_to_openclaw.py`) and `--check` is clean for both.
  - [x] MECHANICAL: Section 5's prose still names the row count it delivers, and says why the command drops the banner line, so the next reader does not re-add it.
  - [x] EMPIRICAL: the fixed command is run against this repo's own deck (6 active cards) and its output recorded in `log.md`.
  - [x] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
worker: {who: "claude[bot]", where: main}
---

# standup "Next up" shows two cards, not the three it promises

## Location

`goc/templates/skills/standup/SKILL.md:109-116` — Section 5, and the five
mechanical mirrors of the same fenced block:

| Copy | Line |
|---|---|
| `goc/templates/skills/standup/SKILL.md` (source of truth) | 115 |
| `.claude/skills/standup/SKILL.md` | 115 |
| `.codex/skills/standup/SKILL.md` | 138 |
| `claude-plugin/skills/standup/SKILL.md` | 115 |
| `codex-plugin/skills/standup/SKILL.md` | 138 |
| `openclaw-plugin/skills/standup/SKILL.md` | 108 |

Engine side: `render_active_banner` (`goc/engine.py:3683-3715`) is the
conditional preamble that consumes the budget.

## What's broken

Section 5 states a row count, then bounds the engine's output with a line
count that only adds up when the engine stays silent:

````markdown
## Section 5 — Next up

Show the top 3 open `human_gate: none` cards by value score (the cards
`Skill(pull-card)` would pick next), as a forward look.

```bash
goc --ready 2>/dev/null | head -5 || true
```
````

`head -5` budgets 5 lines for 2 lines of table chrome (the `TITLE …`
header and its `---` rule) plus 3 rows. That arithmetic holds only while
the table is the first thing on stdout.

It is not, whenever any card is claimed. `render_active_banner` prepends
a one-line soft-lock warning **to stdout**, not stderr:

```python
return (
    f"ACTIVE: {len(active)} claimed {noun} outside this open queue: {shown}. "
    "Check `goc --status active` or `goc --board` before claiming new work."
)
```

It fires on every open-queue query — bare `goc` and `goc --ready` alike —
and is suppressed only when `not active` returns early. So the chrome is
2 lines or 3 lines depending on deck state, and the fixed budget silently
spends the third card's row on the banner.

The condition is not an edge case for this skill. Standup's Section 1 is
*about* active cards, and its own Context block at line 20 renders them.
A deck with zero active cards is a deck where standup has nothing to
report in flight — so Section 5 delivers its promised three rows in
exactly the sessions where the section matters least.

## Empirical evidence

`reproduce.py` builds two hermetic scratch decks that differ in one bit —
whether a single card carries `status: active` — and runs the Section 5
command extracted verbatim from the shipped template against each. Because
it reads the command out of `SKILL.md` rather than restating it, the same
script measures both sides of the fix.

Against the pre-fix template it exited 1:

```
Section 5 command, verbatim from the shipped template:
    goc --ready 2>/dev/null | head -5 || true

Prose contract (Section 5): "Show the top 3 open `human_gate: none` cards by value score"

[OK ] deck with no active card: 3 of 3 promised rows
         | TITLE          STATUS  CONTR.  VALUE  GATE  TAGS   DOD
         | -------------  ------  ------  -----  ----  -----  ---
         | ready-alpha    open    high      9.0  none  infra  0/1
         | ready-bravo    open    high      9.0  none  infra  0/1
         | ready-charlie  open    high      9.0  none  infra  0/1

[FAIL] deck with one active card: 2 of 3 promised rows
         | ACTIVE: 1 claimed card outside this open queue: in-flight-card. Check `goc --status active` or `goc --board` before claiming new work.
         | TITLE          STATUS  CONTR.  VALUE  GATE  TAGS   DOD
         | -------------  ------  ------  -----  ----  -----  ---
         | ready-alpha    open    high      9.0  none  infra  0/1
         | ready-bravo    open    high      9.0  none  infra  0/1

DEFECT: Section 5 under-delivers with one active card.
```

Both decks hold five ready cards. The only difference is the banner.

Against the fixed template it exits 0 — both decks now forward 3 of 3
promised rows. On this repo's own live deck (7 active cards, empty ready
queue) the fixed command emits the engine's zero-match line unchanged,
confirming the filter does not swallow the empty-queue report:

```
No cards match (ready: status open, gate none, no active impediment; 1 unauthored draft scaffold hidden — author, then `goc publish <title>`).
```

## Why it matters

Section 5 is the forward look — the cards `Skill(pull-card)` takes next.
Losing its third row is a quiet 33% cut to the only part of standup that
faces forward, and nothing in the forwarded text says a row was dropped:
`head` is a byte filter with no channel for reporting what it removed.

It also degrades precisely when the deck is busiest. The banner's line
count grows only up to a cap (`active[:3]` plus a `+N more` suffix, still
one line), so the loss is a flat one row — but it is present in every
session with any claimed card, which on this repo's own deck is every
session: `goc --status active` lists six.

## Relationship to the head-N umbrella

[`skill-context-blocks-truncate-deck-output-hiding-active-cards-and-breaking-json`](../skill-context-blocks-truncate-deck-output-hiding-active-cards-and-breaking-json/)
catalogues the same tool — a fixed `head -N` bounding an unbounded engine
stream — across six live `!`-blocks, and its trigger is *overflow*: too
many cards for the budget. It explicitly scopes this site out:

> Two further `head -N` occurrences (`scan-deck/SKILL.md:40`,
> `standup/SKILL.md:113`) sit inside fenced code blocks as prose examples.
> They are not live context blocks and are out of scope except as
> documentation.

That scoping left a real defect unfixed, because this failure is not
overflow. It fires on a deck of four cards, needs no surplus, and is
cured without the engine-side bounded renderer the umbrella is parked on
deciding. The umbrella's own DoD anticipates the case — "change them only
if the decision makes them wrong as documentation" — and this card is the
evidence that they are. Hence the `advances` edge: closing this settles
one of the sub-questions the umbrella's decision would otherwise have to
re-open.

The closed predecessor
[`standup-next-up-section-lists-cards-pull-card-would-never-pick`](../standup-next-up-section-lists-cards-pull-card-would-never-pick/)
fixed the *predicate* in this same block (bare `goc` → `goc --ready`) and
left `head -5` untouched; it never examined the line budget.

## Sibling sweep

The shape is "a fixed `head -N` budget calibrated against chrome whose
line count is conditional". Every `head -N` in a shipped skill was checked
against whether the banner reaches it and whether the prose states a count:

| Site | Banner reaches it? | Prose states a count? | Verdict |
|---|---|---|---|
| `standup/SKILL.md:115` (`--ready`) | yes | yes — "top 3" | **this card** |
| `scan-deck/SKILL.md:40` (bare `goc -v`) | yes | no — "a one-line summary" | no contract to violate |
| `pull-card/SKILL.md:42` (`--ready -v`) | yes | no — promises the *last* line | umbrella owns it |
| `pull-card/SKILL.md:30` (`--status active -v`) | no | no | unaffected |
| `next-card/SKILL.md:17` (`--status active -v`) | no | no | unaffected |
| `standup/:24`, `refine-deck/:91`, `retrospective/:17` (`--json`) | n/a | no | umbrella owns it |

`--status active` does not trigger the banner — it warns about claimed
cards *outside* the queried set, and there are none when the query is the
active set itself. Verified by running both queries against a scratch deck
holding one active card.

One site, one card.

## Fix (applied)

The conditional preamble is dropped before the budget, so the 5 lines are
spent on the chrome and rows the prose promises:

```bash
goc --ready 2>/dev/null | grep -v '^ACTIVE:' | head -5 || true
```

This is correct in both directions and needs no engine change:

- **Cards ready, banner present** — the banner is filtered, chrome is back
  to 2 lines, and 3 rows land.
- **Cards ready, no banner** — `grep -v` is a no-op; unchanged behaviour.
- **Queue empty** — the engine's `No cards match (…)` line does not start
  with `ACTIVE:`, so it survives, preserving Section 5's stated contract
  that an empty pull queue "is the day's headline".

Nothing is lost by dropping the banner here: standup renders the active
cards in full one section earlier, from its own Context block
(`SKILL.md:20`, `goc --status active -v`), so the soft-lock warning is
redundant inside Section 5.

Only `goc/templates/skills/standup/SKILL.md` was hand-edited; the five
mirrors were regenerated by `scripts/sync_plugin_assets.py`
(Claude/Codex/dogfood) and `scripts/port_skills_to_openclaw.py`
(OpenClaw), and both `--check` modes are clean. Section 5's prose gained a
paragraph naming why the banner is filtered and why the budget stays at 5,
so the next reader does not undo it.

`tests/test_standup_next_up_row_budget.py` pins the behaviour across the
template and all five mirrors by executing the extracted block against a
scratch deck that holds an active card. It fails on the pre-fix tree — and
it caught all five mirrors in the window between the template edit and the
sync run, which is the drift it exists to prevent.
