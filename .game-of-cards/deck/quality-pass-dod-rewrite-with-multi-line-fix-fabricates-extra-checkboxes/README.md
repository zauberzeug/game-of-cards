---
title: quality-pass-dod-rewrite-with-multi-line-fix-fabricates-extra-checkboxes
status: active
stage: null
contribution: medium
created: "2026-06-28T02:27:51Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: regression test proving a multi-line `fix` no longer changes the DoD box count (failing before the fix, passing after)
  - [ ] `_apply_dod_rewrite` collapses embedded newlines in a `fix` so a single-item rewrite stays one physical line
  - [ ] The fix preserves existing behavior (indent restoration, the `- [ ]` prefix injection, the empty-fix no-op guard)
  - [ ] `uv run goc validate` passes
  - [ ] `uv run python -m unittest discover -s tests` passes
worker: {who: "claude[bot]", where: main}
---

# quality-pass DoD rewrite with a multi-line `fix` fabricates extra checkboxes

## Problem

`_apply_dod_rewrite` (`goc/engine.py:3842`) replaces specific DoD items by
0-based index. Its docstring promises a 1-for-1 item replacement
("Replace specific DoD items by 0-based index. Other items preserved
verbatim."), and a DoD item is a single checkbox line.

The rewriter takes the verdict's `fix` string and drops it into a single
line slot:

```python
indent = re.match(r"[ \t]*", lines[line_idx]).group(0)
new_text = fix_by_idx[box_idx]
new_text = new_text.lstrip()
if not new_text.startswith("- ["):
    new_text = f"- [ ] {new_text}"
lines[line_idx] = indent + new_text          # engine.py:3865
```

If `new_text` contains a newline, the embedded `\n` survives into
`lines[line_idx]`. On `"\n".join(lines)` (engine.py:3866) the single
logical item becomes **two or more physical lines**. Because
`_dod_box_indices` / `count_dod_boxes` count checkboxes line-anchored
(`DOD_ANY_BOX.match`, engine.py:698-709), any injected line shaped like
`- [ ]` / `- [x]` is then counted as a real DoD checkbox the operator
never authored — the closure box count grows.

## Why it matters

The `fix` strings are LLM-authored: `_run_sonnet_quality_pass`
(engine.py:3755-3774) shells out to `claude --model sonnet ... --output-format json`
and `json.loads` the result into the verdict's `dod_issues`. An LLM can
readily emit a multi-line `fix` — a wrapped rewrite, or an accidental
second `- [ ]` checkbox in the suggested text. When it does, a
`goc quality-pass --llm` apply silently inflates the card's DoD with a
fabricated checkbox. A fabricated *open* box can later make `goc done`
refuse to close a card whose authored work is in fact complete; a
fabricated line also shifts the index space that subsequent rewrites in
the same batch target. This is the reachability path: LLM verdict →
`_apply_verdict_interactive` → `_apply_dod_rewrite`.

This is distinct from the already-filed
`goc-quality-pass-dod-rewrite-silently-unchecks-previously-checked-items`
(state flip on a single item) and
`goc-quality-pass-overstates-dod-rewrite-count-and-drops-unmatched-fixes`
(miscount of *dropped* fixes): this card is about a fix that *injects
extra* checkbox lines and grows the box count. The sibling indent fix
`dod-rewrite-preserves-indent` only re-applies indent to the first
line, so it does not cover the injected lines either.

## Fix

A DoD item is one line; the rewriter must keep it one line. Collapse any
embedded newline (and the whitespace around it) to a single space before
the `- [ ]` prefix logic, so a single-item rewrite cannot grow the box
count. This is the contract-preserving interpretation — `_apply_dod_rewrite`
replaces *one* item by index, it does not split one item into several.

## Evidence

`reproduce.py` builds a 2-item DoD card and applies a rewrite whose `fix`
contains a newline followed by a `- [ ]` line. Before the fix the DoD
re-emits with **3** open boxes (a fabricated third); the contract
requires it to stay at **2**.
