---
title: cli-reference-steers-authors-onto-deprecated-blocked-status-not-the-wait-overlay
summary: "FIXED. The published CLI reference `goc.md` listed `blocked` as one of five unmarked `goc status` target states and never mentioned `goc wait` or the impediment overlay, so following it produced a card that validated OK yet dropped out of every `status: open` query with no reason recorded. purge-blocked-status-from-skills-and-docs soft-deprecated `blocked` across the skills and AGENTS files but its scope never named `goc.md`. Row marked deprecated, `goc wait` row and a migration paragraph added, and a derived guard now fails on any guidance surface offering a status the skill bodies deprecate."
status: done
stage: null
contribution: medium
created: "2026-09-04T04:34:30Z"
closed_at: "2026-09-04T04:45:11Z"
human_gate: none
advances:
  - remove-blocked-from-status-enum-and-migrate-existing-cards
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — the `goc status` row no longer
        offers `blocked` unmarked, `goc.md` names the overlay, and the
        behavioral contrast is recorded.
  - [x] TDD: `tests/test_guidance_accuracy.py` gains a guard that DERIVES
        the deprecated status values from the skill bodies (not a hardcoded
        word list) and fails when a guidance surface lists one as a
        `goc status` target without a deprecation marker. Verified
        non-vacuous against the pre-fix `goc.md`.
  - [x] MECHANICAL: `goc.md`'s "Common verbs" table marks `blocked` as
        deprecated in the `goc status` row and gains a `goc wait` row for
        the impediment overlay, matching the wording precedent set by
        `Skill(advance-card)` and `Skill(card-schema)`.
  - [x] PROCESS: closed sibling `purge-blocked-status-from-skills-and-docs`
        amended with a forward pointer to this card, and both `advances`
        endpoints carry the inverse `advanced_by` edge.
worker: {who: "claude[bot]", where: main}
---

# `goc.md` steers authors onto the deprecated `blocked` status, not the wait overlay

**FIXED.** `goc.md`'s verb table now marks `blocked` deprecated, documents
`goc wait`, and carries the migration instruction; `DeprecatedStatusGuidanceTest`
in `tests/test_guidance_accuracy.py` derives the deprecated set from the skill
bodies so the next surface to drift turns the build red.

## Location

- `goc.md:283` (pre-fix) — the `goc status` row of the **Common verbs** table.
- `goc.md` as a whole — zero mentions of `goc wait`, `waiting_on`, or the
  impediment overlay.
- Published as the CLI reference at `https://game-of-cards.com/goc/` and
  `/goc.md` (`.github/workflows/pages.yml:11-12`), and linked from
  `site/llms.txt:129` as "CLI reference and install recipe".

## What was broken

`goc.md` is the command-level reference. Its verb table said:

```
| `goc status <title> <state>` | Move a card through `open`, `active`, `blocked`, `disproved`, or `superseded`. |
```

`blocked` sat there as one of five equal, unmarked target states. The
authoritative surfaces say the opposite —
`goc/templates/skills/card-schema/SKILL.md:64`:

```
`blocked` is deprecated — split into derived dependency-readiness and
```

and `goc/templates/skills/advance-card/SKILL.md:54`:

```
stuck model"). The legacy `status: blocked` is deprecated; set the
```

`goc/templates/skills/advance-card/reference.md:23-38` carries a whole
**"Deprecated blocked status"** section stating the value "still parses for
backwards compatibility but is being removed in a follow-up release". `goc.md`
carried no such marker, and it never named the mechanism that replaced it — the
`goc wait` impediment overlay was absent from the document entirely, so a reader
had no way to find the correct alternative from the page they were on.

This was a gap in a *closed* card's scope, not new drift. Sibling
[`purge-blocked-status-from-skills-and-docs`](../purge-blocked-status-from-skills-and-docs/)
closed 2026-05-26 with the stated job "Stop recommending `status: blocked`"; its
`## Surfaces` section enumerated `advance-card`, `card-schema`, `deck`,
`templates/AGENTS_GOC.md` and this repo's `AGENTS.md` — and never named
`goc.md`. A repo-wide sweep confirmed `goc.md:283` was the **only** surface
outside `.game-of-cards/deck/` and the generated mirrors still presenting
`blocked` as a normal state: `site/` has zero mentions, and every remaining hit
is either a skill body that marks it deprecated or engine/schema code the
sibling [`remove-blocked-from-the-status-enum-and-validator`](../remove-blocked-from-the-status-enum-and-validator/)
owns.

## Empirical evidence

`uv run python .game-of-cards/deck/cli-reference-steers-authors-onto-deprecated-blocked-status-not-the-wait-overlay/reproduce.py`
— exit 0 after the fix:

```
========================================================================
STATIC: goc.md vs the skill bodies
========================================================================
goc.md `goc status` row:
  | `goc status <title> <state>` | Move a card through `open`, `active`, `disproved`, or `superseded`. The enum still accepts the deprecated `blocked`; use `goc wait` instead. |

goc.md mentions of the replacement mechanism: missing=[]

skill bodies that call `blocked` deprecated (4):
  goc/templates/skills/advance-card/SKILL.md
  goc/templates/skills/advance-card/reference.md
  goc/templates/skills/card-schema/SKILL.md
  goc/templates/skills/card-schema/reference.md

========================================================================
BEHAVIORAL: what following the doc actually produces
========================================================================

A) after the documented `goc status probe-card blocked`:
  goc          -> No cards match (status: open).
  goc validate -> OK  probe-card

B) after the replacement `goc wait probe-card --reason external`:
  goc          -> TITLE       STATUS  CONTR.  VALUE  GATE      TAGS  DOD
  goc          -> ----------  ------  ------  -----  --------  ----  ---
  goc          -> probe-card  open    medium    3.0  decision        0/1
  goc --ready  -> No cards match (ready: status open, gate none, no active impediment).

  contrast holds: the `blocked` flip loses the card from every `status: open`
  query with no reason recorded; `goc wait` keeps it visible and withholds it
  only from `--ready`.

FIXED: goc.md deprecates `blocked` and documents the overlay.
```

The two static checks were verified non-vacuous by re-running them against
`git show HEAD:goc.md` (the pre-fix text): 2 failures, naming the unmarked row
and the missing overlay. The same check against the pre-fix file drives both new
guards to fail, quoting `goc.md:283` verbatim.

## Why it mattered

The doc was not merely stale — following it produced the exact card state the
three-axis model was built to eliminate. Block **A** of the evidence is what a
reader got by running the documented command: the card validates `OK`, so
nothing warns them, and it disappears from `goc`, from every `status: open`
query, and from the autonomous pull queue, with **no impediment reason
recorded**. Block **B** is what the replacement does: the card stays `open` and
visible with its reason attached, and is withheld only from `--ready`. The doc's
advice lost the card; the undocumented alternative kept it.

Two follow-on costs, both now closed off:

- The state is still *accepted* today, so the damage was silent. When
  [`remove-blocked-from-the-status-enum-and-validator`](../remove-blocked-from-the-status-enum-and-validator/)
  lands, `goc.md` would have been telling readers to run a command that errors,
  and the final DoD box of the parent epic
  [`remove-blocked-from-status-enum-and-migrate-existing-cards`](../remove-blocked-from-status-enum-and-migrate-existing-cards/)
  — "docs match the code" — could not honestly have been ticked.
- It was another instance of
  [`doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/):
  `tests/test_guidance_accuracy.py` already pinned six `goc.md` plugin claims
  (`GocMdPluginReferenceAccuracyTest`), and the status-enum claim simply never
  got a guard — so the purge card could close green with this surface untouched.

## What landed

Followed the wording precedent the purge card set in the skill bodies — **name
`blocked` and mark it deprecated**, rather than silently dropping it, because
legacy cards may still carry the value and the reader needs to know what to do
instead.

1. `goc.md` "Common verbs" — the `goc status` row now lists `open`, `active`,
   `disproved`, `superseded` and adds "The enum still accepts the deprecated
   `blocked`; use `goc wait` instead."
2. `goc.md` "Common verbs" — new `goc wait <title> --reason <r>` row naming the
   overlay's effect (stays `open` and visible, withheld only from `--ready`,
   `--clear` removes it), plus a `goc wait` line in the example block and a
   closing paragraph carrying the three-axis framing and the migration
   instruction (drop to `open` for prerequisite waits, `goc wait` for exogenous
   ones).
3. `tests/test_guidance_accuracy.py` — `DeprecatedStatusGuidanceTest`, three
   tests. `_deprecated_status_values()` derives the deprecated set by binding a
   deprecation marker to a backticked status value **in the skill bodies**, then
   intersecting with `goc.engine.MUTABLE_STATUS_VALUES` (what `goc status`
   actually accepts). Deriving rather than pinning the word `blocked` means a
   future deprecation is covered as soon as the skills announce it, and the
   guards retire themselves when the enum removal empties the set. The third
   test is the anti-vacuity check: an empty derived set is only legitimate once
   `MUTABLE_STATUS_VALUES` has also dropped `blocked`.
