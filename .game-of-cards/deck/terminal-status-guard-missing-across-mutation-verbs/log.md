## 2026-06-21: claimed and gate raised to `decision`

An autonomous `pull-card` session pulled this epic (`human_gate: none`,
the only ready card) and discovered its completion depends on resolving
four children that each carry `human_gate: decision`
(`goc-wait-...`, `goc-attest-...`, `goc-quality-pass-...`,
`goc-move-...`). The guard *shape* per verb — notably the `goc move`
`--force` escape hatch and the `quality-pass` filter-vs-error choice —
is a genuine API-contract taste call, and this repo defines no
project-local `pull-card` consultation hook. Per the pull-card Andon
protocol (no hook → surface the decision), the session did the work it
*could* do autonomously: consolidated the four scattered per-verb
option menus into one coherent recommended bundle (the
`## Decision required` section), then raised this epic's gate so the
human approves the family in a single `Skill(decide-card)` action
rather than four.

The recommended bundle: a shared `_refuse_terminal_mutation` helper
(five call-sites now justify it); strict refuse for `wait` and
`attest`; filter+helper-guard for `quality-pass`; reject-with-`--force`
for `move`; and `_cmd_advance`/`_cmd_unadvance` classified **out of
scope** (supersession edges legitimately mutate closed-card
relationships — that pre-answers DoD item 5). No code changed this
session; implementation waits on the decision.

## 2026-07-09T05:30:00Z — Sibling-shape precedent

[`path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck`](../path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck/)
closed by introducing `resolve_card_dir()` — a single shared helper that every
title-taking verb routes through — rather than per-verb inline checks. That is
a working precedent for this epic's "reusable helper that each verb calls"
option in the PROCESS DoD item, and the helper itself (called at the top of
each verb's title resolution) is a candidate hang-point for a shared
terminal-status guard.
