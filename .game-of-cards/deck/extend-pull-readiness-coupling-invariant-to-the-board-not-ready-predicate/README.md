---
title: extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate
summary: "Pull-readiness logic lives in three hand-rolled copies — `card_is_ready`, `card_is_workable_for_scheduler`, and the board's `not_ready` cell predicate — but only the first two are kept coupled by `tests/test_scheduler_workable_predicate_coupling.py`. The board's copy silently drifted (it omitted the `human_gate` axis; see the closed `board-omits-pull-blocking-marker-for-human-gate-parked-cards`). Extend the coupling guard / extract a shared predicate so the board copy can no longer drift."
status: open
stage: null
contribution: medium
created: "2026-06-06T05:11:35Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - board-omits-pull-blocking-marker-for-human-gate-parked-cards
  - pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty
  - standup-next-up-section-lists-cards-pull-card-would-never-pick
  - reproduce-py-runway-metric-counts-gates-instead-of-the-engine-ready-predicate
tags: [meta-fix, api-contract, infra]
definition_of_done: |
  - [ ] TDD: a regression test asserts the board's not-pullable marker agrees with `card_is_ready` across the `status × human_gate × waiting_on` cross-product (modulo the board's deliberate advisory `dependency_blocked` superset), so a future axis added to `card_is_ready` that is not mirrored into the board fails the build — the same guarantee `tests/test_scheduler_workable_predicate_coupling.py` gives the scheduler predicate.
  - [ ] MECHANICAL: the chosen shape from `## Decision required` is implemented (shared rejection-axis helper reused by all three sites, OR an extended coupling test that introspects the board predicate).
  - [ ] PROCESS: `## Decision required` resolved — pick the coupling mechanism.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; `python scripts/sync_plugin_assets.py --check` green.
---

# Pull-readiness logic has three copies; the coupling invariant guards only two

## What's broken

"Is this card pullable / not-ready?" is computed in three independent
places in `goc/engine.py`:

1. `card_is_ready` (engine.py:2457) — the queue axis (`next-card` / `pull-card`).
2. `card_is_workable_for_scheduler` (engine.py:2669) — the scheduler axis.
3. The board's `not_ready` predicate inside `card_cell` in `render_board`
   (engine.py:3559) — the at-a-glance ⏳ marker.

Copies 1 and 2 carry an explicit coupling invariant in their docstrings
("a future axis added here must be added there in the same edit"),
enforced by `tests/test_scheduler_workable_predicate_coupling.py`, which
introspects both across the `status × human_gate × waiting_on`
cross-product and fails on drift.

Copy 3 — the board — is **not** covered by any such guard, and it
silently drifted: it honored `dependency_blocked` and `waiting_impedes`
but omitted the `human_gate` axis, so human-gate-parked open cards
rendered as freely pullable. That was a real shipped bug, fixed in
[board-omits-pull-blocking-marker-for-human-gate-parked-cards](../board-omits-pull-blocking-marker-for-human-gate-parked-cards/)
by hand-adding the missing axis — but nothing prevents the *next* axis
(or the next renderer that hand-rolls the same check) from drifting
again.

A **fourth copy** has since been confirmed drifted, outside the engine
entirely: `.github/workflows/pull-card.yml` counts the autonomous queue
with `--status open --human-gate none`, omitting the waiting-overlay
axis, so it launches agent sessions `goc --ready` refuses to feed — see
[pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty](../pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty/).
That copy is shell, so no Python introspection guard can cover it; its
fix is substitution (`goc --ready --json`), reinforcing the "expose the
engine predicate, don't re-roll it" direction here.

A **fifth copy** was confirmed drifted on 2026-08-04, and it is the first
one that is not executable code at all: `render_empty_query_line`
(engine.py) restates the readiness predicate as an English sentence —

```python
parts.append("ready: status open, gate none, no active impediment")
```

— naming three of `card_is_ready`'s four conjuncts and omitting the
`card_is_draft` exclusion. Demonstrated on a one-card scratch deck whose
only card is `status: open`, `human_gate: none`, no impediment,
`draft: true`:

```
$ goc --ready
No cards match (ready: status open, gate none, no active impediment).

$ goc --status all
TITLE            STATUS  CONTR.  VALUE  GATE  TAGS  DOD
draft-gate-none  open    medium    3.0  none        0/1
```

Every condition the sentence names holds for that card, and the card is
still excluded — so a reader auditing the message against the deck finds
it self-contradictory. Surfaced while fixing
[empty-result-line-reports-a-drained-ready-queue-that-still-has-cards](../empty-result-line-reports-a-drained-ready-queue-that-still-has-cards/),
a different defect in the same sentence (which filters get *named*,
rather than how the predicate is *spelled*); recorded here rather than
filed separately because it is this card's pattern, not a new one.

**This copy constrains the decision below.** Option (b) extends an
introspection test over *code* predicates, and no such test can reach a
prose string — the sentence would keep drifting undetected. Option (a)
can cover it, but only if the extracted helper also yields the
human-readable axis labels (e.g. `_pull_rejection_axes` returning axis
names the message renders), rather than just a boolean or an opaque set.
That is a requirement on (a)'s shape, not merely a point in its favour.

## The pattern

This is the same drift shape called out for the OpenClaw host in
[openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/),
one surface over: a predicate reimplemented rather than reused keeps
drifting from its source of truth. Here both copies live in the same
module, so the fix is cheaper — a shared helper or an extended
introspection test rather than a cross-language port.

## Why it matters

The board is the primary human triage surface and the queue predicates
are the autonomous-puller's safety gate. A drift between them means the
board lies about what an agent will pull — exactly the class of defect
that just shipped. A coupling guard turns "remember to update all three"
(which already failed once) into a build failure.

## Why this is a non-trivial extraction (not a pure mechanical dedup)

The board's `not_ready` is **not identical** to `card_is_ready`'s
rejection set. The board deliberately marks an additional *advisory*
state — `dependency_blocked` (an open `advanced_by` prereq) — that
`card_is_ready` intentionally treats as pullable (an `advances` edge is
"should be done first", not "must wait"). So the board predicate is a
*superset*: every `card_is_ready` rejection axis (status / human_gate /
waiting) PLUS the advisory dependency hint. A naive "board calls
`card_is_ready`" collapses that distinction. The coupling that must hold
is: **the board marks not-ready whenever `card_is_ready` is False (for
an open card), and may additionally mark the advisory dependency axis.**

(Note: `board-marks-pullable-and-impeded-cards-with-the-same-hourglass-glyph`
is the orthogonal, still-open question of whether that advisory axis
should even share the ⏳ glyph. This card is about *coupling*, not glyph
choice; the two can be resolved independently.)

## Decision required

Which coupling mechanism?

- **(a) Extract a shared rejection-axis helper.** A single function
  (e.g. `_pull_rejection_axes(card, by_title) -> set[str]`) returns the
  axes that hide a card from the queue (`status`, `human_gate`,
  `waiting`). `card_is_ready` / `card_is_workable_for_scheduler` reject
  iff the set is non-empty (modulo the documented `active` divergence);
  the board's `not_ready` is `bool(rejection_axes) or
  dependency_blocked(...)`. Drift becomes structurally impossible because
  there is one source. Most robust; largest edit.

- **(b) Extend the coupling test to introspect the board.** Leave the
  three predicates as hand-rolled code but add the board's `not_ready`
  to `test_scheduler_workable_predicate_coupling.py`'s cross-product
  assertion (rendering a one-card board per combination and checking the
  ⏳ marker agrees with `card_is_ready` modulo the dependency superset).
  Smallest code change; the guard is a test, not an abstraction, so the
  copies still exist but can't drift undetected.

(a) removes the duplication; (b) only detects it. Pick before
implementing.
