## 2026-05-04 — Closure

- **What changed**: `goc/engine.py` — `goc move` now performs a real rename without recreating `REDIRECT.md`, `load_all_cards` no longer special-cases redirect-only directories, and `goc validate` reports deck subdirectories missing a valid card README.
- **Verification**: `uv run pytest` -> 9 passed; `uv run goc validate --quiet` -> exit 0; `find deck -maxdepth 1 -type d -name 'goc-*' -print` -> no output; `uv run goc move --help` -> no redirect wording.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: deck contains live card directories only, and stale filesystem/relation references are validation errors instead of redirect compatibility state.
- **Tests**: 9 passed / 0 failed / 0 xfailed.
- **Bundled with**: n/a.

## Closure verification (2026-05-04)
