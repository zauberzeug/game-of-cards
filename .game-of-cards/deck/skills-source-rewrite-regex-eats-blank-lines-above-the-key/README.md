---
title: skills-source-rewrite-regex-eats-blank-lines-above-the-key
summary: "`_write_skills_source` rewrites the `skills_source:` key in config.yaml with a `re.MULTILINE` regex whose `[#\\s]*` char class matches newlines, so it back-consumes blank-line separators (and a preceding comment line's body) above the key. This contradicts the function's own docstring promise to preserve comments and ordering, and runs unconditionally on every `goc upgrade` / mode switch."
status: done
stage: null
contribution: medium
created: "2026-05-27T13:25:03Z"
closed_at: 2026-05-27T13:31:23Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (both cases preserve surrounding blank lines / comment bodies)
  - [x] TDD: a regression test asserts `_write_skills_source` leaves blank-line separators and a preceding comment line intact when rewriting the key
  - [x] MECHANICAL: the regex char class no longer matches `\n` (e.g. `[ \t]*` for leading whitespace, comment handled explicitly), and the docstring's "preserves comments and ordering" claim is true again
worker: {who: "claude[bot]", where: main}
---

# `_write_skills_source` regex eats blank-line separators above the key

## Location

`goc/install.py:1089` — the rewrite pattern inside `_write_skills_source`.

## What's broken

`_write_skills_source` sets the `skills_source:` key in
`.game-of-cards/config.yaml` by treating the file as line-oriented text.
Its docstring (`goc/install.py:1080-1081`) promises:

> Treats the config file as line-oriented text to avoid round-tripping
> the whole YAML — **preserves comments and ordering** that a
> parser-then-dump would lose.

But the rewrite pattern is:

```python
pattern = re.compile(r"^[#\s]*skills_source\s*:.*$", re.MULTILINE)
```

The leading char class `[#\s]*` includes `\s`, which matches `\n`. Under
`re.MULTILINE`, `^` can anchor at the start of a blank line, and `[#\s]*`
then greedily consumes the run of preceding blank-line `\n`s up to the
`skills_source` token. `pattern.sub(...)` replaces that entire span —
including the blank lines — with the single replacement line, destroying
the separators the docstring claims to preserve. When the line above is a
comment, the match can also swallow the comment line's body.

This runs unconditionally whenever the engine pins the mode: `goc install`
and `goc upgrade` both call `_write_skills_source` (e.g. the upgrade path
near `goc/install.py:1320`), so a routine upgrade silently re-flows a
consumer's hand-formatted config.

## Empirical evidence

`uv run python .game-of-cards/deck/skills-source-rewrite-regex-eats-blank-lines-above-the-key/reproduce.py`:

Before the fix, both cases destroyed the surrounding lines (case 1
collapsed `auto_commit: true\n\n\nskills_source: auto` to
`auto_commit: true\nskills_source: plugin`; case 2 ate the blank line
under the top comment). After the fix:

```
--- blank separators above an active skills_source key
  input    : 'auto_commit: true\n\n\nskills_source: auto\n'
  output   : 'auto_commit: true\n\n\nskills_source: plugin\n'
  expected : 'auto_commit: true\n\n\nskills_source: plugin\n'
  preserved: True

--- blank line above a commented skills_source key
  input    : '# top comment\n\n# skills_source: vendored\n'
  output   : '# top comment\n\nskills_source: plugin\n'
  expected : '# top comment\n\nskills_source: plugin\n'
  preserved: True

============================================================
PASS: blank lines / comments preserved (defect absent).
```

## Why it matters

`config.yaml` is a consumer-owned, hand-edited file (the docstring's whole
reason for not round-tripping through a YAML dumper is to keep the human's
formatting). The function instead mangles exactly that formatting on every
mode pin. The damage is silent — no error, no warning — so a maintainer who
groups config keys with blank-line stanzas loses the grouping on the next
`goc upgrade`, and a commented-out `# skills_source:` documentation line
above the key can be partially eaten. It is cosmetic rather than
data-destroying, hence `medium`, but it directly falsifies a documented
guarantee that other code/maintainers may rely on.

## Fix (applied)

Restricted the leading whitespace to horizontal whitespace so the match
cannot cross line boundaries, and handle the optional comment marker
explicitly (`goc/install.py:1089`):

```python
pattern = re.compile(r"^[ \t]*#?[ \t]*skills_source[ \t]*:.*$", re.MULTILINE)
```

`[ \t]*` matches indentation without newlines; the optional `#?` covers a
commented-out key on its own line. `^` still anchors per line under
`MULTILINE`, but the class can no longer reach back over blank lines.
A regression test
(`tests/test_install.py::test_write_skills_source_preserves_blank_separators_and_comments`)
asserts both cases above round-trip untouched.
