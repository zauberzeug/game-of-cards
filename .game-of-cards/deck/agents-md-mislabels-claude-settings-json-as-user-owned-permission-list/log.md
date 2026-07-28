## 2026-07-26T19:20:00Z — Closure

- **What changed**: `AGENTS.md:201` — the dogfood-sync paragraph now splits its
  two exclusions by their real reasons: the `.game-of-cards/` stubs are
  user-owned, while `.claude/settings.json` is the Claude Code
  hook-registration manifest, excluded because it is a *merge* target whose
  GoC `hooks` entries come from `GOC_CLAUDE_HOOKS` in `goc/install.py`. The
  "project-specific permission allow-list" label is gone, and the paragraph
  states that goc writes no `permissions` block (the `Bash(goc:*)` grant is a
  human step per `Skill(claude-kickoff)`).
  `tests/test_guidance_accuracy.py` — new `ClaudeSettingsOwnershipAccuracyTest`
  (3 guards) wires the claim to the tree.
- **Verification**: `reproduce.py` exit 1 → 0. Regression suite 788 → 791
  tests, all passing. `uv run goc validate` clean (671 OK, no new WARN).
  `scripts/sync_plugin_assets.py --check` OK — no mirror drift (neither
  `AGENTS.md` nor `tests/` is a mirrored surface).
  Guard checked against the defect, not assumed: with `AGENTS.md` reverted to
  `b8f146c3` in a scratch worktree the new test class reports 2 failures / 0
  errors; the initial draft raised a bare `ValueError` on the missing
  paragraph, so the anchor lookup was changed to an `assertIn` with a
  diagnostic message first.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is the empty stub); documentation-accuracy fix, no principle touched.
- **Project impact**: n/a
- **Tests**: 791 passed / 0 failed / 0 xfailed

## Closure verification (2026-07-26T19:12:13Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-26 — Closure' present
