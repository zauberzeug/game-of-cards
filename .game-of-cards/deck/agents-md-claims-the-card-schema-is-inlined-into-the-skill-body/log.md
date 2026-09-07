## 2026-08-06T05:44:00Z — Closure

- **What changed**: `AGENTS.md:160-168` — the `goc/schema.yaml` bullet now
  describes the mechanism that exists (a byte-identical sibling copy at
  `goc/templates/skills/card-schema/schema.yaml`, copied verbatim by
  `goc install` and the plugin mirrors) instead of an install-time inlining
  step that no code performs, and names the hand-sync obligation plus the
  test that enforces it. Pinned by three new assertions in
  `tests/test_guidance_accuracy.py::AgentsArchitectureAccuracyTest`.
- **Verification**: `reproduce.py` exits 0 (was 1); `[1]` — AGENTS.md lines
  asserting the stale claim — goes `[161]` → `[]`. `tests/test_guidance_accuracy.py`
  26 passed (23 before). `goc validate` exits 0.
- **Audit**: no rubric configured (`.game-of-cards/hooks/finish-card.md` is an
  empty stub); doc-accuracy fix, no principle touched.
- **Project impact**: n/a
- **Tests**: 911 passed / 1 failed / 0 xfailed. The one failure is
  `test_canonical_tag_rows.test_live_cards_satisfy_every_state_row`, red on
  `main` **before** this card — reproduced identically in a detached worktree
  at `1ed2ddb2`, the commit that filed the offending card. Tracked by
  `regression-suite-red-on-main-over-the-unverified-tag-row`, filed this
  session at `human_gate: decision` because the guard's two exits (retag the
  card / rewrite the row) are both defensible and it forbids picking by
  widening. The final DoD item was rewritten before ticking to say exactly
  this rather than claim a green suite.
- **Note on the guard's shape**: the two doc assertions are backed by a
  behavioural one (`test_skill_body_really_carries_no_inlined_schema`) that
  reads the schema's top-level keys out of `goc/schema.yaml` and asserts none
  appear in `SKILL.md`. Without it the doc guard would keep pinning
  "not inlined" even if inlining were later implemented — the
  restate-instead-of-derive failure this repo has hit before. The key list is
  read from the file rather than enumerated, matching the fix in
  `schema-parity-guard-enumerates-keys-so-new-keys-drift-unseen`.
- **Deliberately not done**: auto-syncing `goc/schema.yaml` into the template
  copy via `scripts/sync_plugin_assets.py`. That is a mechanism change with
  two credible answers and needs a human pick; this card only corrected the
  briefing about the mechanism that exists today.

## Closure verification (2026-08-06T05:41:09Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-08-06 — Closure' present
