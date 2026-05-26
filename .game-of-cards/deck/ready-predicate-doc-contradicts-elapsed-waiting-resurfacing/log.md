## 2026-05-26T23:29:19Z — Closure

- **What changed**: `goc/templates/skills/card-schema/SKILL.md:330-340` — folded the two independent waiting conjuncts (`waiting_on unset` ∧ `waiting_until absent/past`) of the boxed ready predicate into a single `∧ not waiting_impedes(card)` condition, with a one-line gloss that an elapsed `waiting_until` resurfaces the card regardless of `waiting_on`.
- **Verification**: predicate now matches `waiting_impedes` (`engine.py:1628-1629`) and the adjacent prose at `SKILL.md:366-368`; no remaining internal contradiction.
- **Audit**: PASS — no principle touched, mechanical doc-consistency fix
- **Project impact**: n/a
- **Tests**: n/a (doc-only); `uv run goc validate` clean, `sync_plugin_assets.py --check` green (4 mirror files re-synced)

## Closure verification (2026-05-26T23:29:35Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
