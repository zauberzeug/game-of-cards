## 2026-09-04T04:45:04Z — Closure

- **What changed**: `goc.md:283-285` — the `goc status` row drops `blocked`
  from the offered states and marks it deprecated with a pointer to `goc wait`;
  a new `goc wait <title> --reason <r>` row plus a closing three-axis /
  migration paragraph give the page the replacement it never named.
  `tests/test_guidance_accuracy.py` — `DeprecatedStatusGuidanceTest` derives
  the deprecated set from the skill bodies ∩ `MUTABLE_STATUS_VALUES` and fails
  any guidance surface offering one unmarked.
- **Verification**: `reproduce.py` exit 0 (was 1, with 3 findings). The two
  static checks and both new guards were re-run against `git show HEAD:goc.md`:
  2 static failures and 2 guard failures, the latter quoting `goc.md:283`
  verbatim — non-vacuous. Derived deprecated set is exactly `{blocked}`.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1087 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`, exit 0)
- **Bundled with**: n/a

Scope note: filed at `contribution: high` per the audit-deck rule that a doc
claim contradicting an authoritative source is high, then right-sized to
`medium` when `goc validate` raised `BACKWARDS_EPIC_EDGE` — the card claimed
to outrank both `advances` parents and the whole `blocked`-purge family, which
are all `medium`. The heuristic was correct about the sizing, not just the
edge direction.

## Closure verification (2026-09-04T04:45:07Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-09-04 — Closure' present
