---
title: yaml-lite-double-quoted-decoder-silently-drops-backslash-on-unrecognized-escape
status: done
stage: null
contribution: medium
created: "2026-06-30T01:53:56Z"
closed_at: "2026-06-30T01:59:07Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
summary: "`_parse_double_quoted` in the vendored yaml-lite parser knows only four escapes (`\\n \\t \\\" \\\\`); for every other escape it keeps the escaped char but drops the backslash via a `.get(esc, esc)` fallback, silently corrupting the value (`\"C:\\Users\"` → `C:Users`, `\"caf\\u00e9\"` → `cafu00e9`). This is the lone silent-corruption holdout in the decoder — every other malformed/unsupported double-quoted input fails loud with ParseError. Fix: raise ParseError on unrecognized escapes, matching the parser's documented posture."
definition_of_done: |
  - [x] TDD: reproduce.py exits non-zero after the fix — the three unrecognized-escape scalars (`"C:\Users"`, `"a\rb"`, `"café"`) raise ParseError instead of returning a backslash-dropped value, while the four recognized escapes (`\n \t \" \\`) still decode unchanged.
  - [x] TDD: a regression guard in tests/test_yaml_lite.py asserts an unrecognized escape inside a double-quoted scalar raises ParseError, alongside an assertion that `"a\nb"`, `"it\"s"`, and `"a\\b"` still parse correctly.
  - [x] MECHANICAL: `_parse_double_quoted` raises ParseError on any escape outside `{n, t, ", \}` instead of dropping the backslash, mirroring the fail-loud posture of `_parse_flow_sequence`/`_parse_flow_mapping`.
  - [x] PROCESS: `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green (the vendored parser is mirrored into the plugin payloads).
worker: {who: "claude[bot]", where: main}
---

# yaml-lite-double-quoted-decoder-silently-drops-backslash-on-unrecognized-escape

## Summary

The vendored YAML parser's double-quoted-scalar decoder recognizes only
four escape sequences. For any other escape it silently discards the
backslash and keeps the following character, turning a hand-authored
double-quoted value into a corrupted one with no error. This is the
last silent-corruption holdout in the parser; every other unsupported
or malformed double-quoted input already raises `ParseError`.

## Location

`goc/_vendor/yaml_lite.py`, `_parse_double_quoted` — the escape-decode line:

```python
if inner[i] == "\\" and i + 1 < len(inner):
    esc = inner[i + 1]
    out.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc))
    i += 2
```

## What's broken

The `.get(esc, esc)` fallback returns the *escaped character alone*
whenever `esc` is not one of the four known keys — the backslash is
thrown away. So:

| Input (double-quoted scalar) | Parsed value | Expected |
|---|---|---|
| `"C:\Users"` | `C:Users` | a Windows path, or a loud error |
| `"a\rb"` | `arb` | `a\rb` decoded, or a loud error |
| `"café"` | `cafu00e9` | `café` decoded, or a loud error |

The corruption is silent — no `ParseError`, no warning — which is
exactly the failure mode the rest of this parser was hardened against.
The sibling card
[yaml-lite-flow-collection-with-trailing-content-silently-corrupts-value](../yaml-lite-flow-collection-with-trailing-content-silently-corrupts-value/)
states the parser's posture explicitly: *"fail-loud on malformed
structural input (over-indent, missing-space-after-colon, tabs, folded
scalars all raise ParseError); these two flow helpers are the lone
silent-corruption holdouts."* That card closed the flow-helper
holdouts; `_parse_double_quoted` is the remaining one in the escape
decoder.

## Empirical evidence

`reproduce.py` output on the unfixed parser:

```
=== yaml-lite double-quoted unrecognized-escape decode ===
  '"C:\\Users"'      -> 'C:Users'   (silently corrupted: backslash dropped)
  '"a\\rb"'          -> 'arb'   (silently corrupted: backslash dropped)
  '"caf\\u00e9"'     -> 'cafu00e9'   (silently corrupted: backslash dropped)

DEFECT PRESENT: 3 unrecognized-escape scalar(s) silently corrupted (backslash dropped, no error).
```

## Why it matters — reachability

The emitter side is safe: `emit_frontmatter` doubles backslashes
(`\` → `\\`) and only ever produces the four recognized escapes, so
machine-written frontmatter round-trips cleanly and never triggers the
fallback. The defect bites the **hand-edit path** the project
explicitly supports — an author writing a double-quoted `summary:` or
`worker:` value that contains a backslash sequence the decoder doesn't
know (a Windows path `"C:\Users\..."`, a literal `\r`, a `\u` escape).
The value is then read back corrupted with no signal that anything was
lost, and the corrupted string is what subsequent `goc` reads,
validations, and re-emits operate on.

## Fix

Raise `ParseError` on any escape outside the recognized set, matching
the fail-loud posture of `_parse_flow_sequence` / `_parse_flow_mapping`
and the closed flow-collection holdout card. Concretely, replace the
silent `.get(esc, esc)` fallback so an unknown `esc` raises with a
message naming the offending sequence, while `\n \t \" \\` continue to
decode as before. This keeps the "lite" parser honest: it decodes the
escapes it supports and rejects (loudly) the ones it does not, rather
than mangling them.

(Decoding the full YAML double-quote escape table — `\r \0 \xNN \uNNNN`
… — is a *feature expansion* beyond the lite subset and a separate
decision; this card only closes the silent-corruption hole, consistent
with how the flow-helper holdout was closed.)

## Relationship to the scanner meta-fix

The meta-card
[yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/)
covers the three *position scanners* (`_split_flow`, `_split_key`,
`_strip_comment`) that hand-roll quote/escape/depth bookkeeping.
`_parse_double_quoted` is a *decoder*, not a position scanner — it does
no depth/split tracking — so it is out of that meta-fix's scope and is
fixed here as a standalone correctness defect rather than as an Nth
instance of the scanner family.
