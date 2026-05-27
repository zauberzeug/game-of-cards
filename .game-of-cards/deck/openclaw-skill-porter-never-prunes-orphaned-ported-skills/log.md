## 2026-05-27T00:00:00Z — Closure

- **What changed**: `scripts/port_skills_to_openclaw.py` — added `_expected_dst_names()` + `_orphaned_ported_dirs()`; `drifted_skills()` now appends orphans, `main()` `shutil.rmtree`s them after the re-port. Both passes are destination-aware, mirroring `sync_plugin_assets.py`'s dst-only handling.
- **Verification**: `reproduce.py` exits 0 — synthetic orphan is flagged by `drifted_skills()` and pruned by a full re-port.
- **Audit**: PASS — no project rubric configured (`.game-of-cards/hooks/finish-card.md` empty); mechanical fix making the porter symmetric with the existing engine-tree sync.
- **Project impact**: n/a
- **Tests**: `tests/test_plugin_mirror_parity.py` 12 passed; `port_skills_to_openclaw.py --check` green; `sync_plugin_assets.py --check` green; `goc validate` clean.

## Closure verification (2026-05-27T03:55:15Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
