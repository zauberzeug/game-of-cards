---
title: single-source-pattern-check-reminder-across-host-ports
status: open
stage: null
contribution: low
created: "2026-06-09T04:39:15Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [infra, meta-fix]
definition_of_done: |
  - [ ] DECISION: decide whether single-sourcing is worth it given the Python/TypeScript language boundary, and if so, the mechanism (see "Decision required"). Record the decision on this card.
  - [ ] MECHANICAL (if "yes"): the `pattern-check` REMINDER text exists in exactly ONE authored location per language family; every other occurrence is generated/imported, not hand-edited. Re-grep `Before yielding` → one authored source (+ generated mirrors) rather than N hand-maintained copies.
  - [ ] TDD/PROCESS (if "yes"): a drift guard (test or sync `--check`) fails when an authored copy diverges from the single source, mirroring the existing plugin-mirror parity guards.
---

# single-source-pattern-check-reminder-across-host-ports

## Why this card exists

The `pattern_generalization_check` Stop-hook REMINDER string is duplicated across host ports. Any
wording change must be hand-propagated and re-verified, a DRY smell flagged as the stretch DoD item
on the closed-out reword card
[pattern-check-hook-binary-misses-connect-to-existing-root](../pattern-check-hook-binary-misses-connect-to-existing-root/).
That card reworded the REMINDER to a three-branch form and had to touch the string in ~9 places.

## Current state of the duplication

Two of the copy-sets are **already single-sourced** and need no work:

- The 6 Python copies under `claude-plugin/`, `codex-plugin/`, and `.claude/hooks/` are
  byte-for-byte mirrors regenerated from `goc/templates/hooks/pattern_generalization_check.py`
  by `scripts/sync_plugin_assets.py` (CI-enforced via `--check`). The authored Python source is
  already a single file.

So the genuine remaining duplication is across the **language boundary**:

1. the Python authored source — `goc/templates/hooks/pattern_generalization_check.py`
2. the OpenClaw TypeScript port — `openclaw-plugin/index.ts` (`PATTERN_REMINDER`)

These are different languages with different invocation phrasing (`Skill(create-card)` vs
`goc verb='new'`), so they cannot trivially import one literal.

## Decision required

Is single-sourcing across the Python/TS boundary worth the machinery, and if so how? Candidate
mechanisms:

- **A shared data file** (e.g. a `.txt`/JSON fragment under `goc/templates/`) that both the Python
  hook reads at runtime and the OpenClaw build inlines — with the host-specific invocation token
  (`Skill(create-card)` vs `goc verb='new'`) interpolated. Adds a build/read step to both ports.
- **A generator** that emits both `PATTERN_REMINDER` (TS) and the Python `REMINDER` from one source,
  guarded by a `--check` drift test (mirrors `port_skills_to_openclaw.py`).
- **Do nothing** — accept two authored copies and rely on a lightweight drift test asserting the two
  strings stay structurally equivalent. Lowest cost; keeps the wording honest without a build step.

The "do nothing + drift test" option may well be the right call given there are only two authored
copies after the sync mirrors are accounted for. That is the decision this card exists to make.

## Scope guard

REMINDER-string sourcing only. Does not touch detection logic or the sync/mirror machinery that
already keeps the Python copies in lockstep.
