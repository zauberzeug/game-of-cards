---
title: render-verdict-reimplements-apply-dod-rewrites-fixable-predicate-and-drifts
status: open
stage: null
contribution: medium
created: "2026-06-27T01:59:44Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - quality-pass-llm-counts-fixless-dod-issue-as-proposed-rewrite
  - quality-pass-renderer-counts-whitespace-only-fix-dod-issue-as-rewrite
  - quality-pass-dod-rewrite-with-empty-fix-blanks-the-criterion-text
tags: [bug, meta-fix, api-contract]
summary: "`_render_verdict` and `_apply_dod_rewrite` each carry their own copy of the predicate 'this DoD issue is an applicable rewrite' (`idx` + `fix` + non-whitespace `fix`). The two copies have already drifted apart twice, each time fixed pointwise by a separate card. Extract a single shared predicate both call so they cannot diverge again."
definition_of_done: |
  - [ ] PROCESS: the homing + signature is chosen from "## Decision required" (option 1 or 2, or a recorded alternative) and the gate is lowered to `none` via `goc decide`.
  - [ ] MECHANICAL: the "applicable DoD rewrite" rule lives in exactly ONE place in `goc/engine.py`; both `_render_verdict` and `_apply_dod_rewrite` consume it — no second copy of the `idx`/`fix`/`.strip()` clause remains (grep confirms a single occurrence).
  - [ ] TDD: a regression test feeds a matrix of issue shapes (`{idx,fix}`, `{idx}` no-fix, `{idx, whitespace-fix}`) and asserts `_render_verdict`'s `has_rewrite`/printed classification agrees with what `_apply_dod_rewrite` would write for the same input.
  - [ ] TDD: the existing `tests/test_render_verdict_rewrite_count.py` cases stay green (no regression to the two prior pointwise fixes).
  - [ ] PROCESS: `uv run goc validate` passes and the plugin engine mirrors are re-synced.
---

# `_render_verdict` and `_apply_dod_rewrite` reimplement the "fixable DoD rewrite" predicate and keep drifting

## Location

`goc/engine.py` — `_render_verdict` (the `_is_fixable` helper in the DoD
branch) and `_apply_dod_rewrite` (the `fix_by_idx` comprehension guard).

## What's broken (the recurring shape)

Whether a verdict's `dod_issues` entry is an *applicable rewrite* is
decided in two places that must agree but each spell the rule out
independently:

- **Apply side** — `_apply_dod_rewrite`:
  ```python
  fix_by_idx = {
      issue["idx"]: issue["fix"]
      for issue in issues
      if "idx" in issue and "fix" in issue and issue["fix"].strip()
  }
  ```
- **Render side** — `_render_verdict` (after this card's predecessor):
  ```python
  def _is_fixable(issue: dict) -> bool:
      return "idx" in issue and "fix" in issue and bool(issue["fix"].strip())
  ```

These are the same predicate written twice. They drive coupled
behaviour: the render side computes `has_rewrite` (the
`"N with proposed rewrites"` tally and whether
`_apply_verdict_interactive` is entered), and the apply side decides
what is actually written. When they disagree, `quality-pass --llm`
either advertises a rewrite it won't apply or skips one it claims.

This duplication has already caused **two** filed defects, each a
pointwise resync rather than a structural fix:

1. [quality-pass-llm-counts-fixless-dod-issue-as-proposed-rewrite](../quality-pass-llm-counts-fixless-dod-issue-as-proposed-rewrite/)
   (closed 2026-06-21) — render side missed the `"fix" in issue` clause.
2. [quality-pass-renderer-counts-whitespace-only-fix-dod-issue-as-rewrite](../quality-pass-renderer-counts-whitespace-only-fix-dod-issue-as-rewrite/)
   (closed 2026-06-27) — render side missed the `.strip()` clause that
   [quality-pass-dod-rewrite-with-empty-fix-blanks-the-criterion-text](../quality-pass-dod-rewrite-with-empty-fix-blanks-the-criterion-text/)
   (closed 2026-06-24) had added to the apply side.

The render and apply copies are byte-equivalent again *today*, but the
structure that let them drift twice is unchanged: a future edit to one
guard (e.g. adding a `fix` type check, or accepting `idx == 0`
falsy-edge handling) will silently desync them a third time.

## Why it matters

This is a member of the deck's established "two surfaces reimplement
one rule and keep drifting" meta-fix family (cf.
`renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift`,
`dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting`,
`yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting`).
The resolution shape that family settled on is extraction: one
canonical predicate, every consumer calls it. Until that lands here,
each future divergence costs a fresh audit + reproduce + fix cycle —
the exact overhead the meta-fix family exists to retire.

**Reachability:** both functions are on the live
`goc quality-pass --llm` path — `_cmd_quality_pass` parses the LLM
verdict, `_render_verdict` reports it, `_apply_verdict_interactive`
calls `_apply_dod_rewrite` to write accepted fixes.

## Decision required

The fix is mechanically clear *once the home is chosen*; the open
question is where the canonical predicate lives and what it returns,
which is a design call (hence the gate):

1. **Module-level boolean predicate.** Extract
   `def _dod_issue_is_fixable(issue: dict) -> bool` at module scope;
   `_render_verdict` filters with it and `_apply_dod_rewrite` builds
   `fix_by_idx` by filtering with it. Smallest change; the apply side
   still re-reads `issue["fix"]` after the guard.
2. **Single canonical extractor.** Extract
   `def _applicable_dod_fixes(issues) -> dict[int, str]` (the
   `fix_by_idx` builder) as the one source of truth; `_render_verdict`
   derives `fixable`/`fixless` by membership in its keys. Removes the
   second `issue["fix"]` read entirely but reshapes the render branch's
   per-issue printing (it currently prints `issue['fix']` directly).

Pick the homing + signature, then implement and add a regression test
that asserts render and apply agree on a matrix of issue shapes
(`{idx,fix}`, `{idx}` no-fix, `{idx, whitespace-fix}`, and any future
edge the chosen predicate must cover) so a third drift is caught by
the suite, not a future audit.
