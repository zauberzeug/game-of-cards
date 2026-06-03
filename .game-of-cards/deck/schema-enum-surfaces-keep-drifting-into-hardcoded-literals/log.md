# Log

## 2026-06-03 — PROCESS: schema-enum literal surface inventory

Enumerated every surface in `goc/engine.py` (+ `goc/install.py`) that
re-states a `schema.yaml` enum as a literal.

**Drift-prone literals fixed (now derived from `load_schema()`):**

| Surface | Old location | Derives from |
|---|---|---|
| `STATUS_VALUES` tuple | `engine.py:1831` | `schema.status_values` |
| `STATUS_FILTER_VALUES` / `MUTABLE_STATUS_VALUES` | `engine.py:1832-1833` | derived from `STATUS_VALUES` (already) |
| `CONTRIBUTION_ORDER` dict | `engine.py:1835` | `enumerate(schema.contribution_values)` |
| `STAGE_ORDER` list | `engine.py:1836` | `schema.stage_values` (`None` → `"null"`) |
| `CONTRIBUTION_RANK` dict | `engine.py:1974` | `3.0 ** (N-1-index)` over `contribution_values` |
| `--contribution` global filter `choices` | `engine.py:2713` | `schema.contribution_values` |
| `--human-gate` global filter `choices` | `engine.py:2719` | `schema.human_gate_values` |

**Already schema-sourced (verified, no change):**

- `--status` filter `choices=list(STATUS_FILTER_VALUES)` — `engine.py:2715`
- `goc status <new_status>` `choices=list(MUTABLE_STATUS_VALUES)` — `engine.py:2798`
- `goc new --contribution` `choices=schema.contribution_values` — `engine.py:2822`
- `goc new --gate` `choices=schema.human_gate_values` — `engine.py:2825`
- `goc wait --reason` `choices=schema.waiting_on_values` — `engine.py:2856`
- `render_board` columns `= list(load_schema().status_values)` — `engine.py:2582`
- validator membership checks at `engine.py:1256-1335` — all read `schema.*`

**Exempt (NOT a schema enum):**

- `TERMINAL_STATUSES = frozenset({"done","disproved","superseded"})` —
  `engine.py:1834`. "Terminal" is a semantic subset (closure-bearing
  statuses) the schema does not declare, so it stays a literal.

`goc/install.py` re-states no enum literals (grep confirmed).

**MECHANICAL:** the module-level constants now compute once at import via
a single `_ENUM_SCHEMA = load_schema()` call. Verified byte-for-byte
identical to the prior literals for the shipped six-status /
three-contribution / four-stage enums.

**TDD:** added `tests/test_schema_enum_surface_parity.py` — 14 assertions
covering each ordering constant, every argparse `choices` surface, and the
board column list against the corresponding `schema.*` list. The family
now turns red on the first drift instead of recurring instance by instance.

Full suite green (370 tests); `goc validate` OK; plugin mirrors re-synced.

## 2026-06-03T00:00:00Z — Closure

- **What changed**: `engine.py:1828-1844` — module enum constants
  (`STATUS_VALUES`, `CONTRIBUTION_ORDER`, `STAGE_ORDER`) and
  `CONTRIBUTION_RANK` (`engine.py:1980-1986`) now derive from
  `load_schema()`; global `--contribution` / `--human-gate` filter
  `choices` (`engine.py:2719/2725`) read `schema.*`.
- **Verification**: derived constants byte-for-byte identical to prior
  literals (`STATUS_VALUES`, `CONTRIBUTION_ORDER`, `STAGE_ORDER`,
  `CONTRIBUTION_RANK` asserted equal). New parity guard adds 14
  assertions across every enum surface.
- **Audit**: PASS — invokes the schema-as-single-source-of-truth
  api-contract; no source paper, a project documented-contract closure.
- **Project impact**: n/a
- **Tests**: 370 passed / 0 failed (suite + new test_schema_enum_surface_parity)
- **Bundled with**: n/a

## Closure verification (2026-06-03T05:19:35Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-03 — Closure' present
