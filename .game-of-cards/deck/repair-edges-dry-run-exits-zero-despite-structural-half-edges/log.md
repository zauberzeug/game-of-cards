## 2026-06-29T01:45:00Z — Closure

- **What changed**: `goc/engine.py:5346` — the `_cmd_repair_edges` dry-run branch now `sys.exit(1)` when `structural` is non-empty, mirroring the `--apply` branch's terminal guard so the read-only preview and the executor agree on the success contract.
- **Verification**: `reproduce.py` exits 0 — dry-run and `--apply` both return 1 on a deck with a structural half-edge.
- **Audit**: PASS — no principle touched, mechanical fix (field-symmetric exit-code parity between two modes of the same verb).
- **Project impact**: n/a
- **Tests**: 638 passed / 0 failed (full `unittest discover -s tests`); updated `test_repair_edges_dry_run_matches_apply_on_interacting_half_edges` to assert dry-run exit 1 (its declared intent — "matches apply"), added `test_repair_edges_dry_run_exits_nonzero_on_structural_half_edge`.
- **Bundled with**: n/a

## Closure verification (2026-06-29T01:40:15Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-29 — Closure' present
