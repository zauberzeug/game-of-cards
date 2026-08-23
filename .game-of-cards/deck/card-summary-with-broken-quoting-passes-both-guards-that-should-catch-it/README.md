---
title: card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it
summary: "The repo-local guard `scripts/check_card_frontmatter_yaml.py` skips every value that opens with a quote or a flow bracket, so a card whose quoting is itself malformed is invisible to it. Unescaping the interior quotes in a real card summary leaves `goc validate` OK and the guard reporting 'strict-YAML clean' while PyYAML raises ParserError — the exact divergence the guard was built to close. 105 live card summaries carry an emitter-escaped interior quote, so the hazard is one dropped backslash away."
status: open
stage: null
contribution: medium
created: "2026-08-23T04:36:20Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: human picks one of the three fix paths in `## Decision required`; the choice and its reason are recorded inline in this body. The pick is coupled to `yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting` — path B adds the fourth scanner that card is filed to prevent.
  - [ ] TDD: `reproduce.py` exits zero — every value form the guard currently skips that strict YAML refuses is now either flagged by the guard or refused by `goc validate`.
  - [ ] TDD: a regression test in `tests/test_card_frontmatter_yaml.py` drives all four divergent forms from `reproduce.py` Part 1 as literal frontmatter blocks and asserts the guard flags each one, so a detector that stops matching fails loudly instead of passing on a clean deck (`static-source-guards-never-prove-they-can-catch-an-offender`).
  - [ ] TDD: the guard stays silent on every legitimately-quoted shape the deck actually uses — the 105 escaped-interior-quote summaries, `tags: [a, b]` flow lists, `worker: {who: x, where: y}` flow maps, quoted values holding `: `, and quoted ISO timestamps. Zero false positives across the live deck.
  - [ ] MECHANICAL: the guard's module docstring no longer claims quoted-value legality is covered by `tests/test_skill_frontmatter_strict_yaml.py`. That test walks `SKILL.md` files only and never reads a card, so the sentence is false as written — replace it with whatever the chosen path actually guarantees.
  - [ ] MECHANICAL: `uv run goc validate` clean and `uv run python -m unittest discover -s tests` green. Guard remains runnable standalone and from the regression suite; if the chosen path keeps it dependency-free, no third-party import is added.
---

# A card summary with broken quoting passes both guards that should catch it

## Location

`scripts/check_card_frontmatter_yaml.py:116` — the early `continue` in
`flag_frontmatter`:

```python
key, value = line.split(":", 1)
value = value.strip()
if value.startswith(STRUCTURED_PREFIXES) or value in {"", "null"}:
    continue
```

with (`scripts/check_card_frontmatter_yaml.py:101`):

```python
#: Value forms that are already quoted or flow-structured — not plain scalars.
#: `|` / `>` are deliberately absent: they are legal only as a complete block
#: header, which `_YAML_BLOCK_HEADER_RE` recognizes separately.
STRUCTURED_PREFIXES = ('"', "'", "[", "{")
```

## What's broken

The guard is the net that closed
[`card-frontmatter-passes-goc-validate-while-strict-yaml-parsers-reject-it`](../card-frontmatter-passes-goc-validate-while-strict-yaml-parsers-reject-it/).
Its stated job, quoted from its own failure message:

> goc reads cards through its permissive vendored parser, so these load fine
> under `goc validate` and fail for everyone reading the deck with a strict YAML
> parser.

It catches that divergence only for **plain** scalars. Any value that *opens*
with a quote or a flow bracket is assumed well-formed and skipped whole. But
opening with a quote is not the same as being correctly quoted — and the
malformed-quoting case is exactly where the vendored parser and strict YAML part
company. Four of the six skipped forms are strict-YAML errors that both
`goc validate` and the guard wave through (`reproduce.py` Part 1).

The docstring justifies the skip like this
(`scripts/check_card_frontmatter_yaml.py:49`):

> A value that already opens with `"`, `'`, `[` or `{` is quoted or
> flow-structured and is left alone: its legality is a question about quoting,
> which `tests/test_skill_frontmatter_strict_yaml.py` covers on its own surface,
> and including it here would flag every correctly-quoted summary in the deck.

Both halves of that justification fail:

1. **The cited test does not cover cards.** Its own first line reads
   `"""Regression guard: shipped SKILL.md frontmatter must be strict-YAML safe."""`
   and it walks `SKILL_ROOTS` for `SKILL.md` files
   (`tests/test_skill_frontmatter_strict_yaml.py:62-65`). It never opens a
   `.game-of-cards/deck/*/README.md`. Card quoted-scalar legality is covered by
   nothing at all — the docstring points at a guard on a different surface and
   calls the seam closed.
2. **Checking legality does not mean flagging every quoted value.** Only
   *malformed* quoting has to be flagged. The 105 correctly-escaped summaries in
   the live deck stay silent under any well-formed-quoting predicate; the
   docstring treats "examine quoted values" and "flag quoted values" as the same
   act.

## Empirical evidence

`uv run python .game-of-cards/deck/card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it/reproduce.py`:

```
==============================================================================
Part 1 — the value forms the guard skips, by parser verdict
==============================================================================
value form                       strict YAML              yaml_lite  guard
------------------------------------------------------------------------------
double-quoted, interior quote    REFUSES (ParserError)    ACCEPTS    SILENT
double-quoted, unterminated      REFUSES (ScannerError)   ACCEPTS    SILENT
single-quoted, interior quote    REFUSES (ParserError)    ACCEPTS    SILENT
flow mapping, nested colon       REFUSES (ParserError)    ACCEPTS    SILENT
flow list, unterminated          REFUSES (ParserError)    REFUSES (ParseError) SILENT
flow mapping, unterminated       REFUSES (ParserError)    REFUSES (ParseError) SILENT

4 form(s) refused by strict YAML, accepted by the
vendored parser, and invisible to the guard:
  - double-quoted, interior quote
  - double-quoted, unterminated
  - single-quoted, interior quote
  - flow mapping, nested colon

==============================================================================
Part 2 — reachability on a real card in this deck
==============================================================================
card         : agents-md-architecture-section-cites-removed-click-and-omits-verbs
edit         : dropped the \ before each interior " in `summary`
summary now  : summary: "AGENTS.md's `## Code architecture` section is stale on two facts: it calls `goc/cli.py...
strict YAML  : REFUSES (ParserError)
yaml_lite    : ACCEPTS
repo guard   : SILENT (reports clean)

==============================================================================
Part 3 — how many cards are one dropped backslash away
==============================================================================
cards in deck                            : 732
summaries with an escaped interior quote : 105

FAIL: 4 strict-YAML-refusing value form(s) pass both `goc validate` and the guard.
```

The two unterminated-flow rows are *not* divergences — the vendored parser
refuses them too, so `goc validate` already stops them. They are listed to bound
the finding: the blind spot is four forms wide, not six.

`goc validate` on the Part 2 card, confirmed independently in a scratch deck:

```
OK  agents-md-claims-the-card-schema-is-inlined-into-the-skill-body
goc validate exit: 0
```

## Reachability — who writes a broken quoted summary

`emit_frontmatter` is not the culprit: `_yaml_inline`
(`goc/engine.py:314`) escapes `"` to `\"` before wrapping, so every
goc-*emitted* summary is well-formed. The exposed path is the hand-edit path —
which is the only path this guard exists to cover, since
`goc validate` already covers everything the emitter produces.

Two concrete routes:

1. **Retyping an escaped summary.** 105 of the deck's 732 summaries carry at
   least one `\"`. Editing such a summary in place — rewording it, or pasting the
   text from a rendered view where the backslashes are not visible — drops the
   escape. `reproduce.py` Part 2 performs exactly this edit on a live card: the
   result is a strict-YAML-refusing card that `goc validate` calls `OK` and the
   guard calls `strict-YAML clean`.
2. **Following the guard's own remedy.** The guard's failure message and
   AGENTS.md § Card authoring rules both instruct the author to *quote the
   value*: "Quote any scalar holding `: ` or opening with a YAML indicator". An
   author whose summary contains both a `: ` and an interior `"` obeys by
   wrapping the whole thing in `"..."` — and neither instruction mentions
   escaping the interior quote. The remedy prescribed for a flagged plain scalar
   produces a hazard the guard is blind to, so following the guidance moves the
   card from *detected* to *undetected* while leaving it broken.

Both routes end at a card that is green on `goc validate`, green on the
pre-commit hook, green in CI, and unreadable to any outside reader with a strict
parser — the same silent-drift failure the originating card was filed to stop.

## Why it matters

The originating card's argument was that the deck must stay readable by tools
other than goc, because `Skill(kickoff)` promises every consuming repo, verbatim,
that "each card is a plain Markdown file with YAML frontmatter". That promise is
made to readers who will use a real YAML parser. A guard that covers only plain
scalars honours the promise for the value form the emitter never breaks and
drops it for the form authors most often hand-edit.

The severity is bounded and honest: the live deck is clean today (`reproduce.py`
finds zero live offenders), the guard is repo-local and ships to no consumer, and
the vendored parser keeps goc itself working. What is broken is the *guarantee* —
the seam is reported closed and is not.

Related, no value-flow edge:

- [`yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting`](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/)
  — the meta-fix that path B below would work against. Coupled by decision, not
  by dependency.
- [`yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value`](../yaml-lite-strip-comment-defeated-by-unbalanced-quote-in-bare-value/)
  and
  [`strip-comment-closes-double-quoted-scalar-on-backslash-escaped-quote`](../strip-comment-closes-double-quoted-scalar-on-backslash-escaped-quote/)
  — unbalanced quotes inside the *vendored parser*. Same character, different
  surface: those fix what goc reads, this fixes what the repo-local guard sees.

## Decision required

All three paths close the blind spot. They differ in what they cost and what
they promise, and the originating card's dependency-free constraint is what makes
the cheapest one contentious.

**Path A — strict-parse the frontmatter block in the test, skip when PyYAML is
absent.** Add the real check to `tests/test_card_frontmatter_yaml.py` behind
`unittest.skipUnless(HAS_YAML)`; leave the standalone guard as-is for pre-commit.
One import, no new detector, exact fidelity — a strict parser *is* the oracle,
so there is no calibration to maintain and no shape can be missed.
- *Cost:* the guarantee weakens from "always enforced" to "enforced wherever
  PyYAML is installed". The originating card's DoD chose the opposite
  ("the guard needs no third-party import, so it runs in the dependency-free
  test environment CI uses"), so this path re-opens a settled constraint. Needs a
  check of whether CI's test env has PyYAML; if it does not, the check silently
  never runs and this becomes strictly worse than doing nothing.

**Path B — extend the detector with a well-formed-quoting predicate.** Keep it
dependency-free: verify a `"`-opened value terminates on an unescaped `"` at
end-of-value, likewise for `'` with `''` doubling, and that a flow collection
closes and holds no bare `: `.
- *Cost:* this is a fourth quote scanner in the repo, which is precisely what
  [`yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting`](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/)
  is filed to stop. It also inherits the calibration burden the guard's docstring
  already carries ("Detection is calibrated, not asserted") — a hand-rolled
  predicate must be re-proven against the deck on every change. Picking B should
  come with a decision on whether it shares a scanner with that card's fix or
  deliberately forks.

**Path C — narrow the guard's promise instead of widening the guard.** Change
nothing in the detector; correct the docstring and the failure message to say the
guard covers *plain scalars only*, and record quoted-value legality as an
accepted, documented gap.
- *Cost:* the divergence stays live and reachable by the two routes above. Buys
  honesty for free but fixes nothing, and leaves the kickoff promise unbacked for
  the value form authors edit most.

The `MECHANICAL` docstring item in the DoD is required under all three paths —
the false citation of `tests/test_skill_frontmatter_strict_yaml.py` is wrong
today regardless of which way the detector goes.
