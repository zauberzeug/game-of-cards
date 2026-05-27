## 2026-05-27T06:03:11Z — Closure

- **What changed**: `goc/engine.py:3399` — the `advanced-by-closed` closure check now tests `not in TERMINAL_STATUSES` instead of `!= "done"`, so the closure gate, `dependency_blockers`, and the scheduler prune all agree on the resolved set. Success message softened `"all N done"` → `"all N closed"`.
- **Verification**: `reproduce.py` exits 0 (superseded/disproved upstreams now pass, matching `dependency_blockers`); new `tests/test_closure_gate_terminal_prereqs.py` asserts done/superseded/disproved pass and open/active still fail.
- **Audit**: PASS — invokes "the deck is both a scheduler and a record" (AGENTS.md); aligns the gate's code to the already-documented contract (card-schema SKILL.md:524 says "non-terminal"), removing the nudge toward record-destroying `goc unadvance`.
- **Project impact**: n/a
- **Tests**: 2 passed / 0 failed / 0 xfailed (new regression test); `goc validate` clean; plugin-asset sync `--check` green.

## Closure verification (2026-05-27T06:03:21Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
