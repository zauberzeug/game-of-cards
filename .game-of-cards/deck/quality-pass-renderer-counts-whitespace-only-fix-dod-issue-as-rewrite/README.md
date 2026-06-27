---
title: quality-pass-renderer-counts-whitespace-only-fix-dod-issue-as-rewrite
status: done
stage: null
contribution: medium
created: "2026-06-27T01:53:16Z"
closed_at: "2026-06-27T01:58:24Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py feeds `_render_verdict` an OK title/summary and one `dod_issues` entry with `{"idx": 0, "fix": "   "}` (whitespace-only), and asserts the buggy `has_rewrite == True` while `_apply_dod_rewrite` would write nothing for the same input.
  - [x] FIX: in `goc/engine.py` `_render_verdict`, the `fixable` classifier mirrors `_apply_dod_rewrite`'s full guard — `"idx" in issue and "fix" in issue and issue["fix"].strip()` — so a whitespace-only `fix` is demoted to the `fixless` (no-rewrite) path.
  - [x] TDD: after the fix, the whitespace-`fix` verdict returns `has_rewrite == False` and prints under "flagged, no rewrite offered"; an issue with a real non-empty `fix` still returns `True` (no regression). Covered by `tests/test_render_verdict_rewrite_count.py::test_whitespace_only_fix_dod_issue_not_counted` and `::test_mixed_whitespace_fix_and_real_fix_dod_issues`.
  - [x] EMPIRICAL: rerun reproduce.py against the patched engine; record before/after output in this body's "Empirical evidence" section.
  - [x] PROCESS: `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# quality-pass renderer counts a whitespace-only-`fix` DoD issue as a proposed rewrite

## Location

`goc/engine.py:3803-3807` — `_render_verdict` (the DoD branch's classifier).

## What's broken

`_render_verdict` splits `dod_issues` into `fixable` (counted toward
`has_rewrite`, printed as `dod: N issue(s)` with a `fix:` line) and
`fixless` (printed as "flagged, no rewrite offered"). Its comment
states it mirrors `_apply_dod_rewrite`'s guard:

```python
# Mirror _apply_dod_rewrite's guard: only an issue carrying both `idx` and
# `fix` is an applicable rewrite, so only those count. A flagged-but-fixless
# issue prints for visibility but does NOT count toward has_rewrite.
fixable = [issue for issue in dod_issues if "idx" in issue and "fix" in issue]
fixless = [issue for issue in dod_issues if not ("idx" in issue and "fix" in issue)]
```

But `_apply_dod_rewrite` carries a **third** condition the classifier
omits — `issue["fix"].strip()` — added so a whitespace-only `fix`
means "no rewrite offered" and the original DoD item is preserved
verbatim (`goc/engine.py:3845-3852`):

```python
# An empty/whitespace-only `fix` means "no rewrite offered" — keep the
# original item verbatim (per this function's contract) rather than
# blanking it to "- [ ] ". Mirrors the `fixless` (no-`fix`-key) path.
fix_by_idx = {
    issue["idx"]: issue["fix"]
    for issue in issues
    if "idx" in issue and "fix" in issue and issue["fix"].strip()
}
```

So for an issue like `{"idx": 0, "issue": "vague", "fix": "   "}`, the
two functions disagree: the renderer classifies it as `fixable`, sets
`has_rewrite = True`, and prints it as `dod: 1 issue(s)` with an empty
`fix:` line — while the apply path treats it as `fixless` and writes
nothing. The renderer therefore violates its own stated contract
("Mirrors the `fixless` (no-`fix`-key) path") and overstates the
rewrite work.

## Empirical evidence

`reproduce.py` feeds the verdict
`{"idx": 0, "issue": "vague item", "fix": "   "}`.

Before the fix it exited non-zero:

```
=== x ===
title:   OK
summary: OK
dod:     1 issue(s)
  [0] vague item
      fix:
has_rewrite (renderer)      = True
apply path would write      = {}  (empty -> no rewrite)

FAIL: renderer counts this as a rewrite (has_rewrite=True) but the apply path writes nothing — render/apply disagree on a whitespace-only fix.
```

After the fix it exits zero — the renderer demotes the whitespace-only
fix to the "no rewrite offered" path, matching the apply path:

```
=== x ===
title:   OK
summary: OK
dod:     1 flagged, no rewrite offered
  [0] vague item
has_rewrite (renderer)      = False
apply path would write      = {}  (empty -> no rewrite)

PASS: renderer agrees with the apply path (whitespace-only fix is not a rewrite).
```

## Why it matters

`has_rewrite` drives two downstream behaviours in `_cmd_quality_pass`:
(1) the `"N cards with proposed rewrites"` tally exercised by
`--dry-run`, and (2) whether `_apply_verdict_interactive` is even
entered for the card. A whitespace-`fix` issue inflates the dry-run
count and pushes a card into the interactive apply loop even though
`_apply_dod_rewrite` will preserve the line verbatim and offer no
edit — wasted prompts plus a count that overstates the actual work.

**Reachability:** the offending input is an LLM verdict produced by
`goc quality-pass --llm`, parsed in `_cmd_quality_pass` and handed to
`_render_verdict`. A model emitting an `idx`+`fix` issue whose `fix`
is empty or whitespace is exactly the shape the closed sibling
[quality-pass-dod-rewrite-with-empty-fix-blanks-the-criterion-text](../quality-pass-dod-rewrite-with-empty-fix-blanks-the-criterion-text/)
hardened the *apply* path against; that fix added the `.strip()` guard
to `_apply_dod_rewrite` (2026-06-24) but left `_render_verdict`'s
classifier — added earlier by
[quality-pass-llm-counts-fixless-dod-issue-as-proposed-rewrite](../quality-pass-llm-counts-fixless-dod-issue-as-proposed-rewrite/)
(2026-06-21) — at the two-condition form. This card closes the gap
between the two so render and apply agree.

## Fix

In `_render_verdict` (`goc/engine.py:3806`), add the missing
`.strip()` clause so the `fixable` classifier matches the applier's
`fix_by_idx` guard exactly:

```python
fixable = [issue for issue in dod_issues if "idx" in issue and "fix" in issue and issue["fix"].strip()]
fixless = [issue for issue in dod_issues if not ("idx" in issue and "fix" in issue and issue["fix"].strip())]
```

The `fixless` negation is updated symmetrically so a whitespace-`fix`
issue is printed under "flagged, no rewrite offered" rather than
dropped from both lists.
