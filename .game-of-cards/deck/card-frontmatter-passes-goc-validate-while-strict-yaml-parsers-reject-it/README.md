---
title: card-frontmatter-passes-goc-validate-while-strict-yaml-parsers-reject-it
summary: "Two cards in this repo's deck carry frontmatter that `goc validate` reports OK but no strict YAML parser can read — an unquoted `summary` holding a nested `: `, and one opening with a backtick, which YAML reserves. The vendored `yaml_lite` parser is deliberately a permissive superset of what `emit_frontmatter` produces, and hand-authored frontmatter — the documented filing path — has no guard, so the deck silently drifts from the YAML format goc's own kickoff briefing promises consumers. The identical defect on `SKILL.md` frontmatter was closed with a repo-local test guard; the card surface still has none."
status: done
stage: null
contribution: medium
created: "2026-08-16T04:50:03Z"
closed_at: "2026-08-16T05:01:23Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — the dependency-free detector flags no card in the deck.
  - [x] MECHANICAL: both offending cards carry a quoted `summary` that a strict YAML parser accepts, with the summary text itself unchanged.
  - [x] TDD: a repo-local guard flags BOTH historical offenders from their exact on-disk summary lines, so a guard that stopped matching fails rather than passing quietly on a clean deck (`static-source-guards-never-prove-they-can-catch-an-offender`).
  - [x] TDD: the guard stays quiet on the legitimate frontmatter shapes the deck actually uses — block scalars, block sequences, `tags: [a, b]` flow lists, `worker: {who: x}` flow maps, quoted values holding `: `, `null`, and ISO timestamps.
  - [x] TDD: a "guard the guard" assertion fails if the scan covers no cards, so moving or renaming the deck cannot turn the clean verdict vacuous.
  - [x] MECHANICAL: the guard needs no third-party import, so it runs in the dependency-free test environment CI uses (`drop-third-party-runtime-dependencies-from-goc`).
  - [x] MECHANICAL: the guard runs at filing time, not only on push — a card whose frontmatter strict YAML rejects fails before it lands.
worker: {who: "claude[bot]", where: main}
---

# Card frontmatter passes goc validate while strict YAML parsers reject it

`goc validate` reports `OK` for every card in this repo's deck. Two of
those cards are not valid YAML, and no mechanism owns the gap.

## Location

- `.game-of-cards/deck/closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded/README.md:3`
- `.game-of-cards/deck/repair-edges-help-and-docstrings-omit-supersession-half-edges-from-scope/README.md:3`
- `goc/_vendor/yaml_lite.py` — the permissive parser every goc surface reads through
- `goc/engine.py:1788` — `validate_card`, which checks field *values*, never the block's YAML legality
- `tests/test_skill_frontmatter_strict_yaml.py` — the guard that already exists for the sibling surface

## What's broken

Both offenders are an unquoted `summary` scalar. The first holds a nested
`: `:

```yaml
summary: When `workflow.closure_on_integration: true`, `goc done` refuses to close unless HEAD is reachable from origin/main, but ...
```

A plain scalar may not contain `: ` — YAML reads it as a nested mapping key
and refuses: `mapping values are not allowed here`. The second opens with a
backtick:

```yaml
summary: `goc repair-edges --help` and the verb's docstrings claim the verb only handles `advances/advanced_by` half-edges, but ...
```

`` ` `` and `@` are **reserved indicators** in YAML — a plain scalar may not
start with either, at all: `found character '`' that cannot start any token`.

`yaml_lite` accepts both because it splits a mapping line on the *first*
colon and treats the remainder as opaque text. That permissiveness is
deliberate and documented — the card that introduced it
([`replace-pyyaml-with-vendored-parser`](../replace-pyyaml-with-vendored-parser/))
scoped the parser as "a superset of what `emit_frontmatter` produces". The
gap is that the deck's frontmatter is not only emitter-produced.

Nothing in the pipeline contradicts this. `validate_card` validates parsed
*values* — enum membership, edge symmetry, date shape — and never asks whether
the block it was handed is legal YAML. So the two cards are `OK`:

```
$ uv run goc validate
...
OK  closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded
OK  repair-edges-help-and-docstrings-omit-supersession-half-edges-from-scope
$ echo $?
0
```

What this contradicts is the promise goc makes to every repo it is installed
into. `goc/templates/skills/kickoff/SKILL.md:78` has the agent deliver, in
the skill's words, "verbatim (no edits, no summarising)":

> each card is a plain
> Markdown file with YAML frontmatter

Two cards in goc's own deck are not that file.

## Empirical evidence

`python3 .game-of-cards/deck/<this-card>/reproduce.py` against the deck as it
stood when this card was filed, verbatim:

```
cards with frontmatter scanned: 721

[1] goc's vendored yaml_lite parses: 721/721

[2] strict YAML (PyYAML 6.0.1) refuses: 2
      REFUSED closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded
              mapping values are not allowed here
      REFUSED repair-edges-help-and-docstrings-omit-supersession-half-edges-from-scope
              while scanning for the next token

[3] scripts/check_card_frontmatter_yaml.py flags: 2
      FLAGGED closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded
              line 2: summary: plain scalar contains an unquoted ': '
      FLAGGED repair-edges-help-and-docstrings-omit-supersession-half-edges-from-scope
              line 2: summary: plain scalar opens with YAML indicator '`'

      false positives (flagged, strict YAML fine): []
      false negatives (strict YAML refuses, unflagged): []

VERDICT: DEFECT PRESENT — 2 card(s) pass `goc validate` while carrying frontmatter no strict YAML parser can read.
```

The false-positive and false-negative lines are the load-bearing result: across
721 cards the guard and the strict parser agree card-for-card, which is what
lets a dependency-free guard reproduce a YAML verdict without importing a YAML
library. Section 3 loads
`scripts/check_card_frontmatter_yaml.py` itself rather than restating its rules,
so the calibration measures the guard that actually runs in CI and pre-commit.

On the current tree — both summaries quoted — the same run reports `0` in
sections 2 and 3 and exits `0`. The catch-an-offender direction is pinned
instead by `tests/test_card_frontmatter_yaml.py`, which replays both `summary`
lines byte-for-byte as they sat on disk; a clean deck cannot make that pass
vacuously.

## Reachability — who writes an unquoted summary

Not the emitter. `emit_frontmatter` quotes both shapes correctly, confirmed
by driving `goc new` directly:

```
$ goc new emit-probe-colon --summary 'When `workflow.closure_on_integration: true`, it refuses.'
summary: "When \`workflow.closure_on_integration: true\`, it refuses."
$ goc new emit-probe-backtick --summary '`goc repair-edges --help` claims otherwise.'
summary: "`goc repair-edges --help` claims otherwise."
```

The path is **hand-authored frontmatter**, which is the documented primary
path, not a corner case. `goc new` itself ends with

> Next: edit `.game-of-cards/deck/<title>/README.md` to fill the body and DoD

and `Skill(create-card)` Step 5 has the agent write the body and rewrite the
DoD in place. Once an agent is editing that file with a text editor, the
`summary` line is one more line of prose, and neither offender's `git log`
shows a goc verb as the author: one arrived in a bulk hygiene pass
(`chore(deck): hygiene pass — repair 389 drifted file:line citations`), the
other in an ordinary `fix(engine)` commit. Every future card is filed the
same way.

## Why it matters

The concrete loss is portability of the deck, which is the product. Nothing
inside this repo reads cards with a strict parser today — the engine, the
Python session-start hook, and the OpenClaw TypeScript port all mirror
`yaml_lite`'s permissiveness on purpose — so the failure is silent *here* and
lands on whoever reads the deck from outside it: `yq`, an editor's frontmatter
pane, a static-site generator, a downstream importer, a consuming repo's own CI
step. Each of those fails on the file rather than on a goc command, with an
error naming YAML rather than naming the card.

The severity ceiling is set by that containment, which is why this is
`contribution: medium` and not `high`. The severity *floor* is that the gap is
unowned and monotonically growing: every hand-authored card is another draw,
and the deck currently gains cards faster than anything reads it strictly, so
the count only goes up until something checks.

This repo has already decided this exact question once. The identical defect on
the sibling surface —
[`skill-frontmatter-descriptions-break-yaml-loading`](../skill-frontmatter-descriptions-break-yaml-loading/)
— was a real outage, not a theoretical one: unquoted `: ` in shipped `SKILL.md`
frontmatter made Codex's plugin cache skip `kickoff`, `advance-card`,
`pull-card` and `next-card` entirely, "even though GoC's permissive YAML-lite
parser accepts the same files". It closed with a repo-local guard,
`tests/test_skill_frontmatter_strict_yaml.py`. A sweep of all 99 shipped
`SKILL.md` files and every in-tree `.yaml`/`.yml` file is clean today, so the
card README is the one frontmatter surface in the repo with no guard on it.

## Fix (landed)

Two mechanical parts, no new dependency.

1. **Both offending summaries re-emitted through `emit_frontmatter`**, which
   quotes and escapes them correctly. Only the `summary` line changed in each
   file, and re-parsing confirms every frontmatter field — summary included —
   holds an identical value before and after.

2. **`scripts/check_card_frontmatter_yaml.py`** is the guard, enforced from
   `tests/test_card_frontmatter_yaml.py` and from the `card-frontmatter-yaml`
   pre-commit hook next to `card-language`. It detects the two hazard shapes
   statically: a plain scalar matching `:(?:[ \t]|$)`, and a plain scalar
   opening with a YAML indicator. `|` and `>` are exempted only as a complete
   block header, by reusing `engine._YAML_BLOCK_HEADER_RE` rather than
   restating it. `reproduce.py` § 3 is the calibration — zero false positives
   and zero false negatives against PyYAML across the deck.

   Building it turned up one bug in the guard itself, now pinned by
   `test_check_exits_nonzero_on_an_offending_deck`: `main` counted cards from
   the late-bound `DECK_DIR` global but scanned through `scan_deck`'s default
   argument, which binds once at definition. Pointed at a planted offender the
   two disagreed, and the guard reported `clean (1 cards scanned)` while exiting
   `0` — a guard that cannot be exercised end-to-end is the failure mode
   `static-source-guards-never-prove-they-can-catch-an-offender` describes.
   `scripts/check_card_language.py:266` carries the same shape; it is harmless
   there because nothing repoints its `DECK_DIR`, so it is left alone rather
   than changed as drive-by scope.

### Why the guard is repo-local rather than a `goc validate` check

Not taste; the alternative is closed. `goc validate` ships to consumers, and a
strict-YAML check inside it would need a strict YAML parser — the dependency
[`drop-third-party-runtime-dependencies-from-goc`](../drop-third-party-runtime-dependencies-from-goc/)
deliberately removed, and which `yaml_lite` exists to replace. Re-adding
strictness to `yaml_lite` itself is a *different* card: it changes the
acceptance set every existing consumer deck is already parsed under, which is
the migration risk that card's own DoD ruled out ("zero on-disk migration —
every existing card stays bit-identical").

Repo-local also matches how this repo has settled the same placement question
twice: `tests/test_skill_frontmatter_strict_yaml.py` for skill frontmatter, and
`scripts/check_card_language.py` for the English-only card rule — both
repo-local, both enforced from the regression suite, neither shipped to a
consumer. This card follows the `check_card_language.py` shape exactly, because
that guard is the closest analogue: a repo-local rule about *card frontmatter
fields*, standalone-runnable, imported by a test, and wired into pre-commit so
it fires on the filing path rather than only on push.

## Scope boundary

- **Not the engine's acceptance set.** Whether `yaml_lite` should *reject*
  these shapes for every consumer is a separate, decision-class question with a
  migration cost; this card does not touch `goc/_vendor/yaml_lite.py`.
- **Not the emitter.** `emit_frontmatter` already quotes both shapes correctly
  (see Reachability), and
  [`frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values`](../frontmatter-emitter-does-not-quote-indicator-or-whitespace-padded-values/)
  closed the emitter's own indicator gap.
- **Known adjacent gap, deliberately left.** The existing skill guard checks
  the nested-`: ` hazard but not the leading-indicator one, so it would not
  have caught the backtick offender. No shipped `SKILL.md` carries that shape
  today, so it is a coverage gap rather than a live defect; sharing one detector
  across both surfaces is the natural follow-up and is not attempted here.
- **Not a doc fix.** The kickoff briefing's claim is correct; the deck is what
  drifted from it.
