## 2026-05-14 — Closure

`closed_at` now records every terminal exit (done, disproved, superseded),
not just done. `_cmd_status` (`goc/engine.py`) stamps the timestamp when
flipping to `disproved` or `superseded`; the validator collapses to a
single symmetric rule keyed on `TERMINAL_STATUSES`. The `closed_at` Card
property carries a docstring matching the new contract.

`--since` keeps its existing `--done`-only gate, so "what shipped
recently" queries are unaffected. Other `closed_at` consumers
(`retrospective` skill) already scope by `--status done`.

Backfill: `scripts/backfill_terminal_closed_at.py` reads
`git log -1 --format=%aI -- .game-of-cards/deck/<title>/README.md` for each
disproved/superseded card with a null `closed_at`, normalizes to UTC `Z`
form, and writes it back. Six existing cards in this repo's deck got
backfilled — see the commit diff for the per-card timestamps.

Skill bodies (`card-schema`, `advance-card`) updated to describe the new
semantics; `finish-card` already documents the `done` case correctly.
CLAUDE.md / AGENTS.md carry no `closed_at` references to drift.

## Closure verification (2026-05-14)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-05-14 — Closure' section

## Closure verification (2026-05-14)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-05-14 — Closure' present
