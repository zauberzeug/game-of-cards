---
title: quality-pass-verdict-with-null-fix-crashes-render-and-apply-paths
status: open
stage: null
contribution: medium
created: "2026-07-22T13:18:58Z"
closed_at: null
human_gate: decision
advances:
  - render-verdict-reimplements-apply-dod-rewrites-fixable-predicate-and-drifts
advanced_by: []
tags: [bug, api-contract]
summary: "A `goc quality-pass --llm` verdict whose `dod_issues` entry carries `\"fix\": null` (or any non-string) crashes both duplicated fixable-predicate sites — `_render_verdict`'s `_is_fixable` and `_apply_dod_rewrite`'s `fix_by_idx` guard — with a raw AttributeError, after the expensive LLM subprocess already succeeded. The `_cmd_quality_pass` try/except wraps only the subprocess call, so the traceback escapes uncaught."
definition_of_done: |
  - [ ] PROCESS: the fix shape is chosen from "## Decision required" (pointwise type guard now vs folding into the shared-predicate extraction) and the gate is lowered to `none` via `goc decide`.
  - [ ] TDD: reproduce.py prints no `[FAIL]` (both sites classify a `fix: null` / non-string `fix` issue as fixless instead of raising).
  - [ ] TDD: a regression test feeds `{idx, fix: None}` and `{idx, fix: 42}` issues through both the render and apply paths and asserts fixless classification with no exception.
  - [ ] MECHANICAL: plugin engine mirrors re-synced (`python scripts/sync_plugin_assets.py --check` clean).
  - [ ] PROCESS: `uv run goc validate` passes.
---

# quality-pass verdict with `"fix": null` crashes the render and apply paths

## Location

`goc/engine.py:4016` (`_is_fixable` inside `_render_verdict`) and
`goc/engine.py:4060` (`fix_by_idx` comprehension in
`_apply_dod_rewrite`).

## What's broken

Both copies of the fixable-DoD-rewrite predicate call `.strip()` on
`issue["fix"]` without checking it is a string:

```python
def _is_fixable(issue: dict) -> bool:
    return "idx" in issue and "fix" in issue and bool(issue["fix"].strip())
```

```python
fix_by_idx = {
    issue["idx"]: issue["fix"]
    for issue in issues
    if "idx" in issue and "fix" in issue and issue["fix"].strip()
}
```

The verdict JSON comes from an LLM subprocess. `"fix": null` is a
shape the prompt contract never forbids and one models naturally emit
for "flagged, no rewrite offered" — the exact semantic the fixless
path exists for. On such a verdict both sites raise
`AttributeError: 'NoneType' object has no attribute 'strip'` (a
numeric `fix` crashes identically). The `try/except (ValueError,
json.JSONDecodeError, RuntimeError)` in `_cmd_quality_pass` wraps only
`_run_sonnet_quality_pass`, not the render/apply loop, so the
traceback escapes raw — after the expensive `claude` call already
succeeded, and in non-dry-run potentially midway through applying
earlier cards' rewrites.

## Empirical evidence

`uv run python .game-of-cards/deck/quality-pass-verdict-with-null-fix-crashes-render-and-apply-paths/reproduce.py`:

```
=== some-card ===
title:   OK
summary: OK
_render_verdict: AttributeError: 'NoneType' object has no attribute 'strip'
_apply_dod_rewrite: AttributeError: 'NoneType' object has no attribute 'strip'

[FAIL] 2/2 sites crash on a null `fix` the prompt contract never forbids; the _cmd_quality_pass try/except wraps only the subprocess call, so this escapes as a traceback.
```

## Why it matters

**Reachability:** both functions sit on the live
`goc quality-pass --llm` path — `_cmd_quality_pass` parses the LLM
verdict, `_render_verdict` reports it, and
`_apply_verdict_interactive` calls `_apply_dod_rewrite` for accepted
fixes. The input is model-authored JSON, i.e. adversarial by nature;
a single `null` turns a completed multi-card LLM pass into a stack
trace and (non-dry-run) can abandon the pass midway with earlier
cards already rewritten.

This is precisely the "future edit" scenario the open meta card
[render-verdict-reimplements-apply-dod-rewrites-fixable-predicate-and-drifts](../render-verdict-reimplements-apply-dod-rewrites-fixable-predicate-and-drifts/)
warns about: a type guard must now be added to the duplicated
predicate, and adding it pointwise to one copy desyncs the other — the
third such desync in the family. This card is wired as advancing that
meta card because the natural home for the guard is the shared
predicate it wants extracted.

## Decision required

1. **Fold into the extraction (preferred by the meta card).** Resolve
   [render-verdict-reimplements-apply-dod-rewrites-fixable-predicate-and-drifts](../render-verdict-reimplements-apply-dod-rewrites-fixable-predicate-and-drifts/)
   first (its own gate is still up), and give the single shared
   predicate the `isinstance(issue.get("fix"), str)` clause — one
   guard, both consumers, no third desync possible.
2. **Pointwise guard now.** Add the `isinstance` check to both copies
   immediately (two-line change) and leave the extraction to the meta
   card. Ships the crash fix without waiting on the meta decision, at
   the cost of writing the duplicated clause the meta card exists to
   retire.
