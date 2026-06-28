---
title: refine-deck-meta-fix-orphan-check-counts-only-advances-false-positives-wired-families
summary: "`Skill(refine-deck)`'s orphaned-dependency sub-check 2 (meta-fix) tests `if not (c.get('advances') or [])`, counting only the `advances` field. But the established convention — confirmed by the closed `meta-fix-umbrella-cards-leave-sibling-family-advanced-by-edges-unwired` card — wires umbrella families via `advanced_by` (umbrella `advanced_by` siblings, sibling `advances` umbrella). So every correctly-wired umbrella is a false positive: a 2026-06-22 hygiene pass surfaced 31 meta-fix cards, of which 12 were genuine roots already wired via `advanced_by`. Sub-checks 1 (epics) and 3 (legacy markers) already count `len(advances) + len(advanced_by)`; sub-check 2 should match."
status: done
stage: null
contribution: low
created: "2026-06-22T01:46:28Z"
closed_at: "2026-06-22T01:53:57Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra, api-contract]
definition_of_done: |
  - [x] MECHANICAL: sub-check 2 in `goc/templates/skills/refine-deck/SKILL.md` counts `len(c.get('advances') or []) + len(c.get('advanced_by') or [])` (matching sub-checks 1 and 3) so a meta-fix umbrella wired via `advanced_by` is no longer surfaced as "empty advances".
  - [x] MECHANICAL: the prose at lines 186-191 ("Meta-fix cards with empty advances") is updated to say "zero edges (neither `advances` nor `advanced_by`)" and the printed message no longer says "empty advances" specifically.
  - [x] PROCESS: the change is made in the template only; `python scripts/sync_plugin_assets.py` (or the pre-commit `sync-plugin-assets` hook) regenerates the five skill mirrors (`.claude/`, `.codex/`, `claude-plugin/`, `codex-plugin/`, and the OpenClaw port via `scripts/port_skills_to_openclaw.py`).
  - [x] EMPIRICAL: re-running the sub-check 2 survey on this repo's deck surfaces only genuinely-naked meta-fix cards (zero on both edge fields), not the umbrellas already wired via `advanced_by`.
  - [x] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
worker: {who: "claude[bot]", where: main}
---

# `refine-deck` meta-fix orphan sub-check counts only `advances`, false-positives correctly-wired families

## Location

`goc/templates/skills/refine-deck/SKILL.md`, the "Orphaned dependencies"
survey in Step 2:

- Sub-check 1 (epics), line ~181:
  `n = len(ep.get('advances') or []) + len(ep.get('advanced_by') or [])` — counts **both** fields.
- Sub-check 2 (meta-fix), line ~197:
  `if not (c.get('advances') or []):` — counts **only** `advances`.
- Sub-check 3 (legacy markers), line ~211:
  `n = len(c.get('advances') or []) + len(c.get('advanced_by') or [])` — counts **both** fields.

(The same asymmetry is mirrored byte-for-byte into the five generated
skill copies under `.claude/`, `.codex/`, `claude-plugin/`,
`codex-plugin/`, and `openclaw-plugin/` — fix the template, the sync
regenerates them.)

## What's broken

Sub-check 2 is meant to catch a meta-fix umbrella that declares a
sibling-family roster in prose but never wired the edges. It tests the
`advances` field alone. But the established wiring convention for these
umbrellas — set out and exercised by the closed card
[meta-fix-umbrella-cards-leave-sibling-family-advanced-by-edges-unwired](../meta-fix-umbrella-cards-leave-sibling-family-advanced-by-edges-unwired/)
— is:

> each sibling instance carries `advances: [umbrella]`, and the umbrella
> carries `advanced_by: [siblings…]`. The symmetric pair is set
> atomically by `goc advance <umbrella> --by <sibling>`.

So a *correctly-wired* umbrella has a populated `advanced_by` and an
empty `advances` — which is exactly the shape sub-check 2 flags as
"family unwired". Every umbrella that did the right thing is reported
as rot.

That closed card even anticipated the correct survey shape in its own
DoD (item: "re-run the meta-fix zero-edge survey counting **BOTH**
`advances` and `advanced_by`") — but the shipped sub-check was never
updated to match.

## Evidence (2026-06-22 hygiene pass)

The meta-fix zero-`advances` survey surfaced **31** open cards. Splitting
them by whether `advanced_by` is populated:

- **12** are genuine umbrellas already correctly wired via `advanced_by`
  (false positives), e.g.:
  - `bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes` → 4 siblings
  - `frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting` → 8 siblings
  - `session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting` → 8 siblings
  - `ship-game-of-cards-as-cross-agent-cli` → 18 children (epic-shaped)
- **19** are "fully naked" (neither `advances` nor `advanced_by`), and
  nearly all of those carry the `meta-fix` tag only because the tag
  predicate fires on any body mention of the literal string
  `meta-fix` (per `Skill(card-schema)`: "literal `meta-fix` /
  `family meta-fix` in title, title, or body"). Spot-checks show they
  are individual bugs noting "this is a meta-fix candidate", not
  umbrellas with a roster — and all 19 are `human_gate: decision`.

Counting both edge fields collapses the 12 false positives, leaving the
survey to surface only the genuinely-edge-empty cards a human still
needs to triage.

## Why it matters

`refine-deck` is the recurring deck-hygiene tax. A sub-check that
reports 12 correctly-wired cards as rot on every pass trains the
operator to ignore the whole category — the same alarm-fatigue failure
the orphaned-dependency check exists to prevent. The fix is a
one-expression change that brings sub-check 2 in line with its two
siblings and with the documented wiring convention.

## Scope note

This is strictly the survey-counting bug. The looseness of the
`meta-fix` tag predicate (firing on any prose mention, which is what
pulls the 19 naked instances into the survey at all) is a separate
concern about the tag's application criteria and is **not** in scope
here — flag it as a follow-up if the operator wants the survey to also
exclude non-umbrella instances.

## Notes

Filed at `human_gate: none` by an autonomous `refine-deck` pass with no
human in the loop. The fix is mechanical (a counting-expression change
plus a prose tweak), but it touches a shipped skill template, so it is
filed rather than hand-applied mid-hygiene-pass to keep the pass's own
edits reviewable in isolation. The next reader may raise the gate if
they disagree.
