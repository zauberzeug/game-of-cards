## 2026-05-26 — EMPIRICAL verdict: defect confirmed

`grep -n "human_gate_default" goc/engine.py` → appears only at the `Schema`
dataclass field (line ~373) and the `load_schema` constructor (line ~394).
Never inside `_cmd_new` or `_build_parser`. `contribution_values` is read at
the `Schema` field/constructor and in `_cmd_validate` (line ~1093), but not
on the new-card path.

`_cmd_new` reads `args.gate` and `args.contribution`, which were populated
by the hardcoded argparse defaults `--gate default="decision"` and
`--contribution default="medium" choices=["high","medium","low"]` — so the
schema gate-default was dead config.

TDD reproduction (in a throwaway copy of the repo): set
`human_gate_default: none` in `schema.yaml`, run `goc new foo-bar` with no
`--gate`. Before fix: emitted `human_gate: decision`. After fix: emits
`human_gate: none`.

## 2026-05-26 — fix

`_build_parser` now calls `load_schema()` and derives the `new` subparser's
`--gate` default from `schema.human_gate_default`, `--gate` choices from
`schema.human_gate_values`, and `--contribution` choices from
`schema.contribution_values` (default still `medium`, falling back to the
first listed value if a consuming repo drops `medium`). `uv run goc validate`
clean.

## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/engine.py:2159` (`_build_parser` loads schema), `goc/engine.py:2260-2262` (`new` subparser `--contribution` choices + `--gate` default/choices derived from schema) — schema is now the single source of truth for the new-card gate default and enums.
- **Verification**: throwaway-repo TDD — `human_gate_default: none` → `goc new` emits `human_gate: none` (was `decision`); shipped schema unchanged behavior (`decision`).
- **Audit**: PASS — invokes the project's "schema.yaml is the single source of truth for card frontmatter" principle (AGENTS.md "Code architecture").
- **Project impact**: n/a
- **Tests**: no pytest suite; `uv run goc validate` clean (exit 0).
- **Bundled with**: none

## Closure verification (2026-05-26T23:15:17Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
