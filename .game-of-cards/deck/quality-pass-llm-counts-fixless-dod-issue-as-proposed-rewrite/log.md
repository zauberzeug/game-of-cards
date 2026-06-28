# Log

## 2026-06-21 — closed (done)

Fixed `_render_verdict` (`goc/engine.py`) so the DoD branch only sets
`has_rewrite = True` for issues carrying both `idx` and `fix` — mirroring
`_apply_dod_rewrite`'s apply-side guard. Fixless flagged issues now print as
"flagged, no rewrite offered" without inflating `rewrite_count` or triggering
the interactive apply loop. This is the DoD-branch sibling of commit `678594d`,
which had aligned only the title/summary branches.

- `reproduce.py`: over-count assertion fails pre-fix, passes post-fix.
- `tests/test_render_verdict_rewrite_count.py`: added `test_fixless_dod_issue_not_counted`
  and `test_mixed_fixable_and_fixless_dod_issues`.
- Plugin engine mirrors re-synced via `scripts/sync_plugin_assets.py`.
- Full suite: 483 tests pass; `uv run goc validate` clean.
