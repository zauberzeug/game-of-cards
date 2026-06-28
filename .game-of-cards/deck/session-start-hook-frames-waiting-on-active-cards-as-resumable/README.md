---
title: session-start-hook-frames-waiting-on-active-cards-as-resumable
summary: "SessionStart hook (`deck_session_start.py`) partitions active cards by `human_gate` only — the partner fix to closed sibling [session-start-hook-shows-gated-active-cards-as-resumable](../session-start-hook-shows-gated-active-cards-as-resumable/). A `status: active` card with `human_gate: none` but `waiting_on: external|resource|deferred` (or a future `waiting_until`) is still impeded and not agent-resumable, yet the hook tells the agent to `resume or close` it. The three-axis stuck model in AGENTS.md says these axes compose; the hook collapses them."
status: done
stage: null
contribution: medium
created: "2026-05-29T09:22:32Z"
closed_at: "2026-05-29T09:30:10Z"
human_gate: none
advances:
  - session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] MECHANICAL: `deck_session_start.py` also inspects `waiting_on` (and optionally `waiting_until`) when bucketing active cards. A `status: active, human_gate: none` card with an active impediment overlay is reported under the parked/impeded bucket (or its own bucket), not the "resume or close" bucket. A future `waiting_until` is treated as an active impediment.
  - [x] TDD: a regression test exercises the hook on a fixture deck containing (a) one `status: active, human_gate: none` card with no `waiting_on` (truly resumable), (b) one with `waiting_on: external`, (c) one with `waiting_on: deferred` + future `waiting_until`, (d) one with `human_gate: decision`. The test asserts only (a) appears under the resumable framing.
  - [x] MECHANICAL: all four file copies updated in lockstep (source-of-truth + auto-synced mirrors): `goc/templates/hooks/deck_session_start.py`, `.claude/hooks/deck_session_start.py`, `claude-plugin/hooks/deck_session_start.py`, `codex-plugin/hooks/deck_session_start.py`. The byte-for-byte mirror tripwire in CI catches drift if any are missed.
  - [x] MECHANICAL: the OpenClaw TypeScript port of this hook in `openclaw-plugin/index.ts` is updated to match — same `waiting_on` filtering semantics. (The OpenClaw hook is hand-ported, not auto-synced; verify by re-reading `index.ts` after the change.)
  - [x] PROCESS: `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# SessionStart hook frames `waiting_on` active cards as resumable

## Location

`goc/templates/hooks/deck_session_start.py:82-87` (and three mirrored copies — see DoD).

## What's broken

The recent commit `4384733` partitioned active cards into a resumable
bucket and a parked bucket — but the partition predicate inspects only
`human_gate`:

```python
# goc/templates/hooks/deck_session_start.py:74-87
resumable = []
parked = []
for card_dir in sorted(deck_dir.iterdir()):
    if not card_dir.is_dir():
        continue
    readme = card_dir / "README.md"
    if not readme.is_file():
        continue
    if _card_status(readme) != "active":
        continue
    if _card_human_gate(readme) == "none":
        resumable.append(card_dir.name)
    else:
        parked.append(card_dir.name)
```

This collapses the second axis of the three-axis stuck model
(`waiting_on` impediment overlay) into the resumable bucket. AGENTS.md
spells out the composition:

> **Three-axis "stuck" model.** A card that isn't moving fails for one
> of three independent reasons … (3) **stored impediment overlay** —
> `waiting_on` ∈ {`external`, `resource`, `deferred`} … The overlay
> composes alongside `human_gate` (decision/session waits) — a card
> may be `status: active` AND carry `waiting_on`.

The schema's `waiting_until` predicate adds a fourth case: a future
`waiting_until` hides the card from queues, so the hook should also
treat it as impeded rather than resumable.

## Reachability path

The dogfood deck currently has the exact input the hook misframes. The
parent epic [blocked-status-conflates-dependency-external-wait-and-deferral](../blocked-status-conflates-dependency-external-wait-and-deferral/)
and its child [remove-blocked-from-status-enum-and-migrate-existing-cards](../remove-blocked-from-status-enum-and-migrate-existing-cards/)
both carry `status: active` (well, `open` with `waiting_on: deferred`
at the moment, but the same shape ships once they're claimed). The
`openclaw-subagent-plugin-tools-alsoallow-ignored` card carries
`status: open, human_gate: none, waiting_on: external` — once a worker
claims it, it becomes `status: active, human_gate: none, waiting_on:
external`, and every subsequent SessionStart will misreport it.

Both surfaces this hook drives run on every fresh session:

- Claude Code's `SessionStart` event runs the hook (registered in
  `claude-plugin/hooks/hooks.json` and in the consumer's
  `.claude/settings.json` via `GOC_CLAUDE_HOOKS`).
- The OpenClaw plugin's `index.ts` reimplements the same logic and
  registers it via `api.on('session_start', ...)`.

## Empirical evidence

```
$ uv run python .game-of-cards/deck/session-start-hook-frames-waiting-on-active-cards-as-resumable/reproduce.py
Hook stdout:
[GoC] Active card(s): a-resumable-no-overlay, b-impeded-external, c-impeded-deferred-future — resume or close before starting new work.
[GoC] Parked active card(s) (awaiting human): d-control-gated — agent cannot resume.


FAIL — defect reproduced:
  - DEFECT: b-impeded-external (waiting_on: external) is framed as RESUMABLE.
  - DEFECT: c-impeded-deferred-future (waiting_until=2099-01-01) is framed as RESUMABLE.
```

Both impeded fixtures are bucketed under the `resume or close` line. Only
the `human_gate: decision` control (d) lands correctly in the parked line —
the partition cuts on `human_gate` only, ignoring the `waiting_on` axis.

## Why it matters

The closed sibling [session-start-hook-shows-gated-active-cards-as-resumable](../session-start-hook-shows-gated-active-cards-as-resumable/)
shipped the partition; this card finishes the partition on the second
axis. Without the fix:

1. An agent landing in a fresh session reads `resume or close before
   starting new work.` for a card whose impediment overlay says the
   work is blocked on an external SLA or a constrained resource.
2. The agent acts on the misframing — either flailing on a card it
   cannot actually resume, or closing a card whose deferral was the
   point.
3. A future `waiting_until` makes the situation worse: the puller
   already hides the card from the queue, but the session-start hook
   waves it under the agent's nose anyway.

## Fix

Extend `_card_human_gate` (or add a sibling `_card_waiting_on` /
`_card_waiting_until` reader) and change the bucketing predicate at
line 84 to:

```python
if _card_human_gate(readme) == "none" and not _is_impeded(readme):
    resumable.append(card_dir.name)
else:
    parked.append(card_dir.name)
```

where `_is_impeded` returns True iff the card has a `waiting_on` value
that is one of `external|resource|deferred`, OR a `waiting_until`
whose date is in the future. Reuse the existing `_FRONTMATTER_RE`
parse pattern — the file deliberately does line-based YAML to avoid
importing the engine.

Optionally split the parked bucket into "awaiting human" and
"impeded" sub-buckets so the session-start summary keeps the same
diagnostic granularity the engine emits elsewhere (e.g. the board's
🛑 marker for impeded cards).
