## 2026-06-07T05:11:45Z — Closure

- **What changed**: `goc/engine.py:_build_parser` now registers `--version`/`-V`
  as an argparse `action="version"` (version string `goc, version <X>`); the
  hand-rolled `argv[0]` intercept and the now-unused `__version__` import were
  removed from `goc/cli.py`. The flag is now position-independent among
  top-level options and listed in `goc --help`. Plugin mirrors
  (`claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`) re-synced.
- **Verification**: `reproduce.py` exits 0 — all four shapes pass
  (`goc --version`, `goc -V`, `goc --no-color --version`,
  `goc --status all --version`), and `--version` appears in `goc --help`.
  New regression test `tests/test_version_flag_position.py` (3 cases) green.
- **Audit**: no rubric configured; mechanical fix (argparse plumbing —
  no project principle touched).
- **Project impact**: n/a
- **Tests**: 405 passed / 0 failed / 0 xfailed (402 prior + 3 new), full
  `unittest discover` suite; `goc validate` and plugin-mirror `--check` clean.
- **Bundled with**: n/a

## Closure verification (2026-06-07T05:15:57Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-07 — Closure' present
