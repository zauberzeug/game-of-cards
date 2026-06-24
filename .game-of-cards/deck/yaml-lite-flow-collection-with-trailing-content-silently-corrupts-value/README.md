---
title: yaml-lite-flow-collection-with-trailing-content-silently-corrupts-value
status: done
stage: null
contribution: medium
created: "2026-06-24T19:01:39Z"
closed_at: "2026-06-24T19:07:47Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
summary: "An inline flow collection followed by non-comment trailing content on the same line — e.g. `tags: [bug, api]# recategorize` (no space before the `#`, so it is not a YAML comment) — is silently corrupted instead of rejected. `_parse_flow_sequence` returns the whole raw line as a single phantom element; `_parse_flow_mapping` silently drops every key/value pair. The parser's documented posture is fail-loud on malformed structural input (over-indent, missing-space-after-colon, tabs, folded scalars all raise ParseError); these two flow helpers are the lone silent-corruption holdouts."
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (the malformed inputs now raise ParseError instead of returning corrupted values)
  - [x] TDD: a new test in tests/test_yaml_lite.py asserts `tags: [bug, api]# recategorize` raises ParseError, and `worker: {who: a}# note` raises ParseError, alongside an assertion that well-formed `[a, b]` / `{k: v}` still parse
  - [x] MECHANICAL: `_parse_flow_sequence` and `_parse_flow_mapping` raise ParseError on text that opens with `[`/`{` but does not close with the matching `]`/`}` (trailing non-comment content)
  - [x] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green
worker: {who: "claude[bot]", where: main}
---

# yaml-lite flow collection with trailing content silently corrupts the value

## Location

`goc/_vendor/yaml_lite.py:376-401` — `_parse_flow_sequence` (376-382)
and `_parse_flow_mapping` (385-401).

## What's broken

Both flow-collection parsers guard with a paired
`startswith(...) and endswith(...)` check and, when it fails, return a
**degenerate value instead of raising**:

```python
def _parse_flow_sequence(text: str) -> list:
    if not (text.startswith("[") and text.endswith("]")):
        return [text]                       # <-- silent: whole line becomes one phantom element
    ...

def _parse_flow_mapping(text: str) -> dict:
    if not (text.startswith("{") and text.endswith("}")):
        return {}                           # <-- silent: every pair dropped
    ...
```

The trigger is an inline flow collection immediately followed by `#`
with **no preceding space**, e.g. `tags: [bug, api]# recategorize`.
A YAML end-of-line comment requires a space before the `#`, so
`_strip_comment` (`yaml_lite.py:498`, guard `text[i - 1] in (" ", "\t")`)
correctly does *not* strip `]# recategorize`. The full string
`[bug, api]# recategorize` therefore reaches `_parse_scalar`, which
dispatches on the leading `[` to `_parse_flow_sequence`
(`yaml_lite.py:342`). There the `endswith("]")` half of the guard
fails (the string ends in the trailing junk, not `]`), so the function
silently returns `[text]`.

This contradicts the module's own stated and demonstrated posture.
The header docstring lists malformed structural input under
`Unsupported (raises ParseError)`, and the parser raises loudly on
every other "silent truncation" trap:

- over-indented mapping key — `yaml_lite.py:122` "Fail loud, matching
  the tab guard in `_peek`..."
- missing space after a colon — `yaml_lite.py:139` "Silently breaking
  would drop this line AND every key below it... Fail loud to match
  that posture."
- tabs as indentation — `yaml_lite.py:68`
- folded scalars — `yaml_lite.py:306`

The two flow helpers are the lone silent-corruption holdouts.

## Empirical evidence

`uv run python deck/<this-card>/reproduce.py` (against current HEAD):

```
tags   = ['[bug, api]# recategorize']    # expected: ParseError
worker = {}                              # expected: ParseError
```

A single phantom list element for the sequence case; total silent loss
of all pairs for the mapping case.

## Why it matters

Reachability: this is a *parser* defect, so the offending input must
be produced by something a reader will actually feed the parser. The
goc frontmatter emitter quotes any value containing `#`, so the
emitter's own round-trip output never triggers this — the reachable
path is **hand-edited input**: a `README.md` frontmatter block edited
by a human or one-shot-authored by an agent, plus the user-owned
`.game-of-cards/config.yaml` and the `canonical_tags:` YAML block in
`canonical-tags.md`, all of which go through `safe_load` /
`parse_frontmatter`.

When it fires, `goc validate` surfaces only the *downstream* symptom —
an unknown tag (`'[bug, api]# recategorize'` is not a canonical tag)
for the sequence case, or a "mapping must have a 'who' key" for the
worker case — and points the author at the wrong thing. The
parse-time corruption is silent, exactly the failure mode the
over-indent and missing-space guards were added to prevent.

Sibling history (all closed, all individually filed — not a meta-fix
family): [yaml-lite-truncates-flow-collection-with-hash-in-quoted-element](../yaml-lite-truncates-flow-collection-with-hash-in-quoted-element/)
(a `#` *inside* a quoted element),
[yaml-lite-flow-mapping-drops-pairs-without-a-space-after-the-colon](../yaml-lite-flow-mapping-drops-pairs-without-a-space-after-the-colon/),
[yaml-lite-flow-collection-mis-splits-on-backslash-escaped-quote](../yaml-lite-flow-collection-mis-splits-on-backslash-escaped-quote/).
Each fixed a distinct flow-collection parse bug; this is a fourth,
distinct one (trailing non-comment content after the close bracket),
not another instance of any one of them.

## Fix

In both helpers, split the paired guard so a leading bracket with no
matching trailing bracket raises `ParseError` (matching the fail-loud
posture) while preserving the defensive `not startswith` fallthrough:

```python
def _parse_flow_sequence(text: str) -> list:
    if not text.startswith("["):
        return [text]
    if not text.endswith("]"):
        raise ParseError(
            f"flow sequence {text!r} has trailing content after its "
            f"closing ']' (an end-of-line '#' comment must be preceded "
            f"by a space)"
        )
    ...

def _parse_flow_mapping(text: str) -> dict:
    if not text.startswith("{"):
        return {}
    if not text.endswith("}"):
        raise ParseError(
            f"flow mapping {text!r} has trailing content after its "
            f"closing '}}' (an end-of-line '#' comment must be preceded "
            f"by a space)"
        )
    ...
```

`_parse_scalar` only dispatches to these helpers when the text starts
with the respective bracket, so the `not startswith` branch is a
defensive fallthrough that never fires in practice; the live behavior
change is the new `endswith` raise.
