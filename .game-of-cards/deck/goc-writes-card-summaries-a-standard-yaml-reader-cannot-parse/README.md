---
title: goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse
summary: "goc's own frontmatter emitter leaves six plain-scalar shapes unquoted that strict YAML refuses — values opening with '!', '%', '- ', '? ', or a non-header '|'/'>' — plus any value holding a tab. The repo's committed pre-commit guard flags exactly those, so 'goc new --summary' can write a card that turns the guard red, and every full-frontmatter re-emit verb strips hand-added quotes back out, making the guard's own remedy ('emit_frontmatter already produces the correct form') an unbreakable loop."
status: active
stage: null
contribution: high
created: "2026-08-28T07:00:13Z"
closed_at: null
human_gate: none
advances:
  - frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — all seven values emit as quoted scalars, and re-emitting a hand-quoted card no longer strips the quotes.
  - [ ] TDD: a regression test asserts `emit_frontmatter` round-trips each of the seven shapes through `yaml_lite.safe_load` unchanged, so widening the quote trigger cannot break the parser side it was already correct for.
  - [ ] TDD: a regression test asserts the emitter and the guard agree by construction — for every character in the shared indicator set, a value opening with it emits quoted AND the guard stays silent on that emitted line. It must fail if either side is edited alone.
  - [ ] MECHANICAL: `scripts/check_card_frontmatter_yaml.py` imports the leading-indicator set from `goc.engine` rather than restating it (matching how it already imports `_YAML_BLOCK_HEADER_RE`), and flags the TAB case it currently misses.
  - [ ] MECHANICAL: the two false remediation claims are corrected or made true — `scripts/check_card_frontmatter_yaml.py:181` and `AGENTS.md:494` both tell the reader `emit_frontmatter` already produces the correct form. Either the fix makes that true for every shape the guard flags, or the sentences say what is actually guaranteed.
  - [ ] PROCESS: the finding that a parser-derived quote trigger would NOT fix these shapes is recorded on `frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`, so its pending decision is made against the right oracle.
  - [ ] MECHANICAL: `uv run goc validate` clean, `uv run python -m unittest discover -s tests` green, `uv run python scripts/check_card_frontmatter_yaml.py --check` clean, and plugin mirrors synced.
worker: {who: "claude[bot]", where: main}
---

# goc writes card summaries a standard YAML reader cannot parse

## Location

- `goc/engine.py:212` — `_YAML_INDICATOR_FIRST`, the emitter's leading-indicator
  quote trigger
- `goc/engine.py:262` — `_yaml_inline`, which consults it
- `scripts/check_card_frontmatter_yaml.py:93` — `LEADING_INDICATORS`, the
  committed guard's leading-indicator set
- `scripts/check_card_frontmatter_yaml.py:96` — `SPACE_BOUND_INDICATORS`
- `scripts/check_card_frontmatter_yaml.py:181` — the guard's remediation message
- `AGENTS.md:494` — the same claim, in the card-authoring rules

## What's broken

Two sets describe "which leading characters force a quote," and they disagree.

The emitter's (`goc/engine.py:212`):

```python
# Leading indicator chars the vendored parser rejects in value position:
# `&`/`*` crash the parse (anchors/aliases not supported). `[`/`{`/`"`/`'`
# are already caught anywhere by _YAML_NEEDS_QUOTE.
_YAML_INDICATOR_FIRST = frozenset("&*")
```

Note the scoping in its own comment: **"chars the vendored parser rejects."**
The emitter's contract target is `goc/_vendor/yaml_lite.py`, not YAML.

The guard's (`scripts/check_card_frontmatter_yaml.py:93`):

```python
LEADING_INDICATORS = tuple("`@&*!|>'\"%[]{},#")
SPACE_BOUND_INDICATORS = ("-", "?", ":")
```

Subtracting what `_YAML_NEEDS_QUOTE` and `_YAML_BLOCK_HEADER_RE` already catch
anywhere leaves **six shapes the emitter writes bare and the guard rejects**:
a value opening with `!`, `%`, `- `, `? `, or a `|`/`>` that is not a complete
block header. A seventh — any value holding a TAB — is refused by strict YAML
and caught by *neither*.

So `goc new --summary '!important deck rewrite'` writes:

```yaml
summary: !important deck rewrite
```

`goc validate` reports `OK`. The `card-frontmatter-yaml` pre-commit hook and
`tests/test_card_frontmatter_yaml.py` reject it. PyYAML raises
`could not determine a constructor for the tag '!important'`.

### The documented remedy does not converge

The guard tells the operator what to do (`check_card_frontmatter_yaml.py:181`):

> Quote the value — `emit_frontmatter` already produces the correct form.

`AGENTS.md:494` repeats it, and its indicator list even names the two characters
the emitter omits:

> Quote any scalar holding `: ` or opening with a YAML indicator (`` ` ``, `@`,
> `&`, `*`, `!`, `%`, `#`, `,`); `emit_frontmatter` already produces the correct
> form, so re-emitting the card is the fix.

Both are false for these shapes. Hand-quoting works — until any
full-frontmatter re-emit verb runs, at which point `_yaml_inline` strips the
quotes back out. Verified against the CLI:

```
$ goc status probe-quoted active      # line-anchored mutation — quotes survive
summary: "!important deck rewrite"

$ goc advance probe-quoted --by probe-alpha   # full re-emit
summary: !important deck rewrite
```

Eight call sites re-emit whole frontmatter (`goc/engine.py` 4572, 4606, 6175,
6212, 6221, 6434, 6779, 7069) — `new`, `quality-pass`, `advance`, `unadvance`,
`wait`, `decide`, `migrate-list-style`. Any of them re-reds the hook on a card
the operator never edited, in a commit about something else.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse/reproduce.py`

```
Part 1 — emit_frontmatter renders these as plain (illegal) scalars
  emitter quote-trigger : engine._YAML_INDICATOR_FIRST = '&*'
  guard  quote-trigger  : guard.LEADING_INDICATORS    = '`@&*!|>\'"%[]{},#'
                          guard.SPACE_BOUND_INDICATORS = ('-', '?', ':')

  [FAIL ] leading '!' — YAML reads it as a tag
         emitted: 'summary: !important deck rewrite'
         guard  : FLAGGED — emitter wrote what the commit hook rejects
  ... (5 more FLAGGED) ...
  [FAIL ] interior TAB — illegal in a YAML plain scalar
         emitted: 'summary: column\tseparated'
         guard  : not flagged — guard blind spot, ships silently

Part 2 — the guard's own remedy is a loop
    hand-quoted : 'summary: "!important deck rewrite"'
    guard       : clean
    after re-emit: 'summary: !important deck rewrite'
    guard       : FLAGGED again
    [FAIL] the emitter strips the quotes the guard demanded

Part 3 — the vendored parser (what goc validate reads) accepts them all
  vendored parser round-trips '!important deck rewrite'  -> faithful   (×7)

Part 4 — strict-YAML cross-check
  strict YAML REFUSES '!important deck rewrite' -> could not determine a constructor for the tag '!important'
  strict YAML REFUSES '%-based progress metric' -> while scanning for the next token
  strict YAML REFUSES '- listed as a sub-item'  -> sequence entries are not allowed here
  strict YAML REFUSES '? unclear which verb wrote it' -> mapping keys are not allowed here
  strict YAML REFUSES '|pipe-delimited output'  -> while scanning a block scalar
  strict YAML REFUSES '>greater-than in a diff' -> while scanning a block scalar
  strict YAML REFUSES 'column\tseparated'       -> while scanning for the next token

DEFECT FIRES — 7/7 value(s) emitted as a plain scalar strict YAML refuses.
               Re-emitting a hand-quoted card strips the quotes back out,
               so the guard's documented remedy never converges.
```

The deck is currently clean (`739 cards scanned`), so the fix is a no-op on
every card on disk — it changes only what future emits produce.

## Reachability

The offending input is a **first-party CLI argument**, not hand-edited YAML:
`goc new <title> --summary '<text>'` puts the string into `fm["summary"]`
verbatim, and `_cmd_new` writes it through `emit_frontmatter`
(`goc/engine.py:6175`). `goc wait --reason` reaches `waiting_on` the same way
(`goc/engine.py:6434`). Prose starting with `%` ("%-based progress metric") or
`- ` (a summary that opens with a list item) is ordinary English, and `>` opens
any pasted diff or quote fragment. No malformed input is required — the
character just has to land first.

## Why it matters

`goc validate` gates CI and the shipped pre-commit hook here, so the blast
radius is the *next* commit by *any* author, with nothing in the output naming
the verb that did it — the same shape catalogued by
[`goc-verbs-emit-frontmatter-their-own-validator-rejects`](../goc-verbs-emit-frontmatter-their-own-validator-rejects/),
one oracle over. That epic's invariant is *writer accept-set == `validate_card`
accept-set*; this card's is *emitter output == legal YAML*, which
`validate_card` never checks by design.

More consequentially, this is counter-evidence for the open decision on
[`frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`](../frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting/).
That card proposes deriving the emitter's quote decision "from parser
behaviour (one source of truth)". **That mechanism would not fix any of these
seven shapes** — `yaml_lite` round-trips all seven faithfully (Part 3), so a
trigger derived from it stays silent. The oracle has to be the union of the
vendored parser's coercions *and* strict-YAML legality. That is new information
for a decision nobody has made yet, which is why this is filed rather than
patched.

The consumer-facing half is worse than the repo-local half: the guard is
repo-local and ships to nobody, so in a consuming repo all seven shapes are
written silently by `goc new`, pass `goc validate`, and fail the first time
anything outside goc reads the deck — which
[`kickoff`](../../../goc/templates/skills/kickoff/SKILL.md) promises consumers is
"a plain Markdown file with YAML frontmatter".

## Fix

Give the engine one exported set of characters that cannot open a YAML plain
scalar, derived from the YAML spec's closed indicator list rather than from
observed bug reports, and have both sides read it:

1. `goc/engine.py:212` — replace `_YAML_INDICATOR_FIRST = frozenset("&*")` with
   the spec set, and add the space-bound cases (`- `, `? `) and the
   non-header `|`/`>` case to `_yaml_inline`'s trigger
   (`goc/engine.py:307-311`). Add a TAB check to `_YAML_NEEDS_QUOTE`
   (`goc/engine.py:208`) — TAB is illegal anywhere in a plain scalar, not just
   at the head.
2. `scripts/check_card_frontmatter_yaml.py:93` — import that set from
   `goc.engine` instead of restating it, and extend the guard to the TAB case.

Step 2 is not a new coupling: the guard already imports `FRONTMATTER_RE` and
`_YAML_BLOCK_HEADER_RE` from `goc.engine` (`check_card_frontmatter_yaml.py:84`)
for exactly this reason — "recognized by reusing the engine's own
`_YAML_BLOCK_HEADER_RE` rather than restating it, so the two cannot drift"
(`check_card_frontmatter_yaml.py:55`). This card is what happens where that
precedent was not followed. Widening the emitter is strictly safe: it only ever
adds quotes, `yaml_lite` reads double-quoted scalars back unchanged, and the
live deck is already guard-clean, so no card on disk re-emits differently.
