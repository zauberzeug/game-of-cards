---
title: quality-pass-llm-counts-fixless-dod-issue-as-proposed-rewrite
status: active
stage: null
contribution: medium
created: "2026-06-21T05:33:18Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `deck/<title>/reproduce.py` calls `_render_verdict` with an OK title/summary and a single `dod_issues` entry that carries no `fix` (e.g. `{"idx": 0, "issue": "vague"}`), and asserts the buggy `has_rewrite == True` while the apply path (`_apply_dod_rewrite`) would write nothing.
  - [ ] FIX: in `goc/engine.py` `_render_verdict`, only set `has_rewrite = True` for DoD issues that would actually be applied — mirror `_apply_dod_rewrite`'s `"idx" in issue and "fix" in issue` guard; fixless flagged issues print as "flagged, no rewrite offered" without counting.
  - [ ] TDD: after the fix, the fixless-DoD verdict returns `has_rewrite == False`; a DoD issue with both `idx` and `fix` still returns `True` (regression for `test_dod_issues_still_counted`).
  - [ ] EMPIRICAL: rerun reproduce.py against the patched engine; record before/after output in this body's "Empirical evidence" section.
  - [ ] PROCESS: `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# `goc quality-pass --llm` counts a fixless DoD issue as a proposed rewrite

## Location

`goc/engine.py` — `_render_verdict` (the DoD branch):

```python
dod_issues = verdict.get("dod_issues") or []
if dod_issues:
    has_rewrite = True
    print(f"dod:     {len(dod_issues)} issue(s)")
    for issue in dod_issues:
        print(f"  [{issue.get('idx', '?')}] {issue.get('issue', '?')}")
        print(f"      fix: {issue.get('fix', '?')}")
```

## What's broken

`_render_verdict` returns `has_rewrite`, which drives two things in
`_cmd_quality_pass`:

1. the `rewrite_count` tally printed as `"N cards with proposed
   rewrites"` (the line `--dry-run` exercises); and
2. whether `_apply_verdict_interactive` is even invoked for that card.

The DoD branch sets `has_rewrite = True` for **any** non-empty
`dod_issues` list, regardless of whether each issue carries an
applicable `fix`. But the apply path `_apply_dod_rewrite` only ever
writes issues that have **both** `idx` and `fix`:

```python
fix_by_idx = {issue["idx"]: issue["fix"] for issue in issues if "idx" in issue and "fix" in issue}
```

So a verdict whose only DoD content is `{"idx": 0, "issue": "vague"}`
(no `fix`) is counted toward `rewrite_count` and prints a bogus
`fix: ?` line, while the apply path offers/writes nothing. The
display/dry-run count overstates the work, and a non-dry-run pass even
enters the interactive apply loop for a card with no applicable edit.

## Why it matters / reachability

The Sonnet pass (`_run_sonnet_quality_pass`) parses raw JSON from the
`claude` CLI; the LLM is free to emit a DoD issue describing a problem
without a concrete `fix` string. That payload flows straight into
`_render_verdict`. This is the same render-vs-apply misalignment the
HEAD commit `678594d`
(`quality-pass-llm-counts-rewriteless-verdict-as-proposed-rewrite`)
fixed for the **title** and **summary** branches — it gated those on a
truthy `rewrite` string but left the DoD branch counting fixless
issues. This card closes the third dimension so all three branches of
`_render_verdict` agree with `_apply_verdict_interactive`.

Distinct from the open card
`goc-quality-pass-overstates-dod-rewrite-count-and-drops-unmatched-fixes`,
which is about the **apply-side** count in `_apply_dod_rewrite` /
`_apply_verdict_interactive` (out-of-range / duplicate `idx`). This
card is about `_render_verdict`'s `has_rewrite` return — a different
function and the path `--dry-run` exercises.

## Decision (mechanical — no gate)

No design choice: the correct behavior is fully determined by the
existing apply-side guard (`"idx" in issue and "fix" in issue`) and by
the pattern the HEAD commit already applied to the two sibling
branches. Render counts only what apply will write.

## Empirical evidence

(to be filled by reproduce.py before/after the fix)
