## 2026-07-25T04:39:14Z — Closure

- **What changed**: `.github/workflows/pull-card.yml:101`, `.github/workflows/audit-deck.yml:77`, `.github/workflows/refine-deck.yml:81` — `--model claude-fable-5` → `--model opus` in each `claude_args` block.
- **Verification**: `grep -rn -- "--model" .github/workflows/` returns exactly three lines, all `--model opus`; no `claude-fable-5` override remains.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: the autonomous pull/audit/refine fleet runs on the Opus tier again — Claude Opus 5 as of today — and will track future Opus releases without a YAML edit. Predecessor card re-pin-autonomous-workflows-to-fable-5-after-re-enable amended with a forward pointer explaining why its explicit-id spelling did not survive the tier change.
- **Tests**: n/a (workflow config edit; `goc validate` clean)

## Closure verification (2026-07-25T04:39:17Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-25 — Closure' present
