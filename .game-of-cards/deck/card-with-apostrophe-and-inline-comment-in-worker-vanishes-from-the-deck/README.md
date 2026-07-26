---
title: card-with-apostrophe-and-inline-comment-in-worker-vanishes-from-the-deck
summary: "yaml-lite's `_strip_comment` gates quote-mode entry on a node-start position only for bare quoted scalars, not for flow collections — so a bare apostrophe inside an unquoted flow element (`worker: {who: o'connor, ...}`) opens a quote run that never closes and suppresses trailing-comment detection. The unstripped ` # comment` then trips the flow-mapping trailing-content guard, so the whole card drops out of every deck view with a parse error that misleadingly blames a missing space."
status: active
stage: null
contribution: medium
created: "2026-07-26T10:00:51Z"
closed_at: null
human_gate: none
advances:
  - yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting
advanced_by: []
tags: [bug, api-contract, infra, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — `worker: {who: o'connor, where: main} # temp owner` parses to `{'who': "o'connor", 'where': 'main'}` and the card stays readable.
  - [ ] TDD: regression — the five behaviours the earlier sibling fixes established still hold (bare-scalar comment stripping, a `#` inside a balanced double-quoted scalar, a `#` and a `]` inside a quoted flow element, and a doubled `''` escape inside a single-quoted scalar).
  - [ ] MECHANICAL: `_strip_comment` enters quote-mode inside a flow collection only at a node-start position (start, after `,`/`:`/`[`/`{`), matching the gate `_split_flow` already carries; the node-start tuple is defined once instead of twice.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` green; `uv run goc validate` clean; `python scripts/sync_plugin_assets.py --check` green (vendored parser mirrored into the three plugin payloads).
worker: {who: "claude[bot]", where: main}
---

# card-with-apostrophe-and-inline-comment-in-worker-vanishes-from-the-deck

## Location

`goc/_vendor/yaml_lite.py:559` — the quote-entry arm of `_strip_comment`.

## What's broken

`_strip_comment` decides whether a `#` terminates a value. It tracks
quote state so a `#` *inside* a quoted scalar is not mistaken for a
comment, and bracket depth so a `#` inside a flow collection is left
alone. Its quote-entry arm is:

```python
    flow = text[:1] in ("[", "{")
    quoted = text[:1] in ('"', "'")
    ...
        elif (quoted or flow) and c in ('"', "'"):
            in_q = c
```

The `quoted` half is correctly conservative — quote-mode is only
considered for a value that *starts* with a quote. The `flow` half is
not: inside a flow collection **any** quote character opens a quoted
run, with no check that the quote actually begins an element. So the
apostrophe in `o'connor` opens a run that never closes, and from there
to end-of-line the comment scanner is blind.

The sibling scanner `_split_flow` (`yaml_lite.py:445`) learned exactly
this lesson and carries the gate:

```python
    prev = ""  # last significant (non-space) char processed outside quotes
    _node_start = ("", ",", ":", "[", "{")
    ...
        elif c in ('"', "'") and prev in _node_start:
            in_q = c
```

That gate landed with
[yaml-lite-flow-collection-mis-splits-on-bare-quote-in-unquoted-element](../yaml-lite-flow-collection-mis-splits-on-bare-quote-in-unquoted-element/),
whose body asserts the reverse of what is actually true:

> The sibling scanner `_strip_comment` (`yaml_lite.py:519-520`, `537`)
> already learned this exact lesson and carries an element-start guard

`_strip_comment` carries it for `quoted`, **not** for `flow`. So the
fix was applied to one scanner on the stated grounds that the other
already had it — and the other still does not. That is the same
"claimed present but wasn't" failure mode
[strip-comment-closes-double-quoted-scalar-on-backslash-escaped-quote](../strip-comment-closes-double-quoted-scalar-on-backslash-escaped-quote/)
documented one card earlier.

The user-visible consequence is worse than a truncated value. With the
comment unstripped, the value handed to `_parse_flow_mapping` is
`{who: o'connor, where: main} # temp owner`, which no longer ends in
`}` — so the trailing-content guard fires, and its message blames the
author for something they did not do:

```
an end-of-line '#' comment must be preceded by a space
```

The `#` *is* preceded by a space. `parse_frontmatter` wraps the
`ParseError` in a `FrontmatterError`, `load_card` downgrades that to a
`WARNING`, and the card is dropped from the deck.

## Empirical evidence

`uv run python .game-of-cards/deck/card-with-apostrophe-and-inline-comment-in-worker-vanishes-from-the-deck/reproduce.py`
before the fix:

```
control  (no comment):  worker={'who': "o'connor", 'where': 'main'}
defect   (+ comment):  ParseError: flow mapping "{who: o'connor, where: main} # temp owner" has trailing content after its closing '}' (an end-of-line '#' comment must be preceded by a space)
  [FAIL] a space-preceded ' #' comment must be stripped
card     parse:        FrontmatterError: YAML parse error inside frontmatter: flow mapping "{who: o'connor, where: main} # temp owner" has trailing content after its closing '}' (an end-of-line '#' comment must be preceded by a space)
  [FAIL] card is unreadable -> load_card warns and skips it, so it
         vanishes from the queue, the board, triage and validate
...
failures: 2
```

The same card in a scratch deck disappears from `goc --status all`
entirely, leaving only a warning line above the table:

```
WARNING: alpha-card: YAML parse error inside frontmatter: flow mapping "{who: o'connor, where: main} # temp owner" has trailing content after its closing '}' (an end-of-line '#' comment must be preceded by a space)
TITLE       STATUS  CONTR.  VALUE  GATE      TAGS  DOD
----------  ------  ------  -----  --------  ----  ---
gamma-card  open    medium    3.0  decision        0/1
beta-card   open    low       1.0  decision  bug   0/1
```

Note the control line: the *identical* `worker` value parses correctly
without the comment. Only the combination fails.

## Why it matters

The reachability path is hand-authored frontmatter, which is a
first-class input: `AGENTS.md` calls `worker` an "optional free-form
identifier naming who should or does work on a card" whose value is
"unregistered — use a person slug, a machine name, or a capability
tag", and the vendored parser's own docstring lists "`#` comments on
their own lines **or at end of lines**" as a supported feature. A
maintainer writing `worker: {who: o'brien, where: main} # until Friday`
is using two documented affordances together.

The emitter never produces this shape — `_YAML_NEEDS_QUOTE` includes
`'`, so `goc`-written values are quoted and the round-trip probe over
all 665 cards in this deck is clean. The defect only fires on
hand-authored input, which is precisely the input the parser exists to
tolerate, and it fires *silently*: a `WARNING` on stderr and a card
that is gone from the queue, the board, `triage`, and `validate`. A
schema-invalid card is loud; this one is invisible.

`yaml_lite` is mirrored byte-for-byte into all three plugin payloads
(`claude-plugin/goc/`, `codex-plugin/goc/`, `openclaw-plugin/goc/`), so
the fix ships to every host.

This is instance #7 of the family generalized by
[yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/),
which predicted it in as many words: *"Each scanner is one forgotten
arm away from the next silent round-trip-corruption bug."* This card
fixes the live arm; the generalization still owns the refactor that
would stop arm #8.

## Fix

In `_strip_comment` (`goc/_vendor/yaml_lite.py:528`), track `prev` — the
last significant character seen outside quotes — the way `_split_flow`
already does, and gate the *flow* quote-entry on it. Leave the `quoted`
half ungated: a bare quoted scalar opens its quote at index 0, where
`prev` is `""`, and re-opening after the closing quote is what keeps a
doubled `''` escape working.

```python
        elif c in ('"', "'") and (quoted or (flow and prev in _FLOW_NODE_START)):
            in_q = c
            prev = c
```

Hoist the node-start tuple to a module-level `_FLOW_NODE_START` so the
two scanners read it from one place instead of each spelling it out.
That is a shared *constant*, not the shared *stepping primitive* the
generalization card is gated on — it does not preempt that decision.

Bracket depth already prevents a `#` inside a flow collection from
being read as a comment, so the gate cannot resurrect the truncation
[yaml-lite-truncates-flow-collection-with-hash-in-quoted-element](../yaml-lite-truncates-flow-collection-with-hash-in-quoted-element/)
fixed; `reproduce.py` pins that case, the `]`-inside-a-quoted-element
case, and the doubled-`''` case as regressions.

### Out of scope

`_split_key` (`yaml_lite.py:505`) has the same ungated quote entry, so a
mapping key containing an apostrophe (`don't: value`) is rejected as
"not a valid 'key: value' mapping entry". It is not filed separately
because it has no reachable path in `goc`: frontmatter keys are
schema-fixed identifiers and block-sequence items are title slugs
matching `^[a-z0-9][a-z0-9-]*[a-z0-9]$`. It is recorded here as one
more arm for the generalization card's shared primitive to cover.
