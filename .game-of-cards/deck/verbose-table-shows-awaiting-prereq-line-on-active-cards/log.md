# Log

## 2026-06-23 — Closure

Surfaced during a queue-empty audit pass (all `human_gate: none` open
cards were impeded: one `waiting_on: external`, two deferred epics).

**Defect.** The verbose `render_table` printed
`awaiting: <prereq> (you may start)` for any non-terminal card, because
it gated only on the shared `dependency_advisory` helper's terminal
slice. The board renderer (`render_board`) applies a stricter
`status == "open"` slice for the same signal, so an `active` card with
an open `advanced_by` prereq got the table's advisory line but no `⏳`
on the board — two human-facing renderers describing the same card
differently, and a "(you may start)" call-to-action with no audience on
an already-claimed card. The closed meta-fix
`renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift`
centralized only the *terminal* gate; the board's later open-only
refinement was never mirrored into the table.

**Fix.** Gated the table's awaiting line on `t.status == "open"`
(`goc/engine.py`), mirroring the board's documented open-only slice.
The `dependency_advisory` terminal gate is untouched, so the existing
terminal-card regression keeps passing. The JSON renderer is left
as-is by design: it is a machine surface exposing the raw
`dependency_awaiting` advisory plus a separate status-gated `ready`
field, so the open-only slice is a human-renderer concern, not the
JSON contract.

**Verification.** `reproduce.py` exits 0 (table omits the advisory on
the active card, keeps it on the open card; board agrees). Extended
`tests/test_verbose_table_awaiting_liveness.py` with an active-card
case asserting table↔board agreement. Full suite: 539 tests OK.
`goc validate` clean. Plugin mirrors re-synced byte-for-byte.

finish-card audit: no rubric configured; mechanical fix (renderer
consistency / read-path display gate — no project principle bound).

## Closure verification (2026-06-23T08:58:33Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-23 — Closure' present
