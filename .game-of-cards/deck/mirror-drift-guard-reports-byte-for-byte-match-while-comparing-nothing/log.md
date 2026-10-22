## 2026-09-12T04:33:09Z — Closure

- **What changed**: `scripts/sync_plugin_assets.py:234` — `_skip` tests `path.parts` / `path.suffix` instead of substring-matching `str(path)`, so an ancestor directory containing `__pycache__` or `.pyc` no longer skips every item the mirror walk offers; `_SKIP_FRAGMENTS` removed with its last reader.
- **Verification**: `reproduce.py` exit 1 → 0 (`--check` on the drifted `.pycharm/checkout` fixture: exit 0 → 1, and the sync now repairs both the corrupted mirror and the deleted hook). New `tests/test_sync_skip_predicate_scope.py` fails 6 assertions against the old substring predicate, passes 4/4 against the fix.
- **Audit**: PASS — no rubric configured; mechanical fix. The change makes the fourth copy of the exclusion predicate agree with the three that were already correct, adding no new convention.
- **Project impact**: n/a
- **Tests**: 1109 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`); `uv run goc validate` exit 0.
- **Bundled with**: none. The sibling umbrella `sync-mechanisms-reimplement-orphan-pruning-and-drift-detection-and-keep-drifting` does not cite this predicate and is unaffected.
- **Note**: `reproduce.py`'s `sync run` line was reworded to print the script's exit code alongside its stdout — the fixture is not a git repo, so the sync's closing `git add` fails after the files are written, and the old `(no output — total no-op)` label would have misread a successful repair as a no-op on every green run.

## Closure verification (2026-09-12T04:33:12Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-09-12 — Closure' present
