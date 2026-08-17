---
title: file-line-citations-drift-again-within-days-of-every-repair-pass
summary: "Cards address code by bare line number, and a bare line number does not survive ordinary growth. Six days after the 2026-08-10 hygiene pass repaired 329 citations, 227 of them (69%) were wrong again — goc/engine.py grew 6731 to 6979 lines and carried 181 of the failures. Repair is therefore permanent recurring work rather than a fix, and between passes a reader cannot tell a good cite from a rotted one without re-deriving it."
status: open
stage: null
contribution: medium
created: "2026-08-17T02:36:14Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the newest bulk repair pass at least three days old has decayed no more than 25%, measured at HEAD.
  - [ ] PROCESS: a citation form is chosen and recorded in `log.md`, with the reason (see `## Fix options` — the options differ in who pays: author, tooling, or reader).
  - [ ] MECHANICAL: `Skill(create-card)` Step 5 states the chosen form where it says a bug-class card's Location is `file:line`, so newly filed cards conform.
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/SKILL.md` § "Defunct file:line citations" reads against the chosen form — if cites become self-anchoring, the pass verifies rather than relocates, and says so.
  - [ ] TDD: a check that fails on a card citing code that does not contain the cited anchor, proving it can catch an offender rather than passing on an empty list (see `static-source-guards-never-prove-they-can-catch-an-offender`).
  - [ ] MECHANICAL: all five mirrors regenerate — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# `file:line` citations drift again within days of every repair pass

## Location

- `goc/templates/skills/create-card/SKILL.md` § Step 5 — "**Location** — `file:line` (bug-class)". This is where the convention is set.
- `goc/templates/skills/refine-deck/SKILL.md` § "Defunct file:line citations" — the recurring repair the convention makes necessary.
- 841 cites across 155 open cards in this deck are written this way.

## What's broken

Nothing malfunctions. The convention works exactly as specified and still
fails, because a line number is a position and the thing it names is
content. Any edit above the cite moves the content and leaves the number
behind, pointing — silently, and still inside the file — at whatever slid
into that position.

The rate is the finding. This is not slow rot measured over quarters:

| Repair pass | Age | Citations it wrote that are wrong at HEAD |
|---|---|---|
| `9fa3a242` deck move | 103 days | 60 / 60 (100%) |
| `69e1e4f2` first anchored repair | 6 days | 227 / 329 (69%) |
| `f290f5f7` this pass | 0 days | 0 / 273 (0%) |

Two thirds of a repair pass's output was wrong again inside a week. The
cause is unremarkable: `goc/engine.py` grew from 6731 to 6979 lines over
those six days, and 181 of the failures are in that one file. No refactor,
no reorganization — just a week of ordinary work on the most-cited file in
the repo.

So a citation's useful life is shorter than the interval between the passes
that maintain it. Between passes the deck is in its normal state, which is
the state where most cites are wrong. And the reader has no way to tell:
a rotted cite resolves to real code in the right file, so following it
produces confident misreading rather than a visible error.

The repair itself is not cheap, either, and most of it cannot be automated.
The 2026-08-17 pass repaired 320 cites and **declined 236** — 112 whose
anchor line is too short to match uniquely, 81 that match in more than one
place, 42 whose text no longer exists anywhere. Those 236 are not a backlog
that shrinks; they are the permanent residue of a scheme that has to
re-derive an address that was never stable.

## Empirical evidence

`reproduce.py` replays each bulk repair pass in the deck's history and asks
how much of its output survives at HEAD. Measuring per pass rather than
"right now" keeps the number meaningful immediately after a repair:

```
Decay of each bulk citation-repair pass, measured at HEAD:

  commit       age         decayed   subject
  f290f5f7f     0d      0/273   (  0%)  chore(deck): hygiene pass — 2026-08-17
  69e1e4f22     6d    227/329   ( 69%)  chore(deck): hygiene pass — repair 389 drifted file:
  9fa3a2421   103d     60/60    (100%)  deck: move canonical deck from deck/ to .game-of-car

newest pass at least 3 days old: 69e1e4f22, 6 days ago — 227/329 of its citations (69%) are
already wrong, budget 25%
  over that span: goc/engine.py 6731 -> 6979 lines; goc/install.py 1838 -> 1838 lines

DEFECT PRESENT: a bare line number does not survive ordinary code growth, so citation repair
is permanent recurring work and a reader cannot trust a cite between hygiene passes.
```

## Why it matters

A card is meant to be picked up cold. Its Location section is the first
thing a reader follows, and for six days out of every seven it is wrong.
That is a direct hit on the deck's read-pattern guarantee, and it is
invisible to `goc validate`, which never reads citations at all.

It also compounds a second defect. Because repair is routine, second and
third passes over the same cite are the normal case — which is the exact
condition under which the shipped repair recipe corrupts correct
citations. See
[second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/):
that card fixes the recipe, this one questions whether a recipe that has to
run this often is the right answer. Fixing the recipe is necessary either
way and should not wait on this card; solving this one would make the
recipe mostly unnecessary.

Finally it is a standing tax on every hygiene pass. Citation repair was the
largest single item in the 2026-08-17 pass by a wide margin, and it will be
the largest item in the next one, on largely the same cites.

## Fix options

The gate is `none` per this repo's autonomous-filing convention, but the
choice below is a genuine one and a reader who wants to make it
deliberately should raise the gate and record it via `Skill(decide-card)`.
The options differ mainly in who pays.

**A. Self-anchoring cites — carry the text, not just the number.**
Write `goc/engine.py:3819` alongside the line's content, so the cite states
what it expects to find. Rot becomes detectable by reading the card against
the file, with no git archaeology, and repair becomes a verified relocation
instead of an inferred one. Cost: authors write more, and the deck's
existing 841 cites need a migration pass. This also dissolves the 112
trivial-anchor declines, since the anchor no longer has to be recovered
from history.

**B. Symbol-relative cites.** Address `goc/engine.py::_build_parser` rather
than a line. Stable across any edit that does not rename or delete the
symbol, and already how most prose in the card bodies actually refers to
code. Cost: no line granularity inside long functions — and `engine.py`'s
functions are long — plus a resolver for the non-Python surfaces (`.md`,
`.ts`, `.json`) that carry a third of the cites.

**C. Keep line numbers, accept the treadmill, make it cheap.**
Fix the recipe (the sibling card), then run the repair automatically on
every deck commit rather than per hygiene pass, so numbers are never more
than one commit stale. Cost: nothing is gained for the 236 cites the
recipe cannot map, and a wrong automated relocation now lands unreviewed
at commit rate rather than at pass rate — which argues for doing the
sibling card's fix first regardless of what is chosen here.
