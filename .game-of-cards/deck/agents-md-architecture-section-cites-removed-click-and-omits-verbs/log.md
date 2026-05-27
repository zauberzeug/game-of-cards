## 2026-05-27T12:40:00Z — Closure

- **What changed**: `AGENTS.md:116-124` — rewrote the `goc/cli.py` bullet to describe the argparse wiring (`_build_parser`, not Click) and extended the `goc/engine.py` verb roster to the full 16, adding `wait`, `repair-edges`, `migrate`, `migrate-list-style`.
- **Verification**: `grep -rni click goc/*.py` returns nothing; `goc --help` lists 16 subcommands, all 14 engine verbs (minus install/upgrade) now appear in the architecture passage.
- **Audit**: PASS — no principle touched, mechanical doc-sync.
- **Tests**: added `AgentsArchitectureAccuracyTest` to `tests/test_guidance_accuracy.py` (3 cases: cli bullet has no Click, cli.py source has no Click, every engine verb listed). Full suite 170 passed / 0 failed.
- **Project impact**: n/a

## Closure verification (2026-05-27T13:17:59Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
