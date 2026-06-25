---
title: waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift
summary: "Meta-fix: `waiting_impedes(card)` deliberately ignores the card's own status, so every caller that wants 'is this card *actively* impeded' must re-apply a liveness gate (`status not in TERMINAL_STATUSES`, or the stricter `status == open`). That gate is re-inlined at ~5 sites with three different phrasings, and it already drifted into a shipping bug: the `--waiting` filter shipped with no gate and leaked closed cards into the impeded view (fixed in waiting-filter-shows-terminal-cards-with-stale-overlay). This is the exact sibling of the already-centralized dependency-advisory liveness gate."
status: open
stage: null
contribution: medium
created: "2026-06-25T14:07:05Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [meta-fix, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: decision recorded — pick the helper shape (single `active_impediment(card, *, queue_only=False)` vs a thin `live_impeded`/`queueable_impeded` pair); see "## Decision required"
  - [ ] MECHANICAL: the chosen helper centralizes `status not in TERMINAL_STATUSES and waiting_impedes(card)` (and the open-only variant), and the live-variant callers (board `card_cell`, `--waiting` filter, `card_is_workable_for_scheduler`) and open-only callers (`card_is_ready`, gated-leverage) route through it instead of inlining the gate
  - [ ] TDD: a unit test covers the helper across {open, active, terminal} x {impeded, clear}; existing regressions (`test_waiting_filter_status_scope`, board/scheduler tests) still pass
  - [ ] TDD: no behavior change — pure consolidation; the predicate-coupling guard (`test_scheduler_workable_predicate_coupling.py`) stays green
  - [ ] PROCESS: instance cards cross-referenced; `uv run goc validate` clean; full suite green
---

# `waiting_impedes` callers re-inline the terminal-status liveness gate and drift

## The duplicated rule

`waiting_impedes(card)` (`goc/engine.py:2253`) answers "does this card's
overlay impede *right now*" purely from `waiting_on` / `waiting_until`.
It deliberately does **not** consult the card's own progress status —
so a terminal card with a stale overlay (closing never clears the
overlay, a documented invariant) returns `True`.

Every caller that wants "is this card *actively* impeded" must therefore
re-apply a liveness gate. They do, independently, in three different
phrasings:

| Caller | file:line | Liveness phrasing |
|---|---|---|
| board `card_cell` | `engine.py:2982-2986` | `live and (... or waiting_impedes(t))`, `live = status not in TERMINAL_STATUSES` |
| `--waiting` filter | `engine.py:3499` | `status not in TERMINAL_STATUSES and waiting_impedes(t)` (just fixed) |
| `card_is_workable_for_scheduler` | `engine.py:2244-2248` | `if status in TERMINAL_STATUSES: return False` then `waiting_impedes` |
| `card_is_ready` | `engine.py:2219-2223` | `if status != "open": return False` then `waiting_impedes` (stricter: open-only) |
| gated-leverage line | `engine.py:3059-3063` | `status == "open" and ... and not waiting_impedes(t)` (open-only) |

Two of these are the stricter open-only variant (`card_is_ready`,
gated-leverage); three are the live variant (non-terminal, includes
`active`). No single function owns the rule.

## Why it matters — the drift already shipped

The `--waiting` filter shipped with **no** liveness gate at all, so it
leaked closed-but-deferred cards into the impeded view. That was a real
bug, fixed in
[waiting-filter-shows-terminal-cards-with-stale-overlay](../waiting-filter-shows-terminal-cards-with-stale-overlay/)
by hand-inlining the gate — adding a *sixth* copy of the rule rather
than consolidating it. The next read surface that consults
`waiting_impedes` will face the same choice and can drift the same way.

This is structurally identical to
[renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift](../renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift/)
(done), which centralized the *dependency-advisory* liveness gate into
one `dependency_advisory(card, by_title, *, queue_only=...)` helper after
it drifted into a shipping bug. The impediment-overlay gate is the same
shape around a different predicate and wants the same treatment. Compare
also the mutation-side family
[terminal-status-guard-missing-across-mutation-verbs](../terminal-status-guard-missing-across-mutation-verbs/)
(write-side guard) — this card is the read-side analog.

## Decision required

The two liveness variants are not interchangeable, so the consolidation
shape is a genuine choice:

- **Option A — one helper with a flag.** `active_impediment(card, *,
  queue_only=False)`: `queue_only=True` requires `status == "open"`,
  else `status not in TERMINAL_STATUSES`; both then AND with
  `waiting_impedes`. Mirrors the `dependency_advisory(queue_only=...)`
  precedent exactly. One name, parameterized.
- **Option B — two thin helpers.** e.g. `live_impeded(card)` and
  `queueable_impeded(card)`, each a one-liner. More call-site-legible,
  no boolean-flag-at-callsite smell, but two names to keep coherent.

Recommendation: Option A, to match the established
`dependency_advisory` precedent so the two liveness gates read the same
way. Confirm before implementing.

## Fix

Pure consolidation, no behavior change: introduce the chosen helper,
route all five callers through it, keep the predicate-coupling guard
green. The just-shipped `--waiting` inline gate becomes a call to the
helper.
