## 2026-05-04 — Closure

- **What changed**: tests/test_version_surfaces.py — CI now checks `pyproject.toml`, `goc.__version__`, `deck/.goc-version`, and AGENTS/CLAUDE marker versions stay aligned.
- **Verification**: `uv run pytest` -> 33 passed; `uv run python -m unittest discover -s tests` -> 33 tests OK; `uv run goc validate --quiet` -> exit 0.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: live self-hosted version drift is now guarded before release; archival deck mentions remain untouched.
- **Tests**: 33 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-04)
