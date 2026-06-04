---
title: yaml-lite-folded-scalar-with-chomp-or-indent-indicator-misparses
summary: |-
  The vendored yaml-lite parser guards against the unsupported folded-scalar
  feature with an exact-string `rest == ">"` check, so only the bare `>`
  raises. Every folded variant carrying a chomping or explicit-indent
  indicator slips past, is returned as the literal header string, and
  silently drops every frontmatter field after it.
status: done
stage: null
contribution: medium
created: "2026-06-04T04:53:32Z"
closed_at: "2026-06-04T04:57:15Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — every folded-scalar variant (`>`, `>-`, `>+`, `>2`, `>2-`, `>2+`) raises ParseError, none silently misparse
  - [x] TDD: a regression test asserts `safe_load("summary: >-\n  x")` raises ParseError, not `{'summary': '>-'}`
  - [x] MECHANICAL: the `rest == ">"` exact-string guard is replaced by a folded-indicator regex mirroring `_BLOCK_INDICATOR_RE`
worker: {who: "claude[bot]", where: main}
---

# yaml-lite-folded-scalar-with-chomp-or-indent-indicator-misparses

The vendored yaml-lite parser is documented to *raise* on the unsupported
folded-scalar (`>`) feature — "never silently mis-parses." It only honors
that contract for the bare `>` indicator. Folded headers that carry a
chomping (`-`/`+`) or explicit-indent (`2`, `10`, …) indicator bypass the
guard, are returned as their literal header string, and cause every
subsequent frontmatter field to be silently dropped.

## Location

`goc/_vendor/yaml_lite.py:246-247`, in `_Parser._resolve_value`:

```python
if rest == ">":
    raise ParseError(f"line {self._pos + 1}: folded scalars (>) not supported")
```

## What's broken

The guard is an **exact-string** match on `">"`. It catches only the bare
indicator. The literal-block path directly above it already handles all
indicator variants via a regex (`yaml_lite.py:38`):

```python
# Literal block scalar header: `|`, with an optional explicit indentation
# indicator (`|2`) and an optional chomping indicator (`-` strip / `+` keep).
_BLOCK_INDICATOR_RE = re.compile(r"^\|(\d+)?([-+]?)$")
```

The folded path has no analogous regex. So `>-`, `>+`, `>2`, `>2-`, `>2+`,
`>10-` all fail the `rest == ">"` check, fall through past the
anchor/alias/empty branches, and reach `return _parse_scalar(rest)` at
line 266 — which returns the header string verbatim. The indented folded
body that follows is then left dangling at a deeper indent, terminating
the enclosing block mapping early, so all later fields vanish.

This directly violates the module's own documented contract
(`yaml_lite.py:16-21`):

```
Unsupported (raises ParseError):
  ...
  - Folded scalars (>)
```

and the closed card `replace-pyyaml-with-vendored-parser`'s DoD:
*"Unsupported YAML syntax (…folded `>` scalars) errors with
`<file>:<line>: <reason>` — never silently mis-parses."*

## Empirical evidence

```
$ uv run python .game-of-cards/deck/yaml-lite-folded-scalar-with-chomp-or-indent-indicator-misparses/reproduce.py
'>'    -> ParseError (correct): line 3: folded scalars (>) not supported
'>-'   -> {'title': 't', 'summary': '>-'}   [MISPARSE: status, tags dropped]
'>+'   -> {'title': 't', 'summary': '>+'}   [MISPARSE: status, tags dropped]
'>2'   -> {'title': 't', 'summary': '>2'}   [MISPARSE: status, tags dropped]
'>2-'  -> {'title': 't', 'summary': '>2-'}   [MISPARSE: status, tags dropped]
'>2+'  -> {'title': 't', 'summary': '>2+'}   [MISPARSE: status, tags dropped]
DEFECT CONFIRMED: 5 folded variant(s) misparsed instead of raising
```

## Why it matters

goc never *emits* folded scalars (the emitter only writes literal `|`
blocks for multi-line values), so this does not bite round-trips of
goc-authored cards. The reachability path is **hand-authored or
externally-generated frontmatter**: a contributor who writes a `summary:`
or `definition_of_done:` as a folded `>-` block — the most natural YAML
idiom for a wrapped one-paragraph string — gets their card silently
truncated rather than a clear "unsupported" error pointing at the line.
Every card loader (`goc validate`, `goc show`, the board renderer, the
session-start hook) routes through `safe_load`, so the corruption is
deck-wide and silent. The parser's whole reason for raising on
unsupported syntax is to make exactly this failure loud.

## Fix

Add a folded-indicator regex mirroring `_BLOCK_INDICATOR_RE` and match
against it instead of the bare string:

```python
_FOLDED_INDICATOR_RE = re.compile(r"^>(\d+)?([-+]?)$")
...
if _FOLDED_INDICATOR_RE.match(rest):
    raise ParseError(f"line {self._pos + 1}: folded scalars (>) not supported")
```

This routes every folded variant to the same documented ParseError the
bare `>` already raises.
