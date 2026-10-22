
## 2026-09-10T04:42:47Z — Closure

- **What changed**: `goc/templates/game_of_cards/README.md:54` (+ the dogfood copy `.game-of-cards/README.md:54` and three regenerated plugin mirrors) — the `hooks/audit-deck.md` row's phantom `Phase 0` anchor becomes `Context`, the section the hook is really injected under; `tests/test_readme_hook_catalogue_parity.py` gains `HookCatalogueRowAccuracyTest`, widening the guard from column 1 (the stub set) to the `Loaded by` and `Workflow point` columns.
- **Verification**: `reproduce.py` 1 → 0 (2 phantom anchors → 0, across 2 README copies). Both new guards mutation-tested: reinstating `Phase 0` and repointing the `refine-deck` row at `scan-deck` each turn the suite red.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md` is an empty stub); mechanical doc fix plus its derived guard.
- **Project impact**: n/a
- **Tests**: 1105 passed / 0 failed / 0 xfailed (1102 before — three new cases).
- **Bundled with**: n/a

Notes for the next reader: `git log -S "Phase 0" --all` shows the anchor never
existed in any shipped skill — it was wrong in the commit that first wrote the
catalogue (`46bfdfc5`, 2026-05-04) and was copied forward into every plugin
payload. The row edit is the small half; the widened guard is the half that
generalizes, and it is why the next added row cannot repeat this.

## Closure verification (2026-09-10T04:42:48Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-09-10 — Closure' present
