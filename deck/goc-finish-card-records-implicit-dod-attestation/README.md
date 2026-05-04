---
title: goc-finish-card-records-implicit-dod-attestation
summary: |-
  The frontmatter `definition_of_done` checklist is the *card-specific*
  closure contract. Two implicit DoD layers also exist but are not
  recorded in the closure: (a) project-wide ("tests pass, /mindset
  audit, ruff/pre-commit") enforced today by hooks + finish-card
  prose, and (b) GoC-wide ("all advanced_by closed, schema validates,
  log.md has closure entry") enforced by deck.py validate. Neither
  is persisted as part of the closure record, so a 6-month-old log.md
  reader cannot tell what was actually checked. Update finish-card
  to auto-generate a "Closure verification" attestation block in
  log.md listing both implicit-DoD layers and their pass/fail status.
  Closure becomes auditable: visible boxes ticked + invisible
  conditions verified.
status: done
stage: null
contribution: medium
created: 2026-05-03
closed_at: 2026-05-03
human_gate: none
advances: []
advanced_by: []
tags: [epic, infra]
definition_of_done: |
  - [x] **Define the implicit DoD layers** in deck/SCHEMA.md (or equivalent doc): layer-1 (card-specific, frontmatter) + layer-2 (project-wide, declared in CLAUDE.md) + layer-3 (GoC-wide, universal). Each layer has a list of named checks with pass/fail signals.
  - [x] **Layer-2 list extracted from CLAUDE.md** (current implicit set: tests pass, ruff/format, pre-commit hooks pass, /mindset audit pass, no debug code). Extract into a structured form (`.claude/deck-config.yaml` or similar) so finish-card can read it.
  - [x] **Layer-3 list extracted from deck conventions**: all advanced_by closed (deck.py validate exit 0); schema validates; log.md has closure entry; frontmatter DoD checkboxes ≥ N/N or explicitly waived.
  - [x] **finish-card skill updated**: at closure time, run all layer-2 + layer-3 checks, and append a "Closure verification (DATE)" section to log.md with the result of each. Pass/fail per check; one-line rationale on each pass.
  - [x] **prepare-commit skill aligned**: the commit message generated at finish-card closure references the attestation by date, so the commit log itself points back to the verifiable record.
  - [x] **Pilot on one closure**: next card closed via finish-card after this lands carries the new attestation block. Verify the block reads useful (not noisy boilerplate).
  - [x] **Backfill not in scope**: past closures keep their existing log.md format. The attestation is forward-only.
---

# goc-finish-card-records-implicit-dod-attestation

## Tier

**Epic — closure-rigor improvement.** Smaller blast radius than the
`advances` rename; one skill (finish-card) plus one structured config
file. Independent of the rename; can land in either order.

## Background

The conversation on May 3 surfaced that DoD operates in three layers
in this repo:

| Layer | Where it lives today | Visible at closure? |
|---|---|---|
| 1. Card-specific | frontmatter `definition_of_done` checklist | ✓ (boxes ticked) |
| 2. Project-wide | CLAUDE.md prose ("tests pass, ruff green, /mindset audit pass") | ✗ (only in skill prose) |
| 3. GoC-wide | deck.py validate + finish-card behavior | ✗ (no record) |

Today's closure record is the layer-1 ticked boxes plus the freeform
log.md entry. Reading a 6-month-old closure, you can see *what work
was tracked* but not *what conditions were checked at the moment of
closure*. The implicit DoDs — the assumptions that "of course tests
pass" or "of course /mindset was audited" — are invisible.

User's framing (May 3): "Should we make that explicit in each
frontmatter? Maybe at time of closing add them so we see that the
closer has 'checked against implicit DoDs'?"

The right answer is at closure time, not in frontmatter — the frontmatter
DoD is the *card-specific* contract; project- and GoC-wide DoDs are
the *meta*-contract that applies to every card. Persisting the
attestation at closure makes the meta-contract visible per-card
without bloating frontmatter with boilerplate.

## What the attestation looks like

Concrete proposal (auto-appended by finish-card to log.md):

```markdown
## Closure verification (2026-05-03)

Layer-1 (card DoD): 4/4 boxes ticked.

Layer-2 (project, from CLAUDE.md):
- [x] Tests pass (706 / 0 failed / 3 xfailed)
- [x] ruff check + format clean
- [x] Pre-commit hooks pass (ruff, end-of-files, deck-validate)
- [x] /mindset audit: PASS — no axiom touched, mechanical fix
- [x] No debug code / blocking ops in async / broad except

Layer-3 (GoC):
- [x] All advanced_by cards closed
- [x] deck.py validate (schema + bidirectional edges)
- [x] log.md has closure entry (this section + prior verdict entry)
- [x] Frontmatter DoD = 4/4 (no waivers)
```

The closer (human or pull-card agent) reads each check at closure
time, attests result + one-line rationale, and the block is committed
alongside the closure. **Auditable at any future point.**

## Why "session" gate

The layer-2 list lives in CLAUDE.md prose today; extracting it into
structured form is an editorial decision (which prose-rules count
as gateable, which are advisory). The user should review the extracted
list before it becomes the canonical layer-2 list for the project.

Layer-3 is more universal across GoC installations — once defined,
it's stable; the per-project layer-2 is the variability point.

## Implementation sketch

1. **Config file**: `.claude/deck-config.yaml` (or similar) with two
   sections:
   ```yaml
   layer_2_project_dod:
     - name: tests-pass
       check: uv run pytest
       pass_signal: exit 0
     - name: ruff-clean
       check: uv run ruff check . && uv run ruff format --check .
       pass_signal: exit 0
     - name: mindset-audit
       check: manual
       pass_signal: closer attests in log.md
     - ...

   layer_3_goc_dod:
     - name: advanced_by-closed
       check: deck.py validate
       pass_signal: exit 0
     - ...
   ```

2. **finish-card skill update**: read the config, run automated checks,
   prompt for manual attestations, write the formatted block to log.md.

3. **prepare-commit alignment**: when finish-card invokes prepare-commit,
   the generated commit message includes "Closure verified per
   `<card>/log.md` § Closure verification (DATE)".

## Open questions for the session-gate decision

1. Which CLAUDE.md prose rules become layer-2 checks vs stay advisory?
2. Are there project-specific checks not in CLAUDE.md that should
   be added (e.g., does the doc-consistency-checker subagent always
   need to run pre-closure)?
3. How does finish-card handle a check failure — block closure
   (refuse to close) or proceed with a documented waiver?

## Why this is medium impact (not high)

- Audit-trail improvement, not a behavior change. Closures still happen;
  they just record more context.
- Tooling change, not methodology change (the rename card is the
  methodology change).
- Backfill not in scope, so existing 100+ closed cards stay as-is.
  The new attestation is forward-only.

## Cross-references

- Spawned by: May 3 user discussion on DoD layers
  (companion card: [`goc-rename-blocks-to-advances-and-design-value-sort`](../goc-rename-blocks-to-advances-and-design-value-sort/)).
- Affects: `Skill(finish-card)`, `Skill(prepare-commit)`, possibly
  `Skill(deck)` documentation.
- Touches: every future card closure (forward-only).

## Orphan-epic note

This is leaf-level GoC tooling work; the `epic` tag is editorial
grouping with sibling `goc-*` infrastructure cards, not a
child-aggregator declaration. Empty `advanced_by` is correct.

## Decision

*Resolved 2026-05-03:* Proceed now in full; on automated-check failure (pytest/ruff/etc.) finish-card blocks closure outright

*Reasoning:* closure-audit gap is the highest-leverage GoC improvement and ~1 day of skill+config work; closure-rigor is the contract and waivers normalise drift
