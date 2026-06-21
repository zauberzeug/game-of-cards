---
title: meta-fix-umbrella-cards-leave-sibling-family-advanced-by-edges-unwired
summary: "Several open `meta-fix` umbrella cards (the `…-keep-drifting` / `…-reimplement…` family) declare their sibling-bug roster in prose with `[[links]]` but carry empty `advanced_by` edges, so the deck's record/scheduler axes and the board's dependency display never see the family. The established convention (per `render-json-emits-bare-string-edge-fields-as-json-strings-not-lists`) is sibling `advances` umbrella / umbrella `advanced_by` siblings; a refine-deck pass wired two exemplars (`yaml-lite-quote-scanners…`, `dod-fence-mask…`) but the rest need per-body judgment because each umbrella's prose also cross-references *peer* umbrellas (\"same shape elsewhere\"), which must NOT be wired as family edges."
status: active
stage: null
contribution: low
created: "2026-06-21T08:24:27Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [meta-fix]
definition_of_done: |
  - [ ] EMPIRICAL: for each umbrella below, the genuine sibling-bug cards (the family the umbrella retires) are wired `umbrella.advanced_by += sibling` via `goc advance <umbrella> --by <sibling>`, and peer-umbrella cross-references are left UNwired. Verified by re-reading each body to separate the "## family / each was fixed independently" roster from the "same shape elsewhere" cross-references.
  - [ ] MECHANICAL: `goc validate` stays clean (edge symmetry holds by construction via `goc advance`).
  - [ ] PROCESS: the orphaned-meta-fix-family sub-check in `Skill(refine-deck)` Step 2 returns no open umbrella with a prose roster but zero edges (re-run the meta-fix zero-edge survey counting BOTH `advances` and `advanced_by`).
worker: {who: "claude[bot]", where: main}
---

# Meta-fix umbrella cards leave their sibling-family `advanced_by` edges unwired

## What this is

`Skill(refine-deck)`'s orphaned-dependency sub-check catches edge
*absence* — a card whose body declares a family roster but whose
schema edge arrays are empty. The schema validator cannot see this
(it only enforces edge *symmetry*). A hygiene pass on 2026-06-21
found a cluster of open `meta-fix` umbrella cards — the
`…-keeps-drifting` / `…-reimplement…` / `…-reenumerates…` naming
family — that name their sibling-bug roster in prose with `[[links]]`
but carry empty `advanced_by`. As a result the deck's record axis
(walk edges through closed cards to reconstruct a decision's history)
and the board's dependency display never surface the family the
umbrella exists to retire.

## The established wiring convention

`render-json-emits-bare-string-edge-fields-as-json-strings-not-lists`
(filed as the "8th confirmed sibling" of
`bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`)
established the convention: each sibling instance carries
`advances: [umbrella]`, and the umbrella carries
`advanced_by: [siblings…]`. The symmetric pair is set atomically by
`goc advance <umbrella> --by <sibling>`.

## Already wired this pass (exemplars)

- `yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting`
  — wired to its 4 enumerated closed siblings.
- `dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting`
  — wired to its 3 enumerated closed siblings.

## Remaining open umbrellas with a prose roster but zero edges

Each needs its body re-read to separate the genuine family roster
from peer-umbrella cross-references (the bodies routinely cite
`yaml-lite-quote-scanners…` and `dod-fence-mask…` as "the same shape
named elsewhere" — those are NOT family members and must not be
wired):

- `frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting`
  — roster appears to be the 8 `frontmatter-emitter-*` / `inline-emitter-*` bug cards.
- `dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting`
  — roster includes `dry-run-plan-promises-pre-commit-append-…`,
  `goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run`,
  `migrate-dry-run-omits-legacy-tree-removal-for-identical-only-trees`.
- `sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting`
  — roster includes the `openclaw-skill-porter-*` and
  `sync-plugin-assets-*` orphan-pruning bug cards.
- `session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting`
  — roster includes `goc-waiting-filter-drifts-from-engine-…` and
  `standup-impeded-filter-drifts-from-engine-…`.
- `openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting`
  — thinner body; confirm whether it has an instance roster at all
  or is purely a forward-looking umbrella (if no closed siblings
  exist yet, leaving edges empty is correct, not rot).

The three `pattern-generalization-mutation-detector-*` cards share a
root cause but are peer instance bugs, not an umbrella + family — they
need a judgment call on whether one is the umbrella (or whether a new
umbrella should be filed) before any wiring, so they are deliberately
excluded from the mechanical scope here.

## Why it matters

Edge absence is invisible to `goc validate`, so it rots silently. The
record axis is a first-class deck guarantee: a cold reader landing on
a closed sibling should be routed to the umbrella that retires its
class, and a reader on the umbrella should see the evidence trail.
Prose `[[links]]` alone do not feed the scheduler, the board's `⏳`
dependency display, or the `goc --json` edge fields.

## Notes

Filed at `human_gate: none` by an autonomous refine-deck pass with no
human in the loop. This is mechanical orphaned-edge hygiene, not a
taste call — but it was scoped out of the same pass because correctly
wiring each remaining umbrella requires reading its body to exclude
peer-umbrella cross-references, which exceeded the single pass's
budget. The next reader may raise the gate if they disagree with the
roster judgments above.
