## 2026-05-04 — Closure

- **What changed**: `goc install --codex` / `--agents codex` now plans and writes `.codex/skills/` from the shared GoC skill templates; `goc upgrade --agents codex` refreshes the same tree.
- **Compatibility**: Codex skill copies are normalized to `name` + quoted `description` frontmatter so Claude-only `argument-hint` metadata is not written into `.codex/skills/`.
- **Verification**: dry-run plans list Codex skill writes; fresh temp install wrote 11 valid Codex skills and no `.claude/`; current repo `.codex/skills/*` validated with the Codex skill quick validator.
- **Tests**: `uv run goc validate`; `.venv/bin/python -m compileall goc`; focused fresh-install and dry-run smoke checks.
