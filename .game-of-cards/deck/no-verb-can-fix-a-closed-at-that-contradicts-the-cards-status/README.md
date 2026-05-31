---
title: no-verb-can-fix-a-closed-at-that-contradicts-the-cards-status
summary: "`goc validate` requires `closed_at` to be set iff `status` is terminal (`validate_card`, engine.py ~1288/~1298), but no CLI verb can repair a card already in the contradictory state. A terminal card with `closed_at: null` can't be fixed — the close verbs (`done`, `status … <terminal>`) refuse already-terminal cards. A non-terminal card carrying a stray `closed_at` can't be fixed either — `status <card> open/active` early-returns as a no-op when status is unchanged and never clears the date. Both directions are *mechanically* repairable (stamp / clear), so this is the one closed_at-shaped gap surfaced by the `validate-flags-card-states-that-no-verb-can-repair` audit that genuinely warrants a verb. Reachable via hand-edits, `goc migrate` imports, and bot commits that bypass the pre-commit validate gate."
status: open
stage: null
contribution: medium
created: "2026-05-31T09:34:33Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` — pick the repair surface (see options): a dedicated `goc repair-closed-at`-style affordance, a general `goc repair`, or a narrowly-scoped flag on an existing verb.
  - [ ] TDD: `deck/<title>/reproduce.py` exits zero — it asserts the chosen verb takes (a) a terminal card with `closed_at: null` and (b) a non-terminal card with a stray `closed_at` from validator-red to green, without changing `status` or any other field.
  - [ ] TDD: a `tests/` regression test exercises both directions (terminal→stamp, non-terminal→clear) and confirms the card stays otherwise byte-identical.
  - [ ] MECHANICAL: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; plugin mirrors regenerated if engine changed (`python scripts/sync_plugin_assets.py`).
---

# No verb can fix a `closed_at` that contradicts the card's status

## Location

`goc/engine.py` `validate_card` — the `closed_at` conditional:

- terminal `status` ⇒ `closed_at` must be set (~engine.py:1288).
- non-terminal `status` ⇒ `closed_at` must be null (~engine.py:1298).

## What's broken

The invariant is enforced but unrepairable once violated:

- **Terminal card with `closed_at: null`.** `goc done` refuses an
  already-`done` card; `goc status <card> <terminal>` refuses to move a
  terminal card (terminal cards can't be moved through `status`). Nothing
  re-stamps `closed_at`.
- **Non-terminal card with a stray `closed_at`.** `goc status <card> open`
  (or `active`) early-returns as a no-op when the requested status equals
  the current status, so it never clears the date. Nothing else writes
  `closed_at: null`.

Both states are reachable today — hand-edits, `goc migrate` imports, and
autonomous bot commits that bypass the pre-commit `goc validate` gate
([`pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate`](../pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate/)).
The only repair is hand-editing frontmatter through `git`.

## Why this one (and not the other gaps)

Spawned by the audit on
[`validate-flags-card-states-that-no-verb-can-repair`](../validate-flags-card-states-that-no-verb-can-repair/).
Most validator gaps need human judgment to repair (which successor? which
tag? what summary?), so a verb can't auto-fix them. `closed_at` is
different: it is **mechanically** derivable from `status` —
terminal ⇒ a timestamp is needed, non-terminal ⇒ it must be null — so a
verb *can* fix it deterministically. That makes it the one closed_at-shaped
gap from the audit that genuinely warrants a repair affordance.

One wrinkle for the decision: re-stamping a terminal card that never had a
`closed_at` cannot recover the *true* close date. The verb has to either
use the current time (honest "repaired at" stamp, lossy on the original),
read it from git history (`git log` of the last status flip — accurate but
heavier), or refuse and ask the operator. The clearing direction
(non-terminal → null) is unambiguous.

## Decision required

Pick the repair surface and the terminal-stamp source:

1. **Dedicated affordance** — a small `goc repair-closed-at [--apply]`
   mirroring `repair-edges`: previews the drift, clears strays, and stamps
   missing terminal dates (source per the sub-choice below). Cohesive with
   the existing repair-verb pattern.
2. **General `goc repair`** — fold this into the broader repair verb
   contemplated by the parent audit card. Defer until that verb exists;
   risks blocking on a larger design.
3. **Flag on `status`** — let `goc status <card> <same-status> --fix-closed-at`
   bypass the no-op early return to reconcile the date. Smallest surface,
   but overloads `status`.

Terminal-stamp source sub-choice (applies to options 1/2): current time vs.
`git log` of the last status flip vs. refuse-and-prompt.
