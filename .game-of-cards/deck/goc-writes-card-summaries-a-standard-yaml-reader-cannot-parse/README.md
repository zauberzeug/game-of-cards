---
title: goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse
summary: "goc's own frontmatter emitter leaves six plain-scalar shapes unquoted that strict YAML refuses — values opening with '!', '%', '- ', '? ', or a non-header '|'/'>' — plus any value holding a tab. The repo's committed pre-commit guard flags exactly those, so 'goc new --summary' can write a card that turns the guard red, and every full-frontmatter re-emit verb strips hand-added quotes back out, making the guard's own remedy ('emit_frontmatter already produces the correct form') an unbreakable loop."
status: done
stage: null
contribution: high
created: "2026-08-28T07:00:13Z"
closed_at: "2026-08-30T04:42:29Z"
human_gate: none
advances:
  - frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — all seven values emit as quoted scalars, and re-emitting a hand-quoted card no longer strips the quotes.
  - [x] TDD: a regression test asserts `emit_frontmatter` round-trips each of the seven shapes through `yaml_lite.safe_load` unchanged, so widening the quote trigger cannot break the parser side it was already correct for.
  - [x] TDD: a regression test asserts the emitter and the guard agree by construction — for every character in the shared indicator set, a value opening with it emits quoted AND the guard stays silent on that emitted line. It must fail if either side is edited alone.
  - [x] MECHANICAL: `scripts/check_card_frontmatter_yaml.py` imports the leading-indicator set from `goc.engine` rather than restating it (matching how it already imports `_YAML_BLOCK_HEADER_RE`), and flags the TAB case it currently misses.
  - [x] MECHANICAL: the two false remediation claims are corrected or made true — `scripts/check_card_frontmatter_yaml.py:181` and `AGENTS.md:494` both tell the reader `emit_frontmatter` already produces the correct form. Either the fix makes that true for every shape the guard flags, or the sentences say what is actually guaranteed.
  - [x] PROCESS: the finding that a parser-derived quote trigger would NOT fix these shapes is recorded on `frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`, so its pending decision is made against the right oracle.
  - [x] MECHANICAL: `uv run goc validate` clean, `uv run python -m unittest discover -s tests` green, `uv run python scripts/check_card_frontmatter_yaml.py --check` clean, and plugin mirrors synced.
worker: {who: "claude[bot]", where: main}
---

# goc writes card summaries a standard YAML reader cannot parse

## Location

Post-fix line numbers; the pre-fix values are in the code blocks below.

- `goc/engine.py:224` — `_YAML_INDICATORS`, the spec's `c-indicator` list, split
  into `_YAML_INDICATOR_FIRST` (:234) and `_YAML_SPACE_BOUND_INDICATORS` (:228)
- `goc/engine.py:214` — `_YAML_NEEDS_QUOTE`, now including TAB
- `goc/engine.py:264` — `_opens_with_yaml_indicator`, the leading-char predicate
- `goc/engine.py:358` — the `_yaml_inline` quote trigger that consults it
- `scripts/check_card_frontmatter_yaml.py:90` — the guard's engine import
- `scripts/check_card_frontmatter_yaml.py:108`/`:111` — `LEADING_INDICATORS` and
  `SPACE_BOUND_INDICATORS`, now derived from that import
- `scripts/check_card_frontmatter_yaml.py:148` — the new TAB finding
- `scripts/check_card_frontmatter_yaml.py:198` — the guard's remediation message
- `AGENTS.md:493` — the same claim, in the card-authoring rules
- `tests/test_emitter_strict_yaml_quoting.py` — the regression contract

## What was broken

Two sets described "which leading characters force a quote," and they disagreed.

The emitter's (`goc/engine.py:212`, pre-fix):

```python
# Leading indicator chars the vendored parser rejects in value position:
# `&`/`*` crash the parse (anchors/aliases not supported). `[`/`{`/`"`/`'`
# are already caught anywhere by _YAML_NEEDS_QUOTE.
_YAML_INDICATOR_FIRST = frozenset("&*")
```

Note the scoping in its own comment: **"chars the vendored parser rejects."**
The emitter's contract target is `goc/_vendor/yaml_lite.py`, not YAML.

The guard's (`scripts/check_card_frontmatter_yaml.py:93`, pre-fix):

```python
LEADING_INDICATORS = tuple("`@&*!|>'\"%[]{},#")
SPACE_BOUND_INDICATORS = ("-", "?", ":")
```

Subtracting what `_YAML_NEEDS_QUOTE` and `_YAML_BLOCK_HEADER_RE` already catch
anywhere leaves **six shapes the emitter writes bare and the guard rejects**:
a value opening with `!`, `%`, `- `, `? `, or a `|`/`>` that is not a complete
block header. A seventh — any value holding a TAB — is refused by strict YAML
and caught by *neither*.

So `goc new --summary '!important deck rewrite'` wrote:

```yaml
summary: !important deck rewrite
```

`goc validate` reported `OK`. The `card-frontmatter-yaml` pre-commit hook and
`tests/test_card_frontmatter_yaml.py` rejected it. PyYAML raises
`could not determine a constructor for the tag '!important'`.

### The documented remedy did not converge

The guard tells the operator what to do (`check_card_frontmatter_yaml.py:181`):

> Quote the value — `emit_frontmatter` already produces the correct form.

`AGENTS.md:494` repeats it, and its indicator list even names the two characters
the emitter omits:

> Quote any scalar holding `: ` or opening with a YAML indicator (`` ` ``, `@`,
> `&`, `*`, `!`, `%`, `#`, `,`); `emit_frontmatter` already produces the correct
> form, so re-emitting the card is the fix.

Both were false for these shapes. Hand-quoting worked — until any
full-frontmatter re-emit verb ran, at which point `_yaml_inline` stripped the
quotes back out. Verified against the CLI at filing time:

```
$ goc status probe-quoted active      # line-anchored mutation — quotes survive
summary: "!important deck rewrite"

$ goc advance probe-quoted --by probe-alpha   # full re-emit
summary: !important deck rewrite
```

Eight call sites re-emit whole frontmatter (`goc/engine.py` 4572, 4606, 6175,
6212, 6221, 6434, 6779, 7069) — `new`, `quality-pass`, `advance`, `unadvance`,
`wait`, `decide`, `migrate-list-style`. Any of them re-redded the hook on a card
the operator never edited, in a commit about something else.

Both sentences are true as of this closure, because the emitter now quotes
every shape the guard flags and re-emits the quoted form idempotently
(`reproduce.py` Part 2). The guard's message additionally names the two shared
sets so the next reader can check the claim instead of trusting it.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse/reproduce.py`
exits 0 after the fix; all seven values emit quoted, the guard has nothing left
to flag, and the vendored parser still reads every one back faithfully:

```
Part 1 — how emit_frontmatter renders seven strict-YAML-illegal values
  emitter quote-trigger : engine._YAML_INDICATOR_FIRST = '!"#%&\'*,>@[]`{|}'
  guard  quote-trigger  : guard.LEADING_INDICATORS    = '!"#%&\'*,>@[]`{|}'
                          guard.SPACE_BOUND_INDICATORS = ('-', ':', '?')

  [ ok  ] leading '!' — YAML reads it as a tag
         emitted: 'summary: "!important deck rewrite"'
         guard  : clean — quoted, so the guard has nothing left to flag
  ... (6 more ok) ...

Part 2 — the guard's remedy has to converge
    hand-quoted : 'summary: "!important deck rewrite"'   guard: clean
    after re-emit: 'summary: "!important deck rewrite"'  guard: clean

Part 3 — the vendored parser (what goc validate reads) accepts them all
  vendored parser round-trips all 7 -> faithful

Clean — emit_frontmatter quotes every strict-YAML-illegal plain scalar.
```

Before the fix the same script reported `DEFECT FIRES — 7/7 value(s) emitted as
a plain scalar strict YAML refuses` and the two trigger lines disagreed
(`engine._YAML_INDICATOR_FIRST = '&*'` against the guard's sixteen characters).

The deck was clean at filing (`739 cards scanned`) and is clean after
(`740 cards scanned`), so the fix is a no-op on every card on disk — it changes
only what future emits produce.

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
behaviour (one source of truth)". **That mechanism would not have fixed any of
these seven shapes** — `yaml_lite` round-trips all seven faithfully (Part 3),
so a trigger derived from it stays silent. The oracle has to be the union of
the vendored parser's coercions *and* strict-YAML legality. That finding is
recorded on the drift card, whose pending decision now covers only the parser
half of the union (see `## Fix (applied)` below).

The consumer-facing half was worse than the repo-local half: the guard is
repo-local and ships to nobody, so in a consuming repo all seven shapes were
written silently by `goc new`, passed `goc validate`, and failed the first time
anything outside goc read the deck — which
[`kickoff`](../../../goc/templates/skills/kickoff/SKILL.md) promises consumers is
"a plain Markdown file with YAML frontmatter". That half is where the fix
matters most: the emitter ships in the wheel and every plugin payload, so
consumers get it without the repo-local guard.

## Fix (applied)

The engine holds one spec-derived definition of "cannot open a YAML plain
scalar" and both sides read it:

1. `goc/engine.py` — `_YAML_INDICATORS` transcribes YAML 1.2 §5.3's closed
   `c-indicator` list, split into `_YAML_SPACE_BOUND_INDICATORS` (`-`, `?`, `:`,
   which bind only before a space/TAB or standing alone) and
   `_YAML_INDICATOR_FIRST` (the other sixteen, illegal at position 0 whatever
   follows). `_opens_with_yaml_indicator` applies the split, and `_yaml_inline`
   consults it instead of the old `frozenset("&*")`. TAB joined
   `_YAML_NEEDS_QUOTE`, since it is illegal *anywhere* in a plain scalar and a
   double-quoted scalar carries it through unchanged.
2. `scripts/check_card_frontmatter_yaml.py` imports both sets from `goc.engine`
   rather than restating them, and flags the TAB case it used to miss.

Step 2 is not a new coupling: the guard already imported `FRONTMATTER_RE` and
`_YAML_BLOCK_HEADER_RE` for exactly this reason — "recognized by reusing the
engine's own `_YAML_BLOCK_HEADER_RE` rather than restating it, so the two cannot
drift". This card is what happened where that precedent was not followed. The
guard's sixteen-character tuple turned out to already *be* the spec set minus
the space-bound three, so adopting it changed no guard verdict — only the
emitter moved.

The widening is strictly additive: it only ever adds quotes, `yaml_lite` reads
double-quoted scalars back unchanged (`reproduce.py` Part 3), and the live deck
was already guard-clean, so no card on disk re-emits differently. Precision is
pinned too — `-v is a flag`, `?query-shaped` and `-1000 is not a sequence`
are legal plain scalars and stay bare, so the widening cannot rewrite the
`summary` line of a card nobody edited.

### Why the union, not the parser, is the oracle

`_yaml_inline`'s trigger is now an explicit union of two oracles, and the
comment at `goc/engine.py:346` says so: two spec-derived clauses (a strict
reader must accept the output) plus three parser-derived ones
(`_parser_coerces_scalar`, `_YAML_BLOCK_HEADER_RE`, `s != s.strip()`). Either
alone leaves live defects — the seven shapes here round-trip through
`yaml_lite` faithfully, and conversely an integer-looking string is legal YAML
that comes back as an `int`. The `|`/`>` heads of `_YAML_BLOCK_HEADER_RE` are
now subsumed by the indicator set; the clause stays as the parser half of the
union so narrowing either side alone still leaves a bare block header quoted.

That finding is recorded on
[`frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`](../frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting/),
whose pending decision now covers only the parser half.

## Regression contract

`tests/test_emitter_strict_yaml_quoting.py`:

- each of the seven shapes emits quoted, and still round-trips through
  `yaml_lite.safe_load` with the field below it intact;
- a hand-quoted value survives re-emission (`emit(parse(emit(v))) == emit(v)`),
  so the guard's remedy converges;
- for every character in the shared set the emitter quotes AND the guard stays
  silent on the emitted line, and the bare form of each is still flagged — both
  directions, so narrowing either side alone turns the build red;
- the spec list is enumerated independently in the test, so shrinking
  `engine._YAML_INDICATORS` fails there instead of quietly shortening the loops.

Sensitivity checked by reverting the trigger to `frozenset("&*")` (21 failures)
and by restating the guard's tuple with `!` dropped (23 failures).
