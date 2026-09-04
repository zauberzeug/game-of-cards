---
title: cli-reference-steers-authors-onto-deprecated-blocked-status-not-the-wait-overlay
summary: "The published CLI reference goc.md still lists blocked as a normal goc status target state and never mentions goc wait or the impediment overlay, so a reader following it flips a card to status: blocked — which validates fine but drops the card out of every status: open query with no reason recorded. purge-blocked-status-from-skills-and-docs soft-deprecated blocked across the skill bodies and AGENTS files on 2026-05-26 but its scope never named goc.md, leaving it the only surface outside the deck that still recommends the deprecated status."
status: open
stage: null
contribution: medium
created: "2026-09-04T04:34:30Z"
closed_at: null
human_gate: none
advances:
  - remove-blocked-from-status-enum-and-migrate-existing-cards
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
draft: true
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the `goc status` row no longer
        offers `blocked` unmarked, `goc.md` names the overlay, and the
        behavioral contrast is recorded.
  - [ ] TDD: `tests/test_guidance_accuracy.py` gains a guard that DERIVES
        the deprecated status values from the skill bodies (not a hardcoded
        word list) and fails when a guidance surface lists one as a
        `goc status` target without a deprecation marker. Verified
        non-vacuous against the pre-fix `goc.md`.
  - [ ] MECHANICAL: `goc.md`'s "Common verbs" table marks `blocked` as
        deprecated in the `goc status` row and gains a `goc wait` row for
        the impediment overlay, matching the wording precedent set by
        `Skill(advance-card)` and `Skill(card-schema)`.
  - [ ] PROCESS: closed sibling `purge-blocked-status-from-skills-and-docs`
        amended with a forward pointer to this card, and both `advances`
        endpoints carry the inverse `advanced_by` edge.
---

# `goc.md` steers authors onto the deprecated `blocked` status, not the wait overlay

## Location

- `goc.md:283` — the `goc status` row of the **Common verbs** table.
- `goc.md` as a whole — zero mentions of `goc wait`, `waiting_on`, or the
  impediment overlay.
- Published as the CLI reference at `https://game-of-cards.com/goc/` and
  `/goc.md` (`.github/workflows/pages.yml:11-12`), and linked from
  `site/llms.txt:129` as "CLI reference and install recipe".

## What's broken

`goc.md` is the command-level reference. Its verb table says:

```
| `goc status <title> <state>` | Move a card through `open`, `active`, `blocked`, `disproved`, or `superseded`. |
```

`blocked` sits there as one of five equal, unmarked target states. The
authoritative surfaces say the opposite. `goc/templates/skills/card-schema/SKILL.md:64`:

```
`blocked` is deprecated — split into derived dependency-readiness and
```

and `goc/templates/skills/advance-card/SKILL.md:54`:

```
stuck model"). The legacy `status: blocked` is deprecated; set the
```

`goc/templates/skills/advance-card/reference.md:23-36` carries a whole
**"Deprecated blocked status"** section telling the reader the value "will be
removed in a follow-up release". `goc.md` carries no such marker, and it never
names the mechanism that replaced it — the `goc wait` impediment overlay is
absent from the document entirely, so a reader has no way to find the correct
alternative from the page they are on.

This is a gap in a *closed* card's scope, not new drift. Sibling
[`purge-blocked-status-from-skills-and-docs`](../purge-blocked-status-from-skills-and-docs/)
closed 2026-05-26 with the stated job "Stop recommending `status: blocked`";
its DoD enumerated `advance-card`, `card-schema`, `deck`,
`templates/AGENTS_GOC.md` and this repo's `AGENTS.md` — and never named
`goc.md`. A repo-wide sweep confirms `goc.md:283` is now the **only** surface
outside `.game-of-cards/deck/` and the generated mirrors that still presents
`blocked` as a normal state: `site/` has zero mentions, and every remaining hit
is either a skill body that marks it deprecated or engine/schema code the
sibling [`remove-blocked-from-the-status-enum-and-validator`](../remove-blocked-from-the-status-enum-and-validator/)
owns.

## Empirical evidence

`uv run python .game-of-cards/deck/cli-reference-steers-authors-onto-deprecated-blocked-status-not-the-wait-overlay/reproduce.py`
(exit 1):

```
========================================================================
STATIC: goc.md vs the skill bodies
========================================================================
goc.md `goc status` row:
  | `goc status <title> <state>` | Move a card through `open`, `active`, `blocked`, `disproved`, or `superseded`. |

goc.md mentions of the replacement mechanism: missing=['goc wait', 'waiting_on', 'impediment overlay']

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

B) after the undocumented `goc wait probe-card --reason external`:
  goc          -> TITLE       STATUS  CONTR.  VALUE  GATE      TAGS  DOD
  goc          -> ----------  ------  ------  -----  --------  ----  ---
  goc          -> probe-card  open    medium    3.0  decision        0/1
  goc --ready  -> No cards match (ready: status open, gate none, no active impediment).

DEFECT STANDS (3):
  - the `goc status` row offers `blocked` as a normal target state with no deprecation marker
  - goc.md never mentions `goc wait` / `waiting_on` / the impediment overlay, so it offers no correct alternative
  - the documented `blocked` flip drops the card out of the default `status: open` queue with no reason recorded, while the undocumented `goc wait` keeps it visible
```

## Why it matters

The doc is not merely stale — following it produces the exact card state the
three-axis model was built to eliminate. Block **A** above is what a reader
gets by running the documented command: the card validates `OK`, so nothing
warns them, and it disappears from `goc`, from every `status: open` query, and
from the autonomous pull queue, with **no impediment reason recorded**. Block
**B** is what the replacement does: the card stays `open` and visible with its
reason attached, and is withheld only from `--ready`. The doc's advice loses the
card; the undocumented alternative keeps it.

Two follow-on costs:

- The state is still *accepted* today, so the damage is silent. When
  [`remove-blocked-from-the-status-enum-and-validator`](../remove-blocked-from-the-status-enum-and-validator/)
  lands, `goc.md` will be telling readers to run a command that errors, and
  the final DoD box of the parent epic
  [`remove-blocked-from-status-enum-and-migrate-existing-cards`](../remove-blocked-from-status-enum-and-migrate-existing-cards/)
  — "docs match the code" — cannot honestly be ticked while this row stands.
- It is another instance of
  [`doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/):
  `tests/test_guidance_accuracy.py` already pins six `goc.md` plugin claims
  (`GocMdPluginReferenceAccuracyTest`, `tests/test_guidance_accuracy.py:509`),
  and the status-enum claim simply never got a guard — so the purge card could
  close green with this surface untouched.

## Fix

Follow the wording precedent the purge card set in the skill bodies — **name
`blocked` and mark it deprecated**, rather than silently dropping it, because
legacy cards may still carry the value and the reader needs to know what to do
instead.

1. `goc.md:283` — mark the state deprecated in the `goc status` row, e.g.
   `open`, `active`, `disproved`, or `superseded` (plus the deprecated
   `blocked` — see `Skill(advance-card)`).
2. `goc.md` "Common verbs" table — add a `goc wait <title> --reason <r>` row
   for the impediment overlay, so the page names the replacement it currently
   omits.
3. `tests/test_guidance_accuracy.py` — add a guard beside
   `GocMdPluginReferenceAccuracyTest` that **derives** the deprecated status
   values from the skill bodies and fails when a guidance surface lists one as
   a `goc status` target without a deprecation marker. Deriving (rather than
   hardcoding `blocked`) is what makes the guard survive the enum removal.
