## 2026-05-27 — CONFIRMED and fixed

Hypothesis verified true. `reproduce.py` builds `cycle`-terminated
multi-hop paths (`["C","A","cycle"]`, `["A","cycle"]`) and feeds them to
`_format_why`. Pre-fix the renderer emitted a phantom `→ cycle (?)` hop
(exit 1); post-fix it trims the trailing `cycle` sentinel and appends a
` (cycle)` suffix (exit 0), e.g. `→ C (low) → A (med) (cycle)`.

Fix mirrors the cc2d4ce `self`-sentinel trim but keeps the cycle signal:
the `[cycle]` singleton still renders `(cycle)`, and non-cyclic chains
plus `self`-terminated paths are unchanged (regression-asserted in
reproduce.py). Dropped the `unverified` tag.

`goc validate` clean; plugin engine mirrors re-synced via pre-commit.

## 2026-05-27T05:50:30Z — Closure

- **What changed**: `goc/engine.py` `_format_why` — trim a trailing `cycle` sentinel (mirroring the cc2d4ce `self` trim) and append a ` (cycle)` suffix so a multi-hop cyclic WHY path renders `→ C (low) → A (med) (cycle)` instead of a phantom `→ cycle (?)` card.
- **Verification**: `reproduce.py` exits 1 pre-fix (phantom `→ cycle (?)`), 0 post-fix; `[cycle]` singleton still `(cycle)`; non-cyclic + `self` paths unchanged.
- **Audit**: PASS — no principle touched, mechanical display fix.
- **Project impact**: n/a
- **Tests**: no pytest suite; reproduce.py passes, `goc validate` clean.

## Closure verification (2026-05-27T05:50:30Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-05-27 — Closure' section

## Closure verification (2026-05-27T05:50:47Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
