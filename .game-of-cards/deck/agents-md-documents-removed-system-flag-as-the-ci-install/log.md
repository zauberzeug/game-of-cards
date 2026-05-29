# Log

## 2026-05-29T04:54:46Z — Closure

- **What changed**: `AGENTS.md` Common-commands line — `uv pip install --system -e .` → `uv pip install -e .  # editable install into the project venv (what CI does)`, matching ci.yml's setup-uv-activated-venv install model.
- **Verification**: AGENTS.md now grep-clean of `pip install --system`; the documented recipe matches `ci.yml` (plain `uv pip install -e .` into the activated `.venv`).
- **Audit**: PASS — no principle touched, mechanical doc-drift fix.
- **Project impact**: n/a (doc accuracy; no code or deck-state change).
- **Tests**: n/a (comment-only doc edit; no executable surface).
- **Bundled with**: n/a (follow-up to bump-deprecated-node-20-github-actions-before-forced-node-24-cutover)

## Closure verification (2026-05-29T04:54:46Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 2/2 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present
