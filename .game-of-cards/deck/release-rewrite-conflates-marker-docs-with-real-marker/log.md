## 2026-05-19T17:58:51Z — Closure

- **What changed**: `scripts/release_rewrite_versions.py:118-128` — AGENTS.md marker pattern tightened from `<!-- BEGIN GOC v[^>]+ -->` to `^<!-- BEGIN GOC v\d+\.\d+\.\d+ -->$`. Line-start anchor matches `_append_marker_block`'s output convention; semver-digit anchor rejects placeholder mentions like `vX.Y.Z`.
- **Verification**: AGENTS.md match count dropped from 3 → 1. Re-dispatched release run 26115138057 reached "Create and push release tag" (previous run 26114783065 failed there); all five jobs green (Build, smoke, PyPI, npm, ClawHub). v0.0.20 tag exists; bot's `release: bump version literals to v0.0.20` commit (d91d0e3) shipped only the real marker line, leaving the two prose mentions untouched.
- **Audit**: PASS — no principle touched, mechanical fix (no project rubric configured).
- **Project impact**: n/a.
- **Tests**: not run (script-only change; no test suite in this repo).
- **Bundled with**: none.

## Closure verification (2026-05-19T17:59:19Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-19 — Closure' present
