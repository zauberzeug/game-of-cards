## 2026-10-08T05:14:54Z — Closure

- **What changed**: `goc/engine.py:4482` (`_cmd_default`) keeps the query's scope filters (stage, contribution, tag, advances, advanced-by, worker) in one `scope` dict. Both `run_query` and the leverage line's gated pool read from it. `goc/engine.py:4612` passes `filter_cards(cards, status=None, **scope)` to the line instead of the whole deck. `goc/engine.py:3838` (`render_leverage_line`) now takes a full-deck `by_title` for the near-term-flow tiebreak. `goc/templates/skills/pull-card/SKILL.md` now says the gated card shares the pick's scope, and the mirrors are re-synced and re-ported.
- **Scope decision** (left to the implementing agent by the filing): the gated pool honors every scope filter, not only `--worker`. The line claims that lowering a gate would change what this puller works on next. That is true only of gated cards the same query would pull once ungated. `--human-gate` stays out of the pool, because the gate is the conjunct the two halves differ on. The ACTIVE banner stays worker-only, since it is a soft-lock hint.
- **Verification**: before the fix, `reproduce.py` exited 1. `GOC_WORKER=alice goc --ready` named `bob-parked (value 9.0)`, a 9× gap. After the fix it exits 0 and names `alice-parked (value 3.0)`. A mutation check of `tests/test_leverage_line_query_scope.py` (11 tests): reverting the call site fails 8 tests; dropping `by_title` fails the tiebreak test; letting `--human-gate` into the scope fails the human-gate test. The unscoped `goc --ready` on this deck is unchanged.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1270 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`)
- **Bundled with**: none

## Closure verification (2026-10-08T05:15:03Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-08 — Closure' present
