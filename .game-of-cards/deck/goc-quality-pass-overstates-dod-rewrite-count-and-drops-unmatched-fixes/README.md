---
title: goc-quality-pass-overstates-dod-rewrite-count-and-drops-unmatched-fixes
summary: "`_apply_dod_rewrite` (engine.py:3429) only mutates a DoD line when an accepted issue's `idx` falls inside the card's `box_indices`. An accepted fix whose `idx` is out of range — or a duplicate idx that collides with another accepted fix — is silently dropped. But the caller `_apply_verdict_interactive` (engine.py:3487) unconditionally sets `applied[\"dod\"] = len(accepted_issues)` and prints `DoD: N item(s) rewritten`, so the count and per-card tally are overstated and a fix the operator explicitly accepted vanishes with no signal."
status: open
stage: null
contribution: medium
created: "2026-06-10T04:37:46Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `deck/<title>/reproduce.py` builds a 2-checkbox card, accepts (auto_yes) a `dod_issues` entry with out-of-range `idx: 5`, and asserts the reported `applied["dod"]` count diverges from the number of lines actually rewritten (fix text absent, originals preserved)
  - [ ] PROCESS: decide the fix path (see `## Decision required`) and implement it in `goc/engine.py`
  - [ ] TDD: after the fix, the reported count equals the number of DoD lines actually rewritten for both the out-of-range-idx and duplicate-idx cases
  - [ ] EMPIRICAL: rerun reproduce.py against the patched engine; expected output recorded in this body's "Empirical evidence" section
  - [ ] PROCESS: `uv run goc validate` passes
---

# `goc quality-pass --llm` overstates the DoD rewrite count and silently drops unmatched fixes

## Location

- `goc/engine.py:3420-3437` — `_apply_dod_rewrite`. The fix is applied
  only when `box_idx in fix_by_idx` for a real box (lines 3429-3435).
- `goc/engine.py:3477-3488` — `_apply_verdict_interactive`. Line 3487
  sets `applied["dod"] = len(accepted_issues)` and line 3488 prints the
  same count, regardless of how many lines `_apply_dod_rewrite` mutated.

## What's broken

`_apply_dod_rewrite` keys accepted fixes by their `idx`, then walks the
card's real checkbox positions and applies a fix only when its index
matches:

```python
fix_by_idx = {issue["idx"]: issue["fix"] for issue in issues if "idx" in issue and "fix" in issue}
for box_idx, line_idx in enumerate(box_indices):
    if box_idx in fix_by_idx:
        ...
        lines[line_idx] = new_text
```

An accepted issue whose `idx` is **out of range** (no `box_idx` ever
equals it) is silently dropped. So is the loser when **two accepted
issues share the same `idx`** (the dict comprehension keeps only the
last). Neither case produces a warning or a return value the caller can
inspect — `_apply_dod_rewrite` returns `None`.

The caller then reports a count it never verified:

```python
if accepted_issues:
    ...
    _apply_dod_rewrite(target_card, accepted_issues)
    applied["dod"] = len(accepted_issues)
    print(f"    DoD: {len(accepted_issues)} item(s) rewritten")
```

`applied["dod"]` and the printed `N item(s) rewritten` count **accepted**
issues, not **applied** ones. When an accepted fix is dropped, the
operator is told a rewrite they explicitly approved landed when it did
not, and the per-card summary tally (`_cmd_quality_pass` aggregates
`applied["dod"]`) is inflated.

## Empirical evidence

`deck/<title>/reproduce.py` builds a card with exactly two DoD
checkboxes and drives `_apply_verdict_interactive` (with `auto_yes=True`,
the same accept path an interactive `y` takes) with one accepted issue
targeting the nonexistent `idx: 5`:

```
    DoD: 1 item(s) rewritten
reported applied['dod']           : 1
accepted fix text present in DoD  : False
original items preserved          : True

DEFECT CONFIRMED: caller reported 1 DoD item rewritten, but the
accepted fix text never landed in the DoD — idx 5 matched no
checkbox so the fix was silently dropped, and the count was
overstated. The operator is told a fix they accepted was applied.
```

## Why it matters

`goc quality-pass --llm` feeds the model the raw `definition_of_done`
string (`_build_quality_prompt`) and asks it to return 0-based box
indices it infers by counting checkbox lines. The model's count diverges
from `_dod_box_indices` whenever the DoD contains checkbox-shaped lines
inside fenced code blocks, freeform `- [ ]` prose that isn't a real DoD
item, or simple off-by-one miscounting — so an out-of-range `idx` is a
realistic, recurring input, not a contrived one. (Duplicate `idx`
collisions arise the same way.) When it happens, the tool silently
under-delivers while reporting success: the human believes the deck was
groomed, but an accepted rewrite was dropped. This is the inverse of the
sibling defect [goc-quality-pass-dod-rewrite-silently-unchecks-previously-checked-items](../goc-quality-pass-dod-rewrite-silently-unchecks-previously-checked-items/)
(there a matching idx writes the *wrong* prefix; here a non-matching idx
writes *nothing* but is still counted). It is distinct from
[dod-rewrite-box-index-skips-uppercase-checked-boxes](../dod-rewrite-box-index-skips-uppercase-checked-boxes/)
(box-index misalignment landing on the wrong line) and
[goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards](../goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards/)
(terminal-status guard).

## Decision required

The count must reflect what was actually written, and an accepted-but-
unapplied fix must not vanish silently. Two credible fix shapes:

**Option A — count actuals, warn on the rest.** Make `_apply_dod_rewrite`
return the set (or count) of `idx` values it actually applied. The caller
sets `applied["dod"]` to that count, prints the true number, and emits a
`WARNING: DoD fix for idx N skipped (no matching checkbox)` to stderr for
each accepted-but-dropped idx. Smallest change; preserves the current
"best-effort apply" behavior but stops lying about it.

**Option B — validate before applying.** Reject the whole verdict (or the
offending issue) up front when an accepted `idx` is out of range or
collides, surfacing the mismatch as an error before any write. Stricter;
treats a bad idx as a hard contract violation rather than a skipped item.

Recommendation: **Option A** — it matches the engine's existing
best-effort, non-fatal posture for LLM verdicts (a bad title/summary
rewrite already degrades gracefully rather than aborting the pass) and
gives the operator both an honest count and an actionable warning. Decide
A vs B (and the exact warning wording / stream) before implementing.
