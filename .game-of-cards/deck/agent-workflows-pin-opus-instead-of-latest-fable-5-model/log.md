## 2026-06-10T07:50:00Z — Closure

- **What changed**: `.github/workflows/audit-deck.yml:77` and `.github/workflows/pull-card.yml:104` — `--model opus` → `--model claude-fable-5` in the claude-code-action `claude_args` blocks.
- **Verification**: `grep -rn -- "--model" .github/workflows/` returns exactly the two updated lines; no other workflow passes a model override (claude.yml, claude-code-review.yml, and the release.yml smoke jobs inherit the action default by design).
- **Audit**: PASS — no principle touched, mechanical fix (no rubric configured).
- **Project impact**: autonomous audit-deck and pull-card runs now execute on Claude Fable 5, the current top-tier model for long-horizon agentic work.
- **Tests**: n/a — YAML config change only; no Python code touched.

## Closure verification (2026-06-10T07:45:19Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-10 — Closure' present
