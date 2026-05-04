## 2026-05-03: decision recorded

Claude + extension hook — shipping fast on Claude+AGENTS.md covers six agents indirectly, and community PRs grow per-agent shims post-v1 the way Spec-Kit's integrations grew. Gate decision → none.

## 2026-05-04: OpenCLAW deferred

OpenCLAW is not needed in this repo, so it is deferred out of the v1 harness
scope. Claude and Codex remain the concrete installed harness targets; OpenCLAW
can be reopened when a downstream repo needs native OpenCLAW guidance.

## 2026-05-04 — Closure

- **What changed**: `goc/install.py` — installer agent support now loads registered `goc/templates/agents/<agent>/manifest.json` shims for dry-run, install, and upgrade; Codex skill frontmatter is still rendered from the shared skill templates.
- **Verification**: `uv run pytest` -> 7 passed; `uv run goc validate --quiet` -> exit 0; `uv build --out-dir /tmp/...` wheel inspection confirmed both agent manifests are packaged.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: v1 harness registry is Claude + Codex, OpenCLAW remains deferred, and README documents the OpenCode compatibility path.
- **Tests**: 7 passed / 0 failed / 0 xfailed.
- **Bundled with**: n/a.

## Closure verification (2026-05-04)
