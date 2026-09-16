---
title: deck-ships-a-card-whose-frontmatter-no-standard-yaml-reader-can-parse
summary: "FIXED: the latent hazard on `card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it` had landed — `pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries` carried a double-quoted summary with unescaped interior quotes, so PyYAML refused the whole block for 16 days while `goc validate`, `scripts/check_card_frontmatter_yaml.py` and CI all reported clean. The card is repaired by re-emitting it, `CardSummaryQuotingIsEmitterCanonicalTest` now pins every already-quoted summary against `emit_frontmatter` (703 scanned, 0 mismatches) so the next one turns the build red, and the suite docstring no longer asserts an unqualified whole-deck zero-false-negative calibration."
status: done
stage: null
contribution: medium
created: "2026-09-16T04:37:13Z"
closed_at: "2026-09-16T04:44:33Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, test, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — no already-double-quoted `summary:` in the deck differs from the line `emit_frontmatter` would write, and (when PyYAML is importable) no card's frontmatter block is refused by a strict parser while the repo-local guard reports it clean.
  - [x] MECHANICAL: `pattern-generalization-check-jsonl-per-line-loader-trusts-non-dict-entries` is repaired by re-emitting it through goc, so its interior quotes are emitter-escaped. Only its `summary:` quoting changes — the summary's text, the rest of its frontmatter, its body and its `log.md` stay as they are.
  - [x] TDD: a regression test in `tests/test_card_frontmatter_yaml.py` asserts the emitter-canonical invariant over the live deck, and demonstrates on a literal frontmatter block that it catches the offender's exact shape rather than only reporting a clean tree (`static-source-guards-never-prove-they-can-catch-an-offender`).
  - [x] MECHANICAL: the module docstring of `tests/test_card_frontmatter_yaml.py` no longer asserts an unqualified whole-deck "zero false positives, zero false negatives" calibration. It states when that calibration was taken, that it holds for plain scalars only, and names the card that owns the uncovered quoted-scalar class.
  - [x] MECHANICAL: `card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it` is amended in place — its body no longer calls the hazard latent — and carries a `log.md` entry recording the materialized instance. Its gate and its `## Decision required` section are left untouched.
  - [x] MECHANICAL: `uv run goc validate` clean, `uv run python scripts/check_card_frontmatter_yaml.py --check` clean, and `uv run python -m unittest discover -s tests` green.
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

Before the fix, `reproduce.py` failed both ways it can be run:

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

After the fix, both parts are clean and the script exits zero:

```
Part 1 — already-double-quoted summaries scanned: 703
Part 1 — quoted summaries the emitter would write differently: 0
Part 2 — cards scanned: 759
Part 2 — PyYAML refuses but the guard reports clean: 0

CLEAN: every quoted summary is in emitter-canonical form and PyYAML accepts every card
```

Under `uv run` (no PyYAML in the project environment) Part 2 skips itself and
Part 1 alone still decides the exit status, so the check is reachable from the
regression suite without taking the dependency
`drop-third-party-runtime-dependencies-from-goc` removed.

The repair changed exactly one line. Re-emitting the offender through
`emit_frontmatter` left every parsed frontmatter field, the summary's text and
the body byte-identical, and both parsers then agree on the value:

```
yaml_lite summary unchanged: True
all frontmatter fields unchanged: True
body unchanged: True
PyYAML accepts: True
PyYAML summary == yaml_lite summary: True
```

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

## What landed

Two mechanical halves, no decision between them — and deliberately nothing in
`scripts/check_card_frontmatter_yaml.py`.

1. **The instance is repaired.** `AGENTS.md` § "Card authoring rules" already
   prescribed it: "Re-emitting the card through any goc verb is the fix: the
   emitter consults the same set, so it quotes every shape the guard flags and
   preserves a quote you added by hand." Round-tripping the offender through
   `parse_frontmatter` / `emit_frontmatter` escaped the interior quotes; only the
   `summary:` line changed.

2. **The invariant is pinned** — `CardSummaryQuotingIsEmitterCanonicalTest` in
   `tests/test_card_frontmatter_yaml.py`. A frontmatter scalar that is *already*
   double-quoted on disk must be quoted exactly the way `emit_frontmatter` would
   quote it. The oracle is the engine's own emitter, so this adds no fourth quote
   scanner — the proliferation
   [`yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting`](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/)
   is filed to prevent — and needs no YAML dependency. Four tests: the live-deck
   invariant (703 quoted summaries, 0 mismatches), a sensitivity case driving the
   offender's exact shape as a literal block, a precision case on a correctly
   escaped summary, and a non-vacuity check that the walk saw real cards.
   Verified non-vacuous by reverting the repair: the live-deck test fails, and
   passes again once the repair is restored.

3. **The stale claim is corrected.** The module docstring of
   `tests/test_card_frontmatter_yaml.py` no longer states an unqualified
   whole-deck "zero false positives, zero false negatives". It dates the
   calibration, scopes it to plain scalars, records the 2026-09-16 false
   negative, and names the card that owns the uncovered quoted-scalar class.

The broader question — whether `scripts/check_card_frontmatter_yaml.py` itself
should stop skipping quoted values, and by which of three paths — stays parked on
[`card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it`](../card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it/),
whose body and `log.md` are amended with the materialized instance. Its gate,
its DoD and its `## Decision required` section are untouched. The net added here
is narrower than any of its three paths on purpose: cards only, the `summary`
field only, a regression test rather than the pre-commit guard.
