---
title: quality-pass-dod-rewrite-with-empty-fix-blanks-the-criterion-text
status: done
stage: null
contribution: medium
created: "2026-06-24T07:57:36Z"
closed_at: "2026-06-24T08:02:01Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: "`_apply_dod_rewrite` (`goc/engine.py:3707-3725`) replaces DoD checkbox lines by index using each verdict issue's `fix` string, applying any issue that merely has an `idx` and `fix` key with no check that `fix` is non-empty — so an empty `fix` blanks the criterion text to a bare `- [ ]`, contradicting the docstring's 'other items preserved verbatim' promise."
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (an empty/whitespace `fix` no longer blanks the criterion)
  - [x] TDD: a regression test asserts an accepted issue with `fix: ""` leaves the targeted DoD line verbatim
  - [x] TDD: a non-empty `fix` for another index in the same call still applies (no regression to normal rewrites)
  - [x] MECHANICAL: the guard lives in `_apply_dod_rewrite` and preserves the original line; existing rewrite tests stay green
  - [x] PROCESS: log.md records the fix and the preserve-original semantics chosen
worker: {who: "claude[bot]", where: main}
---

# quality-pass DoD rewrite with an empty `fix` blanks the criterion text

## Location

`goc/engine.py:3707-3725` — `_apply_dod_rewrite`.

## What's broken

`_apply_dod_rewrite` replaces specific DoD checkbox lines by 0-based
index using the `fix` string carried on each accepted verdict issue.
Its own docstring promises *"Other items preserved verbatim."* But it
applies any issue that simply *has* an `idx` and a `fix` key — with no
check that `fix` is non-empty:

```python
fix_by_idx = {issue["idx"]: issue["fix"] for issue in issues if "idx" in issue and "fix" in issue}
for box_idx, line_idx in enumerate(box_indices):
    if box_idx in fix_by_idx:
        indent = re.match(r"[ \t]*", lines[line_idx]).group(0)
        new_text = fix_by_idx[box_idx]
        new_text = new_text.lstrip()
        if not new_text.startswith("- ["):
            new_text = f"- [ ] {new_text}"
        lines[line_idx] = indent + new_text
```

When `fix` is `""` (or whitespace-only), `new_text` becomes `""`, the
`- [` prefix test fails, and the line is rewritten to the literal
`"- [ ] "` — an unchecked box with **no criterion text at all**. The
prior item's content is silently destroyed.

## Empirical evidence

`reproduce.py` (run on a clean checkout) feeds the verdict
`[{"idx": 0, "fix": ""}]` against a two-item DoD:

```
BEFORE: ['- [ ] TDD: regression test proves the fix', '- [ ] implement the guard']
AFTER : ['- [ ] ', '- [ ] implement the guard']
FAIL: item 0 criterion text was blanked by an empty fix
```

The criterion `TDD: regression test proves the fix` is gone, replaced
by an empty checkbox that asserts nothing.

## Why it matters

`goc quality-pass --llm` parses an LLM verdict whose `dod_issues`
entries each carry an `idx` + `fix`. The render path
(`engine.py:3680-3683`) and `_apply_verdict_interactive`
(`engine.py:3728+`) impose **no non-empty check** on `fix` — an empty
`fix` is classified as `fixable` (it has the key), printed as
`fix: ` (blank), accepted, and applied through `_apply_dod_rewrite`.
So a model that emits `{"idx": 0, "fix": ""}` — a plausible "I flagged
this item but offered no replacement text" shape — silently erases an
authored DoD criterion. Because `goc done` only counts boxes
(`- [ ]` still counts), the blanked item never resurfaces as a missing
box; the closure contract is quietly hollowed out.

This is distinct from
[goc-quality-pass-overstates-dod-rewrite-count-and-drops-unmatched-fixes](../goc-quality-pass-overstates-dod-rewrite-count-and-drops-unmatched-fixes/),
which covers an *out-of-range or duplicate* `idx` being silently
dropped (no line touched). Here the `idx` is in range and the line IS
touched — destructively — because the `fix` value is empty.

## Fix

In `_apply_dod_rewrite`, treat an empty/whitespace-only `fix` as
"no rewrite offered" and preserve the original line verbatim, matching
the docstring contract. The cleanest single-site guard skips such
entries when building `fix_by_idx`:

```python
fix_by_idx = {
    issue["idx"]: issue["fix"]
    for issue in issues
    if "idx" in issue and "fix" in issue and issue["fix"].strip()
}
```

An empty fix then leaves the targeted item untouched, the same outcome
as the `fixless` (no-`fix`-key) path the renderer already distinguishes.
