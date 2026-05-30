## 2026-05-30T14:04:29Z — Closure

- **What changed**: `goc/engine.py` — added `_DeepDircmp(filecmp.dircmp)` (overrides `phase3` to call `filecmp.cmpfiles(..., shallow=False)` and re-points `methodmap` so `same_files`/`diff_files`/`funny_files` lazy attrs use the deep variant); `validate_plugin_mirror_parity` swaps `filecmp.dircmp(src, dst)` → `_DeepDircmp(src, dst)`. The three plugin mirrors (`claude-plugin/goc/engine.py`, `codex-plugin/goc/engine.py`, `openclaw-plugin/goc/engine.py`) had silently drifted in earlier work because the shallow check missed it; `scripts/sync_plugin_assets.py` regenerated them as part of this commit.
- **Verification**: 299 tests pass (incl. new `test_same_length_same_mtime_drift_is_detected`); `goc validate` green; reproducer demonstrates the underlying stdlib gap (dircmp says `same_files: ['file.txt']`, `cmp(shallow=False)` returns `False` on a same-length pair).
- **Audit**: PASS — no rubric configured; mechanical fix (aligns the engine's directory comparison policy with the sibling sync script, no project principle touched).
- **Project impact**: n/a
- **Tests**: 299 passed / 0 failed / 0 xfailed
- **Bundled with**: (none)

## Closure verification (2026-05-30T14:04:42Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
