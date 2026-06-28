---
title: title-antipattern-check-docstring-describes-wrong-return-type
summary: "`_check_title_antipatterns` is annotated `-> list[str]` and returns a list of reason strings, and every caller iterates it as strings — but its docstring claims it returns `(matched_substring, reason)` tuples. Stale docstring contradicting the implementation and the type annotation; a maintainer trusting the docstring would unpack each element as a 2-tuple and break."
status: done
stage: null
contribution: low
created: "2026-06-28T01:37:05Z"
closed_at: "2026-06-28T01:40:30Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, api-contract]
definition_of_done: |
  - [x] MECHANICAL: the docstring of `_check_title_antipatterns` no longer claims it returns tuples; it describes the actual return value (a list of reason strings) and matches the `-> list[str]` annotation.
  - [x] TDD: a regression test asserts every element returned by `_check_title_antipatterns` for a jargon title is a `str` (not a tuple), pinning the contract the docstring now describes.
worker: {who: "claude[bot]", where: main}
---

# Title-antipattern check docstring describes the wrong return type

## Location

`goc/engine.py:5043-5045`, the helper `_check_title_antipatterns`.

## What's broken

The function is annotated to return `list[str]` and its body returns a
list of plain reason strings:

```python
def _check_title_antipatterns(title: str) -> list[str]:
    """Return list of (matched_substring, reason) tuples; empty if title is clean."""
    return [reason for pat, reason in TITLE_ANTIPATTERNS if pat.search(title)]
```

The comprehension binds `for pat, reason in TITLE_ANTIPATTERNS` and
yields only `reason` — a `str`. The docstring, however, claims the
return value is a list of `(matched_substring, reason)` **tuples**. The
docstring contradicts both the `-> list[str]` annotation and the
implementation.

Both callers treat each element as a string, confirming the code (not
the annotation/callers) is correct and the docstring is the stale party:

- `_cmd_quality_pass` (`engine.py:3953-3956`):
  ```python
  for title, reasons in title_hits:
      print(f"  - {title}")
      for r in reasons:
          print(f"      → {r}")
  ```
  `r` is printed directly as a reason line — if it were a
  `(substring, reason)` tuple the output would render the Python tuple
  repr, not a clean reason.
- `_cmd_new` / `_cmd_move` raise with the joined reasons as plain
  strings.

## Why it matters

This is internal-helper doc drift, not a behavioral bug — nothing
misbehaves today because every caller already treats the elements as
strings. But the docstring is a contract: a maintainer who trusts it
and writes `for substring, reason in _check_title_antipatterns(t):`
would crash with `ValueError: not enough values to unpack` (a 1-char
reason string unpacks into characters only if length 2, otherwise
raises). The likely history is that the helper once returned tuples and
was simplified to strings without updating the docstring. Correcting
the docstring removes the trap and restores the helper's contract to a
single source of truth.

## Fix

Replace the docstring's first line so it describes the real return
value:

```python
def _check_title_antipatterns(title: str) -> list[str]:
    """Return the list of antipattern reason strings matched by `title`; empty if clean."""
    return [reason for pat, reason in TITLE_ANTIPATTERNS if pat.search(title)]
```

No call sites change. A regression test pins that every returned
element is a `str`.
