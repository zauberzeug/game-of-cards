## 2026-05-26T21:07:25Z — Closure

- **What changed**: `goc/engine.py` — added `detect_supersedes_cycles`
  (validator, mirror of `detect_advance_cycles`) and
  `_would_create_supersedes_cycle` (construction guard); wired the
  validator into `_cmd_validate` and the guard into `_cmd_status` so a
  `--by` supersession that would close a `superseded_by` loop exits 2
  before any disk write; corrected the false-premise comment in
  `_repair_edge_cycle_problem` and extended it to guard supersession
  half-edges. reproduce.py updated to call the new validator.
- **Verification**: reproduce.py exits 0 (was 1); validator reports
  `aaa: superseded_by: cycle detected through bbb → aaa` on the mutual
  pair and the symmetric error; 3-cycle (a→b→c→a) also flagged; live
  CLI `goc status bbb-card superseded --by aaa-card` rejected with exit
  2 after `aaa-card superseded --by bbb-card`; legitimate linear chain
  a→b→c supersession accepted; `uv run goc validate` clean on this
  repo's deck (no false positives).
- **Audit**: PASS — no project rubric configured (hook empty); the fix
  invokes the deck's record-axis referential-integrity contract
  (AGENTS.md: "a reader landing on a `superseded` card can be routed
  forward without parsing prose").
- **Project impact**: n/a
- **Tests**: no pytest suite for this path; `goc validate` + reproduce.py
  are the verification gate.

## Closure verification (2026-05-26T21:07:47Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
