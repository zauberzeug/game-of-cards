---
title: deck-ships-a-card-whose-frontmatter-no-standard-yaml-reader-can-parse
summary: "The latent hazard on `card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it` has landed: `pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries` carries a double-quoted summary with unescaped interior quotes, so PyYAML raises ParserError on it while `goc validate` and `scripts/check_card_frontmatter_yaml.py` both report clean. The suite docstring in `tests/test_card_frontmatter_yaml.py` still asserts a whole-deck calibration of zero false negatives, which is now false by measurement."
status: active
stage: null
contribution: medium
created: "2026-09-16T04:37:13Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, test, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — no already-double-quoted `summary:` in the deck differs from the line `emit_frontmatter` would write, and (when PyYAML is importable) no card's frontmatter block is refused by a strict parser while the repo-local guard reports it clean.
  - [ ] MECHANICAL: `pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries` is repaired by re-emitting it through goc, so its interior quotes are emitter-escaped. Only its `summary:` quoting changes — the summary's text, the rest of its frontmatter, its body and its `log.md` stay as they are.
  - [ ] TDD: a regression test in `tests/test_card_frontmatter_yaml.py` asserts the emitter-canonical invariant over the live deck, and demonstrates on a literal frontmatter block that it catches the offender's exact shape rather than only reporting a clean tree (`static-source-guards-never-prove-they-can-catch-an-offender`).
  - [ ] MECHANICAL: the module docstring of `tests/test_card_frontmatter_yaml.py` no longer asserts an unqualified whole-deck "zero false positives, zero false negatives" calibration. It states when that calibration was taken, that it holds for plain scalars only, and names the card that owns the uncovered quoted-scalar class.
  - [ ] MECHANICAL: `card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it` is amended in place — its body no longer calls the hazard latent — and carries a `log.md` entry recording the materialized instance. Its gate and its `## Decision required` section are left untouched.
  - [ ] MECHANICAL: `uv run goc validate` clean, `uv run python scripts/check_card_frontmatter_yaml.py --check` clean, and `uv run python -m unittest discover -s tests` green.
worker: {who: "claude[bot]", where: main}
---

# The deck ships a card no standard YAML reader can parse

## Location

- The offending card: `.game-of-cards/deck/pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries/README.md:3` (the `summary:` line).
- The guard that reports it clean: `scripts/check_card_frontmatter_yaml.py` — `STRUCTURED_PREFIXES` and the early `continue` in `flag_frontmatter`.
- The claim the deck now contradicts: `tests/test_card_frontmatter_yaml.py`, module docstring.

## What's broken

The offending summary is a **double-quoted** scalar that carries **unescaped
interior double quotes**:

```yaml
summary: "`goc/templates/hooks/pattern_generalization_check.py` reads ... a transcript whose last line is `"oops"` raises `AttributeError: 'str' object has no attribute 'get'` out of `_had_code_mutation`, against a contr
```

Inside a YAML double-quoted scalar a bare `"` *closes* the scalar, so a strict
reader ends the value at ``` `" ``` and then meets `oops"` where it expects the
next mapping key:

```
while parsing a block mapping
  in "<unicode string>", line 1, column 1:
    title: pattern-generalization-ch ...
    ^
expected <block end>, but found '<scalar>'
  in "<unicode string>", line 2, column 589:
     ... transcript whose last line is `"oops"` raises `AttributeError: ' ...
                                         ^
```

Every check this repo runs says the card is fine:

- `goc validate` is clean, because `validate_card` checks parsed field *values*,
  never the block's YAML legality.
- `goc/_vendor/yaml_lite.py` is permissive here — it returns the whole 855-char
  summary intact, so nothing in goc ever notices.
- `scripts/check_card_frontmatter_yaml.py --check` prints
  `Card frontmatter is strict-YAML clean (758 cards scanned)`, because it skips
  every value that *opens* with a quote.

Opening with a quote is not the same as being correctly quoted. That gap is
already filed and parked on a human decision —
[`card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it`](../card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it/).
**This card does not pre-empt that decision.** That card called the hazard
"one dropped backslash away" on 2026-08-23 and counted 105 summaries carrying an
emitter-escaped interior quote. The backslash dropped eight days later: the
offender was filed 2026-08-31, and the count is now 114.

The second half of the defect is that the repo states the opposite. The module
docstring of `tests/test_card_frontmatter_yaml.py`:

> The calibration that licenses that substitution lives in the card's
> `reproduce.py`, which runs the detector and PyYAML side by side across the
> whole deck: zero false positives, zero false negatives.

Measured today, side by side over the same deck: **zero false positives, one
false negative.** The calibration was a point-in-time measurement written as a
standing property, and nothing re-takes it — so the deck went red under strict
YAML and the sentence asserting it could not have kept reading true.

## Empirical evidence

`python3 .game-of-cards/deck/deck-ships-a-card-whose-frontmatter-no-standard-yaml-reader-can-parse/reproduce.py`:

```
Part 1 — already-double-quoted summaries scanned: 703
Part 1 — quoted summaries the emitter would write differently: 1
    pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries
Part 2 — cards scanned: 759
Part 2 — PyYAML refuses but the guard reports clean: 1
    pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries: while parsing a block mapping

DEFECT STANDS: the deck holds frontmatter no strict YAML reader accepts,
and every check this repo runs reports it clean.
```

Under `uv run` (no PyYAML in the project environment) Part 2 skips itself and
Part 1 alone still fails the run, so the check is reachable from the regression
suite without taking the dependency
`drop-third-party-runtime-dependencies-from-goc` removed.

## Why it matters

`goc/templates/skills/kickoff/SKILL.md` tells every new consuming repo, verbatim,
that each card is "a plain Markdown file with YAML frontmatter". A card that
PyYAML refuses outright is not that. The reachability path is the filing path
itself: cards are authored by writing `README.md` directly — `goc new` scaffolds
the frontmatter, then the agent edits the file — so any summary that quotes a
code fragment containing a `"` can land unescaped without passing through
`emit_frontmatter`, which is the only component that gets the escaping right.
That is how this one landed (commit `890ca028`, `new card: ...`).

Everything reading the deck from outside goc reads it with a real YAML parser:
the GitHub frontmatter renderer, a consumer's own tooling, an agent that reaches
for `yaml.safe_load`. For them this card is not a card with a slightly wrong
summary — the whole block fails to load.

## Fix

Two mechanical halves, no decision between them.

1. **Repair the instance.** `AGENTS.md` § "Card authoring rules" already
   prescribes it: "Re-emitting the card through any goc verb is the fix: the
   emitter consults the same set, so it quotes every shape the guard flags and
   preserves a quote you added by hand." Verified — round-tripping the offender
   through `emit_frontmatter` escapes the interior quotes and PyYAML then accepts
   the block. Only the `summary:` line changes.

2. **Pin the invariant that catches this class without a new scanner.** A
   frontmatter scalar that is *already* double-quoted on disk must be quoted
   exactly the way `emit_frontmatter` would quote it. The oracle is the engine's
   own emitter, so this adds no fourth quote scanner — the proliferation
   [`yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting`](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/)
   is filed to prevent — and it needs no YAML dependency. Measured on the live
   deck: 703 quoted summaries, exactly one mismatch, so the invariant holds at
   zero false positives the moment the offender is repaired.

The remaining, broader question — whether
`scripts/check_card_frontmatter_yaml.py` itself should stop skipping quoted
values, and by which of three paths — stays parked on
[`card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it`](../card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it/).
This card deliberately leaves `scripts/check_card_frontmatter_yaml.py`
unmodified.
