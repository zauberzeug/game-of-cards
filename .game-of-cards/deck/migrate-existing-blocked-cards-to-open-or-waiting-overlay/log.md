## 2026-05-26T13:09:57Z — Closure

- **What changed**: two cards reclassified off `status: blocked`.
  `llms-txt-still-recommends-uv-tool-install-as-preferred`
  → `status: open` (prereq already terminal, derived readiness
  handles it). `openclaw-subagent-plugin-tools-alsoallow-ignored`
  → `status: open` + `waiting_on: external` (exogenous wait on
  upstream OpenClaw release containing the `alsoAllow` fix). Each
  card got a dated `log.md` entry; the openclaw README's "Partial
  close 2026-05-10" section was rewritten in place to describe the
  overlay instead of the prior blocked framing.
- **Verification**: `uv run goc --status blocked` returns no rows;
  `uv run goc validate` is clean across all cards.
- **Audit**: PASS — no rubric configured; mechanical fix (no project
  principle touched — this is a typed-state reclassification, the
  three-axis design itself was decided in
  `blocked-status-conflates-dependency-external-wait-and-deferral`).
- **Project impact**: n/a — unblocks the queue and clears the
  `blocked` population so the breaking sibling
  `remove-blocked-from-the-status-enum-and-validator` can run at the
  next release boundary without migrating cards under the new schema.
- **Tests**: n/a (no code change; validate is the gate).
- **Bundled with**: none.

### Scope correction

The original DoD enumerated three target cards. One of them
(`clarify-agent-unblockable-blocked-cards`) had already closed
`done` on 2026-05-11 — two weeks before this card was filed
2026-05-26. The migration filer was working from a stale
snapshot. The DoD was rewritten in place to reflect actual
work performed: 2 reclassifications + 1 already-done card noted
as no-op.

## Closure verification (2026-05-26T13:10:14Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
