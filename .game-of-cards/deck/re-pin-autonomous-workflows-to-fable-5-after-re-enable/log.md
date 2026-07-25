## 2026-07-04T13:18:15Z — Closure

- **What changed**: `.github/workflows/pull-card.yml:101`, `.github/workflows/audit-deck.yml:77`, `.github/workflows/refine-deck.yml:81` — `--model opus` → `--model claude-fable-5` in each `claude_args` block.
- **Verification**: `grep -rn -- "--model" .github/workflows/` returns exactly the three updated `claude-fable-5` lines; no `opus` override remains.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: autonomous pull/audit/refine runs execute on Claude Fable 5 again, fulfilling the re-pin condition recorded by pin-autonomous-workflows-to-opus-while-fable-5-disabled; that card amended with a forward pointer.
- **Tests**: n/a (workflow config edit; `goc validate` clean)

## Closure verification (2026-07-04T13:18:29Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-04 — Closure' present

## 2026-07-25 — Superseded (forward pointer)

- **What changed**: the three `claude_args` model overrides this card set to `--model claude-fable-5` are now `--model opus`, per [float-autonomous-workflows-back-to-opus-alias](../float-autonomous-workflows-back-to-opus-alias/).
- **Why**: the maintainer moved the autonomous fleet back to the Opus tier. This card's explicit-id spelling was forced by Fable being a different tier — no Opus-tracking alias could name it — not by a rejection of the alias policy from float-opus-alias-on-autonomous-github-workflows. Back on Opus, the alias is expressible and its staleness rationale governs again.
- **Still true**: the fleet keeps one consistent override across pull-card, audit-deck, and refine-deck; `claude.yml`, `claude-code-review.yml`, and the `release.yml` smoke jobs remain on the action default and out of scope.
