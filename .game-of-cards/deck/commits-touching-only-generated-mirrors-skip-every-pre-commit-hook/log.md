## 2026-08-24T05:52:00Z — Closure

- **What changed**: `.pre-commit-config.yaml:23-53` — all four hooks are now
  `always_run: true` with no `files:` filter, and the file's header records why a
  `pass_filenames: false` hook must not carry a trigger narrower than the tree it
  checks. `tests/test_precommit_hook_reachability.py` pins the invariant.
- **Verification**: `reproduce.py` 6/6 guarded paths uncovered → 0 (exit 1 → 0).
  The new test failed 50 subtests against the pre-fix config and passes now.
  End-to-end with pre-commit 4.6.2 installed: drifting `codex-plugin/goc/engine.py`
  and `.claude/skills/deck/SKILL.md` used to print `(no files to check) Skipped`
  four times and exit 0; it now runs all four hooks, repairs both files via the
  sync hook, stages the repair, and exits 1.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is the empty stub); mechanical config fix that makes AGENTS.md § "Skill and
  hook files have two copies" true as written.
- **Project impact**: n/a
- **Tests**: 1033 passed / 0 failed (was 1030 before the three new cases).
- **Bundled with**: none

Two decisions worth recording. `always_run: true` was chosen over widening each
`files:` regex because the enumeration is what drifted in the first place — the
same failure `goc-upgrade-leaves-stale-pre-commit-validate-pattern` recorded — and
the whole hook set costs ~1.5s. And the now-redundant `files:` keys were deleted
rather than left beside `always_run: true`: pre-commit accepts both together
(verified — `always_run` wins), but a dead filter reads as a live scope.

Sibling found during the closure sweep and filed separately: `goc/install.py:64-73`
ships the same shape to every consuming repo — `PRE_COMMIT_HOOK` is
`pass_filenames: false` yet gated on `files: ^\.game-of-cards/deck/.*$`, while a
`skills_source: vendored` consumer's `goc validate` also walks `.claude/skills/`
via `validate_skill_dir_parity`. Not fixed here: it changes shipped behaviour and
overlaps three open `install`-side pre-commit cards.

## Closure verification (2026-08-24T05:33:03Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-24 — Closure' present
