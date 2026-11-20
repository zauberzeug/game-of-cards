---
title: bug-tag-row-excludes-epic-though-card-schema-calls-the-axes-orthogonal
summary: "The card-schema tag table defines bug as 'not epic and not story', while the schema reference says epic answers a separate question, whether a card coordinates others, orthogonal to the bug-or-story question of what it delivers. The regression test pins bug plus epic as mistagged. So an umbrella fixing a family of defects cannot be both a bug and the epic its own edges make it, and the deck's 28 meta-fix umbrellas with two or more blocking instances are tagged three ways: 11 bug, 4 epic, 13 neither."
status: active
stage: null
contribution: low
created: "2026-11-16T02:13:20Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the `bug` row and the schema reference's `epic` paragraph agree on whether one card may carry both tags.
  - [ ] MECHANICAL: the `bug` row in `goc/templates/skills/card-schema/SKILL.md` and § "The `bug` / `story` / `epic` rows" in its `reference.md` state one rule. Recommended: the row drops its `not epic` clause, leaving `not story (default for findings)`, and the reference says a bug-family umbrella may carry `bug` and `epic` together, as it already says of `story` and `epic`.
  - [ ] TDD: `tests/test_canonical_tag_rows.py` `_score_bug` transcribes the amended row, and the `bug carrying epic` offender becomes an accepted case. Under the alternative (keep the exclusion), the offender stays and the reference states the exclusion and why.
  - [ ] MECHANICAL: no card's tags are changed mechanically by this card. Retagging any of the umbrellas the census lists is a per-card judgment, recorded on that card if made.
  - [ ] MECHANICAL: all five mirrors regenerate — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` are clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass.
worker: {who: "claude[bot]", where: main}
---

# The `bug` tag row excludes `epic` though the card schema calls the two axes orthogonal

## Location

- `goc/templates/skills/card-schema/SKILL.md:258` — the `bug` row of the
  canonical tag table.
- `goc/templates/skills/card-schema/SKILL.md:259` — the `epic` row.
- `goc/templates/skills/card-schema/reference.md:313-315` — the `epic`
  paragraph of § "The `bug` / `story` / `epic` rows".
- `tests/test_canonical_tag_rows.py:92-94` — `_score_bug`, and line 135,
  the `bug carrying epic` offender.
- Mirrors of both skill files under `.claude/`, `.codex/`,
  `claude-plugin/`, `codex-plugin/` and `openclaw-plugin/`.

## What's broken

The tag table defines `bug` by excluding `epic`:

> | `bug` | not `epic` and not `story` (default for findings) | state |

The reference that explains the table says the two questions are
independent:

> **`epic` — whether the card coordinates others.** Orthogonal to the
> first question: an epic that is itself a capability delivery
> legitimately carries `epic` *and* `story`.

The first question is bug-or-story, what the card delivers. If `epic` is
orthogonal to it, a card that fixes something broken and coordinates
the cards that fix its instances is a `bug` and an `epic`. The row
forbids that, and the regression test pins the row: `_score_bug` returns
false for any card carrying `epic`, and `bug carrying epic` sits in the
offender list the scorer must reject.

The `story` half of this was reconciled when
[story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it](../story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it/)
closed: its row now says only "disjoint from `bug`", and the reference
gained the orthogonal `epic` paragraph quoted above. The `bug` row kept
its `not epic` clause.

## Empirical evidence

`reproduce.py` reads the row, the reference paragraph and the test, and
groups every `meta-fix` card whose closure two or more `advanced_by`
instances block, the shape the `epic` row describes:

```
card-schema SKILL.md bug row      : | `bug` | not `epic` and not `story` (default for findings) | state |
  excludes epic                   : True
reference calls epic orthogonal   : True
test pins 'bug carrying epic' bad : True

meta-fix cards with >=2 advanced_by (the epic row fires on each): 28
  tagged bug     : 11
      active-state-conflates-being-worked-on-with-parked-at-human-gate (open, 4 instances)
      bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes (open, 10 instances)
      dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting (open, 3 instances)
      draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it (open, 3 instances)
      goc-decide-leaves-prior-decision-block-when-the-body-already-has-one (open, 2 instances)
      goc-repair-edges-apply-leaves-edge-repairs-uncommitted (open, 2 instances)
      pattern-generalization-mutation-detector-matches-git-staging-by-literal-flag-tokens (open, 4 instances)
      query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it (open, 11 instances)
      query-views-each-decide-by-hand-which-filters-apply-and-keep-drifting (open, 6 instances)
      render-verdict-reimplements-apply-dod-rewrites-fixable-predicate-and-drifts (open, 4 instances)
      unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes (open, 7 instances)
  tagged epic    : 4
      goc-verbs-emit-frontmatter-their-own-validator-rejects (active, 4 instances)
      mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success (open, 9 instances)
      ship-game-of-cards-as-cross-agent-cli (done, 15 instances)
      terminal-status-guard-missing-across-mutation-verbs (done, 4 instances)
  tagged neither : 13
      block-scalar-emitter-reenumerates-parser-whitespace-rules-and-keeps-drifting (open, 6 instances)
      board-renderer-keeps-dropping-cards-the-table-shows (open, 5 instances)
      decision-required-options-have-no-machine-readable-shape-and-parsers-keep-drifting (open, 4 instances)
      doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them (open, 38 instances)
      dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting (open, 7 instances)
      extend-pull-readiness-coupling-invariant-to-the-board-not-ready-predicate (open, 4 instances)
      frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting (open, 12 instances)
      hook-scripts-keep-spawning-one-crash-fix-per-malformed-input-shape (open, 5 instances)
      openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting (open, 5 instances)
      session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting (open, 14 instances)
      sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting (open, 5 instances)
      waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift (open, 4 instances)
      yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting (open, 7 instances)

CONTRADICTION: the bug row forbids epic while the reference makes the two
axes independent, so a bug-family umbrella has no consistent tagging.
```

The umbrellas are wired the way
[meta-fix-umbrella-cards-leave-sibling-family-advanced-by-edges-unwired](../meta-fix-umbrella-cards-leave-sibling-family-advanced-by-edges-unwired/)
prescribes, instances in `advanced_by`, so each one meets the `epic`
row. Authors then pick between a `bug` tag the row forbids next to
`epic`, an `epic` tag that drops `bug`, or neither.

## Why it matters

- `goc --tag bug` and `goc --tag epic` each return an arbitrary subset
  of the deck's umbrellas, so neither filter answers "which open cards
  fix a family of defects" or "which cards coordinate others".
- A tag sweep scoring the `bug` row literally would report any umbrella
  that gains `epic` while keeping `bug`, although the reference says the
  pair is coherent. `Skill(refine-deck)` reports and never strips, so
  the cost is noise, but it is noise about a rule the schema itself
  contradicts.
- The table ships to every consumer through `Skill(card-schema)`.

## Fix

Recommended: drop the `not epic` clause from the `bug` row, leaving
`not story (default for findings)`; say in the reference that a
bug-family umbrella may carry `bug` and `epic`, as it says of `story`;
make `_score_bug` transcribe the new row and move `bug carrying epic`
from the offenders to the accepted cases. This matches the reference's
own reasoning and the `story` precedent, and needs no retagging.

Alternative: keep the exclusion, and have the reference say that a
coordinating card is an `epic` and never a `bug`, and why. The 11
`bug`-tagged umbrellas would then be mistagged, each a per-card call.

## Non-goals

Adding `epic` to the umbrellas that meet its row is a per-card judgment
and outside this card. Nothing here strips or adds a tag mechanically.
