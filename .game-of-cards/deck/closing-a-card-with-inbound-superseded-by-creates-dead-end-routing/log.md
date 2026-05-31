## 2026-05-31T00:13:59Z — Closure

- **What changed**: `goc/engine.py` — added `_inbound_superseded_by_holders` + `_enforce_no_inbound_superseded_by_or_exit` helper near the existing `_would_create_supersedes_cycle`. Wired the enforcer into `_cmd_done`, `_cmd_done_bundle` (per-card preflight after the human-gate check), and `_cmd_status` close-into-terminal path. Regression coverage in `tests/test_close_with_inbound_superseded_by.py` exercises all four close verbs.
- **Verification**: `uv run python .game-of-cards/deck/closing-a-card-with-inbound-superseded-by-creates-dead-end-routing/reproduce.py` exits 0 (every close path now rejects with a message naming `card-a.superseded_by`); regression suite 340/340 passes; `goc validate` errors are 5 before / 5 after — identical pre-existing data drift, no new error class introduced.
- **Audit**: PASS — no principle touched, mechanical fix (close-time symmetric counterpart to an existing set-time guard).
- **Project impact**: n/a
- **Tests**: 340 passed / 0 failed / 0 xfailed

## Closure verification (2026-05-31T00:14:11Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-31 — Closure' present

## 2026-05-31 — Reversed by `goc-validate-requires-supersession-and-gate-states-no-verb-can-produce`

The close-time guard `_enforce_no_inbound_superseded_by_or_exit` (and its
helper `_inbound_superseded_by_holders`) introduced by this card were removed
entirely, along with the test `test_close_with_inbound_superseded_by.py`
(replaced by `test_close_succeeds_with_inbound_superseded_by.py`). The guard
made the successor of *every* supersession permanently un-closeable: after
`goc status A superseded --by B` (B live), `goc done B` was refused because
`A.superseded_by` still pointed at B — but B is exactly the live work the
supersession was created to track, and is meant to be completed. Landing on a
`done` successor is the *resolution* of the supersession, not a dead end (and a
`superseded` successor routes onward via its own pointer). Closing a
supersession's successor is now allowed; `A` legitimately routes forward to the
now-terminal `B`, and `goc validate` accepts the link. This was the deepest of
the three guards in the family — the others only blocked unusual inputs, while
this one broke the normal lifecycle. See the new card for the full rationale.
