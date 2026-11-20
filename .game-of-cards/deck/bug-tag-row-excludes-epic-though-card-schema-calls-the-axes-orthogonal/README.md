---
title: bug-tag-row-excludes-epic-though-card-schema-calls-the-axes-orthogonal
summary: "RESOLVED (2026-11-20): the card-schema tag table defined bug as 'not epic and not story' while its reference calls epic, whether a card coordinates others, orthogonal to the bug-or-story question of what a card delivers, and the regression test pinned bug plus epic as mistagged, so a bug-family umbrella had no consistent tagging: of 28 meta-fix umbrellas with two or more blocking instances, 11 carried bug, 4 epic and 13 neither. The recommended fix landed: the row reads 'not story (default for findings)', the reference says a bug-family umbrella carries bug and epic as a capability epic carries story and epic, and the test accepts the pair and guards both delivery rows against naming epic again. No card was retagged; tagging the umbrellas consistently is a per-card call."
status: done
stage: null
contribution: low
created: "2026-11-16T02:13:20Z"
closed_at: "2026-11-20T04:56:11Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — the `bug` row and the schema reference's `epic` paragraph agree on whether one card may carry both tags. — exits 0: `excludes epic: False`, `reference calls epic orthogonal: True`, `PASS: the bug row and the reference agree.` (exited 1 before the fix).
  - [x] MECHANICAL: the `bug` row in `goc/templates/skills/card-schema/SKILL.md` and § "The `bug` / `story` / `epic` rows" in its `reference.md` state one rule. Recommended: the row drops its `not epic` clause, leaving `not story (default for findings)`, and the reference says a bug-family umbrella may carry `bug` and `epic` together, as it already says of `story` and `epic`. — took the recommended path: the row reads `not `story` (default for findings)`; the reference's `epic` paragraph says either delivery tag may sit beside `epic`, names the bug-family umbrella beside the capability epic, and records why the clause was dropped.
  - [x] TDD: `tests/test_canonical_tag_rows.py` `_score_bug` transcribes the amended row, and the `bug carrying epic` offender becomes an accepted case. Under the alternative (keep the exclusion), the offender stays and the reference states the exclusion and why. — `_score_bug` now rejects only `story`; `bug carrying epic` left `OFFENDERS` for `test_a_bug_family_umbrella_satisfies_both_bug_and_epic` (one umbrella card, accepted by both the `bug` and `epic` scorers). Added `test_delivery_rows_leave_epic_orthogonal`, which demonstrates it rejects the pre-fix row. Both new tests fail against the pre-fix row and scorer (verified).
  - [x] MECHANICAL: no card's tags are changed mechanically by this card. Retagging any of the umbrellas the census lists is a per-card judgment, recorded on that card if made. — the only deck files this card touches are its own; the census is unchanged (11 / 4 / 13).
  - [x] MECHANICAL: all five mirrors regenerate — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` are clean. — both print OK.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass. — 1534 tests OK; `goc validate` exits 0.
worker: {who: "claude[bot]", where: main}
---

# The `bug` tag row excludes `epic` though the card schema calls the two axes orthogonal

## Location

As fixed on 2026-11-20:

- `goc/templates/skills/card-schema/SKILL.md:258` — the `bug` row of the
  canonical tag table, now `not `story` (default for findings)`.
- `goc/templates/skills/card-schema/reference.md:314-328` — the `epic`
  paragraph of § "The `bug` / `story` / `epic` rows", now naming the
  bug-family umbrella beside the capability epic, and a note on the
  dropped clause.
- `tests/test_canonical_tag_rows.py:118` — `_score_bug`;
  `:255` — `test_a_bug_family_umbrella_satisfies_both_bug_and_epic`;
  `:270` — `test_delivery_rows_leave_epic_orthogonal`, over
  `DELIVERY_ROWS` and `delivery_rows_naming_epic` at `:97-102`.
- Mirrors of both skill files under `.claude/`, `.codex/`,
  `claude-plugin/`, `codex-plugin/` and `openclaw-plugin/`.

## What was broken

The tag table defined `bug` by excluding `epic`:

> | `bug` | not `epic` and not `story` (default for findings) | state |

The reference that explains the table said the two questions are
independent:

> **`epic` — whether the card coordinates others.** Orthogonal to the
> first question: an epic that is itself a capability delivery
> legitimately carries `epic` *and* `story`.

The first question is bug-or-story, what the card delivers. If `epic` is
orthogonal to it, a card that fixes something broken and coordinates
the cards that fix its instances is a `bug` and an `epic`. The row
forbade that, and the regression test pinned the row: `_score_bug`
returned false for any card carrying `epic`, and `bug carrying epic` sat
in the offender list the scorer had to reject.

The `story` half of this was reconciled when
[story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it](../story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it/)
closed: its row says only "disjoint from `bug`", and the reference
gained the orthogonal `epic` paragraph quoted above. The `bug` row kept
its `not epic` clause.

## Empirical evidence

At filing, `reproduce.py` read the row, the reference paragraph and the
test, grouped every `meta-fix` card whose closure two or more
`advanced_by` instances block (the shape the `epic` row describes), and
exited 1. That run, preserved:

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
row. Authors had to pick between a `bug` tag the row forbade next to
`epic`, an `epic` tag that dropped `bug`, or neither. At closure no
card carries both, of 838 in any status.

After the fix the same script exits 0 with the census unchanged, as
the non-goal requires (per-card lists elided, identical to the run
above):

```
card-schema SKILL.md bug row      : | `bug` | not `story` (default for findings) | state |
  excludes epic                   : False
reference calls epic orthogonal   : True
test pins 'bug carrying epic' bad : False

meta-fix cards with >=2 advanced_by (the epic row fires on each): 28
  tagged bug     : 11
  tagged epic    : 4
  tagged neither : 13

PASS: the bug row and the reference agree.
```

## Why it matters

- A bug-family umbrella can now be tagged consistently: `bug` for what
  it delivers, `epic` when its instances block its closure. Until the
  umbrellas above are retagged, `goc --tag bug` and `goc --tag epic`
  still each return an arbitrary subset of them, but the schema no
  longer stands in the way.
- A tag sweep scoring the `bug` row literally no longer reports an
  umbrella that carries `epic` beside `bug`, a pair the reference
  always called coherent.
- The table ships to every consumer through `Skill(card-schema)`.

## Resolution — the recommended fix

- **Row.** `goc/templates/skills/card-schema/SKILL.md` — the `bug` row
  reads `not `story` (default for findings)`, the same shape as the
  `story` row, which never named `epic`.
- **Reference.** `goc/templates/skills/card-schema/reference.md` § "The
  `bug` / `story` / `epic` rows" — the `epic` paragraph says either
  delivery tag may sit beside `epic`, names the bug-family umbrella
  next to the capability epic, and adds that neither tag implies the
  other: each still needs its own row to hold. A second paragraph
  records that the `bug` row excluded `epic` until 2026-11-20, where
  the clause came from and the three-way split it produced, so the
  next reader does not restore it as an apparent omission.
- **Test.** `tests/test_canonical_tag_rows.py` — `_score_bug` rejects
  only `story`. `bug carrying epic` left `OFFENDERS` and became
  `test_a_bug_family_umbrella_satisfies_both_bug_and_epic`, which
  scores one umbrella card through both the `bug` and `epic` scorers.
  `test_delivery_rows_leave_epic_orthogonal` reads the row text, which
  the scorers are copied from by hand and which nothing else compares
  against the reference, and fails if either delivery row names
  `epic`. Following
  [static-source-guards-never-prove-they-can-catch-an-offender](../static-source-guards-never-prove-they-can-catch-an-offender/),
  it first shows it rejects the pre-fix row. Both new tests fail
  against the pre-fix row and scorer.

### Why not the alternative

Keeping the exclusion would have made `epic` orthogonal to `story` but
exclusive with `bug`, and nothing specific to defects supports that
asymmetry. The argument that would carry it, that an epic's
deliverable is its children's, applies equally to a capability epic,
and the reference already rejects it there.

The clause's own reason is gone. It dates from the first packaged
table (`94975556`, 2026-05-04), where the three tags were structural
roles: `epic` a coordinator, `story` "part of an epic-grouping", and
`bug` the standalone finding that was neither. In that table `not
epic and not story` was coherent. The `story` card redefined `story`
as what a card delivers and made `epic` orthogonal to it, but left the
`bug` row alone, judging that its exclusion "stops being circular"
once `story` had positive content. It never weighed `bug` beside
`epic`, so the row kept a role-based clause inside a table that no
longer assigns roles. The alternative would also have turned 11 live
umbrellas into `bug` mistags, against none for the recommended fix.

## Non-goals

Adding `epic` to the umbrellas that meet its row is a per-card judgment
and outside this card. Nothing here strips or adds a tag mechanically.
