---
title: auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft
summary: "With `workflow.auto_commit: true`, the two-card edge mutations (`goc status <old> superseded --by <draft>`, `goc advance <card> --by <draft>`) commit only the non-draft endpoint: `_git_auto_commit`'s `exclude_draft` filter silently drops the draft dir from the commit set, publishing a `superseded_by`/`advanced_by` pointer to a card that does not exist in the committed tree. Every fresh checkout then fails `goc validate` with `references unknown title`."
status: open
stage: null
contribution: high
created: "2026-07-05T01:33:09Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded (which option below), gate lowered to none
  - [ ] TDD: reproduce.py exits zero (no dangling edge in the committed tree for both the `advance --by <draft>` and `status … superseded --by <draft>` variants)
  - [ ] TDD: regression test covers the chosen behavior for both two-card verbs under `auto_commit: true`
  - [ ] PROCESS: `_git_auto_commit`'s docstring reconciled with the chosen behavior (its current justification only covers the mutated card, not the counterpart endpoint)
---

# Auto-commit publishes dangling edges when the counterpart endpoint is a draft

## Location

- `goc/engine.py:4343-4353` — `_git_auto_commit`'s `exclude_draft` filter.
- `goc/engine.py:5234-5237` — `_cmd_status`: `commit_targets = [card_dir]`
  plus `DECK_DIR / successor` for `superseded --by`.
- `goc/engine.py:5710` / `:5725` — `_cmd_advance` / `_cmd_unadvance`:
  `_git_auto_commit([DECK_DIR / title, DECK_DIR / advancer], ...)`.

## What's broken

`_git_auto_commit` drops draft cards from the commit set:

```python
if exclude_draft:
    kept: list[Path] = []
    for d in card_dirs:
        ...
        if c is not None and card_is_draft(c):
            continue
        kept.append(d)
    card_dirs = kept
```

Its docstring justifies this with:

> Verbs that legitimately commit a freshly-authored card clear the draft
> flag first (`goc publish` / `goc status active` / `goc done`), so the
> card is no longer a draft by the time it reaches here.

That holds only for the card whose *status* is mutated. The two-card edge
verbs pass a **counterpart** endpoint whose draft flag is neither cleared
nor checked: `goc advance <card> --by <draft-epic>` writes `advanced_by:
[draft-epic]` into `<card>` and `advances: [card]` into the draft, then
commits only `<card>` — the draft dir is silently filtered out, with no
warning that the commit was split. Same for `goc status <old> superseded
--by <draft-successor>`.

The lone caller that opts out (`goc new --commit`,
`engine.py:5426-5431`, `exclude_draft=False`) exists precisely "to avoid a
half-edge (one endpoint committed, the other left untracked)" — the exact
failure the two-card verbs now reproduce.

## Empirical evidence

`uv run python .game-of-cards/deck/auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft/reproduce.py`:

```
setup: fresh git repo, workflow.auto_commit: true, parent-card committed
goc publish parent-card (draft cleared, committed) ...
goc new draft-epic (stays draft) ...
goc advance parent-card --by draft-epic ...
committed HEAD touches: .game-of-cards/deck/parent-card/README.md
untracked (dropped from commit): ?? .game-of-cards/deck/draft-epic/
DEFECT: committed tree has parent-card.advanced_by -> 'draft-epic' but no such card dir in HEAD
```

Related manifestation observed while reproducing: when the *mutated* card
is itself still a draft (e.g. `goc new parent --commit` without publish),
the filter empties the whole commit set and the edge write lands in
neither endpoint — the mutation silently lingers uncommitted, with no
notice that auto-commit was skipped.

## Why it matters

`auto_commit: true` exists for multi-agent shared-main operation — each
mutation lands atomically so parallel sessions see consistent deck state.
This defect makes the flagship two-card mutations non-atomic in exactly
that mode: any other agent (or CI) checking out the pushed commit gets a
deck that fails `goc validate` with `references unknown title`, and the
referential-integrity invariant ("closed-card relationship edges are
first-class; validate enforces both axes") is broken in the committed
record. Reachability: `goc new <epic>` (default no-commit, born draft)
followed by `goc advance <child> --by <epic>` is the documented
aggregation-epic wiring order; with auto_commit on, the split commit
happens on the standard path. Introduced by the fix for
[placeholder-cards-superseded-before-they-are-authored](../placeholder-cards-superseded-before-they-are-authored/)
(commit e861360), whose resolution never considered the successor/advancer
endpoint being a draft.

## Decision required

**Reasoning.** Two guards are in tension. The draft filter exists so
auto-commit never publishes a half-written placeholder (the
dedup/supersede race). The half-edge rule exists so an edge mutation never
commits one endpoint without the other. When the counterpart of an edge
mutation is a draft, satisfying one guard violates the other — picking
blindly either re-opens the placeholder race or keeps shipping corrupt
committed trees. A human should pick which invariant bends.

**Option A — commit the draft counterpart together with the edge
(atomicity wins).** Pass `exclude_draft=False` from the two-card call
sites at `engine.py:5237`, `:5710`, `:5725`.

- Pros: committed tree always validates; matches the `goc new --commit`
  precedent and the half-edge rule; smallest behavior change.
- Cons: publishes a scaffold-placeholder card body to shared main — the
  exact exposure the draft state was added to prevent (though the draft
  flag itself still hides it from queues and dedup automation).
- Preview: pass `exclude_draft=False` explicitly at the three call sites;
  no signature change.

**Option B — refuse the edge mutation while the counterpart is a draft
(draft protection wins).** In `_cmd_status`/`_cmd_advance`/`_cmd_unadvance`,
error out with "counterpart is a draft; `goc publish <title>` it first"
before writing either endpoint.

- Pros: both invariants preserved; the error teaches the publish step;
  no placeholder ever ships.
- Cons: breaks the documented epic-wiring flow (`goc new <epic>` then
  `goc advance <child> --by <epic>` now requires an intervening publish);
  strictness applies even when auto_commit is off, where the split-commit
  problem does not exist — unless the refusal is conditioned on
  auto_commit, adding mode-dependent behavior.
- Preview: guard before the `write_text` pairs at `engine.py:~5230` and
  `:~5700`.

**Option C — warn and skip the whole commit (leave both endpoints
uncommitted).** If any target is a draft, `_git_auto_commit` commits
nothing and prints a "left uncommitted: counterpart is a draft" notice.

- Pros: never publishes a placeholder, never publishes a half-edge;
  no workflow breakage.
- Cons: silently downgrades auto_commit's atomicity promise — mutations
  linger as ambient worktree changes that the next unrelated commit may
  sweep up, which is the failure auto_commit was built to avoid.
- Preview: change the filter at `engine.py:4343-4353` to all-or-nothing
  plus a stderr notice.

**Recommendation.** Option A — the committed-tree referential-integrity
invariant is load-bearing for every consumer (`goc validate` gates CI),
while draft exposure is already mitigated by the flag itself hiding the
card from queues and automation; it also matches the engine's own
`goc new --commit` precedent for edge atomicity.
