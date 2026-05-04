## 2026-05-04 — Closure

- **What changed**: `README.md`, `pyproject.toml`, and `docs/cli.md` now frame Game of Cards as an agile methodology first, restore the "agile in the age of AI agents" line, link peer projects in a sober positioning section, and move command-heavy install/reference detail to a CLI guide.
- **Verification**: `uv run goc validate` passed.
- **Audit**: PASS — no project principle touched, documentation/metadata fix.
- **Project impact**: README first-run path is prompt-first while manual install is package-manager-neutral between `uv tool install` and `pipx`.
- **Tests**: `goc validate` passed; pytest not run because this is documentation and package metadata copy only.

## Closure verification (2026-05-04)
