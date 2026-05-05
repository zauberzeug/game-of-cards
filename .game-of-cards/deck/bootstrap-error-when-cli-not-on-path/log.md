## 2026-05-04 — Closure

- **What changed**: `goc/templates/bootstrap/_goc-bootstrap.sh` now ships as a package asset and selected agent manifests copy it into `.claude/skills/` or `.codex/skills/`. Executable skill command injections use the wrapper instead of direct `goc`; Codex generation rewrites the wrapper path for `.codex/skills/`.
- **Verification**: `uv run pytest` -> 12 passed; `uv run goc validate --quiet` -> exit 0; `sh -n` passed for all wrapper copies; `.claude/skills/_goc-bootstrap.sh --version` works in this source repo via `uv run goc`; wheel inspection confirmed the bootstrap asset is packaged.
- **Missing/old/current CLI checks**: installer test covers PATH-empty missing `goc` -> exit 127 exact install line; fake `goc 0.0.1` with required `0.0.2` -> exit 1 exact upgrade line; fake `goc 0.0.2` -> wrapper execs through and preserves args.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: fresh clones of installed GoC repos fail with one actionable install/upgrade line instead of a shell error or traceback.
- **Tests**: 12 passed / 0 failed / 0 xfailed.
- **Bundled with**: n/a.

## Closure verification (2026-05-04)
