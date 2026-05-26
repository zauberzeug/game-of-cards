---
title: append-marker-block-treats-briefing-text-as-regex-replacement-template
summary: "`_append_marker_block` (and two sibling sites) pass dynamic content as the *replacement* argument to `re.sub`, which parses it for backreferences (`\\1`, `\\g<name>`, `\\\\`). The GoC marker block / import block is the replacement, so any backslash-escape sequence a future AGENTS_GOC.md / CLAUDE_GOC.md edit introduces would be misinterpreted or raise `re.error` on install/upgrade. Latent today (templates contain no such sequences). UNVERIFIED — needs a reproduce.py. Fix: `pattern.sub(lambda _: block, text)`."
status: open
stage: null
contribution: low
created: "2026-05-26T20:56:28Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, unverified]
definition_of_done: |
  - [ ] TDD: reproduce.py — a marker/import block body containing a `\g<x>` or `\1` or trailing backslash round-trips through the merge unchanged (today it corrupts or raises `re.error`).
  - [ ] MECHANICAL: replace the dynamic-replacement `re.sub` calls in `goc/install.py` with a callable replacement (`lambda _: block`) or `re.sub` with a pre-escaped replacement, at ALL sibling sites: lines 222, 884, 1040.
  - [ ] TDD: existing install/upgrade behavior unchanged for the current (escape-free) templates; `tests/test_install.py` stays green.
  - [ ] PROCESS: drop the `unverified` tag once reproduce.py lands.
---

# `_append_marker_block` treats briefing text as an `re.sub` replacement template

## Location

- `goc/install.py:884` — `target.write_text(pattern.sub(block, text))`
- `goc/install.py:222` — `claude_md.write_text(CLAUDE_IMPORT_RE.sub(block, text))`
- `goc/install.py:1040` — `new_text = pattern.sub(replacement, text, count=1)`

## Hypothesis (UNVERIFIED)

`re.sub(pattern, repl, text)` parses `repl` for backreferences: `\1`,
`\g<name>`, and treats a lone trailing `\` or unknown `\x` escape as an
error. At `goc/install.py:884` the marker block — built from the
`AGENTS_GOC.md` / `CLAUDE_GOC.md` template body — is passed as `repl`:

```python
block = f"{GOC_BEGIN}\n{block_body.rstrip()}\n{GOC_END}\n"
...
target.write_text(pattern.sub(block, text))
```

If a future template edit ever puts a `\g`, `\1`, or backslash sequence
in the briefing (e.g. a regex example in the GoC guidance, or a Windows
path), `re.sub` would either silently substitute the wrong text or raise
`re.error` mid-install. The robust form makes the replacement opaque:

```python
target.write_text(pattern.sub(lambda _: block, text))
```

Same shape recurs at the two sibling sites above (lines 222 and 1040),
so the fix should cover all three (a small meta-fix family).

## Why latent / deferred

Verified by grep that the current templates contain no backslash-escape
sequences, so there is no live failure today — this is a robustness /
correctness-in-depth defect, not an active bug. Low contribution. No
reproduce.py budget this round.

## Falsification recipe

Call `_append_marker_block` (or the relevant `re.sub` site) with a
`block_body` containing `\g<oops>` and a target file that already has a
GoC marker block. Defect fires if the output is corrupted or `re.error`
is raised; expected: the literal `\g<oops>` survives verbatim.

Surfaced by the yaml/install defect hunter during an audit-deck round.
