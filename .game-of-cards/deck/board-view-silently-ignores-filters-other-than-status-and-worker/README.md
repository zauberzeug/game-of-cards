---
title: board-view-silently-ignores-filters-other-than-status-and-worker
summary: "`--board` discards every filter except `--status`/`--done` and `--worker`. `goc --ready --board`, `goc --tag bug --board`, `goc --human-gate decision --board`, `goc --contribution high --board`, `goc --waiting --board`, `goc --advances X --board`, `goc --advanced-by X --board`, and `goc --closed-since 7d --board` all render the entire deck. The same filters drive the table renderer correctly — the bug is one branch in `_cmd_default`."
status: open
stage: null
contribution: medium
created: "2026-05-30T07:10:13Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: regression test asserts that `goc --ready --board` does NOT render cards whose `human_gate != none` (or carry an active `waiting_on` overlay).
  - [ ] TDD: regression test asserts that `goc --tag <T> --board` only renders cards carrying tag `T`. Add sibling assertions for `--human-gate`, `--contribution`, `--waiting`, `--advances`, `--advanced-by`, and `--closed-since` so the whole filter family is covered by the suite.
  - [ ] PROCESS: decision recorded — should `--board` use the filtered set whenever any filter is passed (drop the `status_filter_explicit or args.worker` gate), keep the "full deck for context" intent only for the no-filter default, or split the difference (e.g. always render every column but cap each column to the filtered set)? `Skill(decide-card)` records the choice in this body.
  - [ ] MECHANICAL: `engine.py:2858` updated to reflect the chosen rule. Every filter the table renderer honors must reach `render_board` (or be explicitly documented as out-of-scope in `--board`'s help text).
  - [ ] TDD: `reproduce.py` exits zero (defect no longer fires — all four `BUG: ...` assertions PASS).
---

# `--board` silently ignores filters other than `--status` and `--worker`

## Location

- `goc/engine.py:2857-2858` — the `--board` branch of `_cmd_default`:

  ```python
  if args.board:
      board_cards = filtered if (status_filter_explicit or args.worker) else cards
  ```

- `goc/engine.py:2825` — `status_filter_explicit = bool(args.done_flag or args.status_flag is not None)`.

## What's broken

`_cmd_default` builds the filtered card list by passing every global
filter into `filter_cards(...)` — `status`, `stages`, `contribution`,
`human_gate`, `tags`, `since`, `advances`, `advanced_by`, `worker`, and
`ready` — and then applies a `--waiting` post-filter (line 2853). The
result, `filtered`, is what the **table renderer** and the JSON renderer
consume.

The **board renderer** consults a different variable: `board_cards`. On
line 2858, that variable is computed as:

```python
board_cards = filtered if (status_filter_explicit or args.worker) else cards
```

So `board_cards == filtered` only when the user passed `--status`
(or `--done`) or `--worker`. For every other filter flag — `--ready`,
`--tag`, `--contribution`, `--human-gate`, `--waiting`, `--advances`,
`--advanced-by`, `--closed-since` — `board_cards == cards`, i.e. the
entire deck unfiltered.

There is no warning. No error. No help-text note saying that `--board`
honors a different filter set than the table view.

## Empirical evidence

`uv run python .game-of-cards/deck/board-view-silently-ignores-filters-other-than-status-and-worker/reproduce.py`
(exits non-zero today):

```
PASS  table --ready shows ready-bug-card
PASS  table --ready hides gated-bug-card
PASS  table --ready hides documentation-card
PASS  table --tag=documentation shows documentation-card
PASS  table --tag=documentation hides ready-bug-card
FAIL  BUG: board --ready hides gated-bug-card
FAIL  BUG: board --ready hides documentation-card
FAIL  BUG: board --tag=documentation hides ready-bug-card
FAIL  BUG: board --tag=documentation hides gated-bug-card
```

The script materializes a three-card temp deck (one open + `human_gate:
none` + `tag: bug`; one open + `human_gate: decision` + `tag: bug`; one
open + `human_gate: decision` + `tag: documentation`) and runs `goc`
from inside it. The table view obeys the filters; the board view shows
all three cards regardless of `--ready` or `--tag`.

## Reachability

Anyone who types `goc --ready --board` or `goc --tag <T> --board` —
i.e. anyone wanting a kanban visualization of a filtered slice. The
`pull-card` skill body explicitly recommends `goc --board` for capacity
visibility (`Check goc --status active or goc --board before claiming
new work` — engine.py:2498); a user combining `--board` with another
filter expects the documented "filter then render" contract that the
table view already provides.

The closed predecessor `surface-active-cards-in-board` (commit
`c8a7cb8`) introduced the `status_filter_explicit` carve-out to keep
the default `goc --board` showing the full deck rather than just open
cards. The fix correctly handled the `--status` case but did not
generalize to the rest of the global filter family. A later patch wired
`args.worker` into the same branch (`board_cards = filtered if
(status_filter_explicit or args.worker) else cards`), confirming the
pattern needed to grow — but every other filter is still dropped.

## Why it matters

- The board is a `pull-card`-recommended workflow surface. A worker who
  filters with `--ready --board` to see what they can actually pull
  next is shown a full kanban with gated cards mixed in — exactly what
  `--ready` is meant to suppress.
- The bug is silent. Nothing in the output indicates the filter was
  ignored. Compare to `since-filter-without-done-hides-open-queue`
  (closed) and `invalid-tag-filter-silently-empties-queue` (closed) —
  the project already considers "filter silently does nothing" a
  defect class worth catching.
- The current branch is internally inconsistent: `--status` and
  `--worker` propagate through; siblings declared in the same parser
  block don't. The right behavior is one rule, not a growing
  per-filter allowlist.

## Decision required

Three options for the fix; record the choice via `Skill(decide-card)`.

### Option A — propagate every filter (recommended)

Drop the `status_filter_explicit or args.worker` carve-out and use
`board_cards = filtered` unconditionally. The default `goc --board`
falls back to "show open + active" (the default `status == "open"`
filter), which is closer to what most boards do today.

Trade-off: changes the no-flag default — `goc --board` would render
just the open + active queue instead of the full six-column deck.
That regresses the `surface-active-cards-in-board` intent.

### Option B — keep the default, generalize the carve-out

Recognize when *any* filter was passed (`--ready`, `--tag`, `--waiting`,
…) and use `filtered` in that case; only fall back to `cards` when no
filter was given. Concretely: introduce `any_filter_explicit` covering
the full set, and replace the current `status_filter_explicit or
args.worker` predicate with it.

Trade-off: more code, but preserves the existing
"`goc --board` with no filters shows the whole deck for capacity
context" behavior.

### Option C — always render every column, cap rows by filter

`render_board` shows every column header always; the row contents of
each column are the intersection of the column's status and the
filtered set. This separates "which columns to show" (always all) from
"which cards to list within a column" (the filter).

Trade-off: largest delta to `render_board`; clearer mental model for
power users, but the no-flag default would change too.

Author's preference: Option B. Minimal behavior delta, removes the
inconsistency, matches what users already expect from the table
renderer.

## Fix sketch (Option B)

```python
# engine.py:2825 (replace)
status_filter_explicit = bool(args.done_flag or args.status_flag is not None)

any_filter_explicit = (
    status_filter_explicit
    or args.worker
    or args.ready
    or args.tags
    or args.contribution
    or args.human_gate
    or args.advances
    or args.advanced_by
    or getattr(args, "waiting", False)
    or args.since
    or getattr(args, "closed_since", None)
    or args.stage_flag
)

# engine.py:2858 (replace)
if args.board:
    board_cards = filtered if any_filter_explicit else cards
```

(Or, equivalently, introduce a small helper that returns `True` when
any global filter argument is non-default. The exact spelling is the
human's call.)
