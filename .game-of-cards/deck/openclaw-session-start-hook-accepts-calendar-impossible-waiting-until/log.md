# Log

## 2026-06-05 — Closure

Surfaced during a queue-empty audit pass (the ready queue held only
`waiting_on`-overlaid and aggregation-epic cards). The OpenClaw TS port's
`parseWaitingUntil` (`openclaw-plugin/index.ts`) parsed `waiting_until` with
JS `Date.parse`, which silently rolls a calendar-impossible-but-ISO-shaped
date (`2026-02-30` → `2026-03-02`) forward instead of rejecting it. The Python
engine rejects such values via `_is_iso_date` (real-calendar parse) and keeps
the card impeded through the `until_unparseable` backstop, so the port drifted
from the engine for this whole input class — re-announcing a deferred card as
resumable at session start when the rolled date lands in the past.

This is the TS-port sibling of the closed engine fix
[validate-accepts-calendar-impossible-dates-that-un-defer-cards](../validate-accepts-calendar-impossible-dates-that-un-defer-cards/).

### Fix

`parseWaitingUntil` now round-trips the parsed UTC `Y-M-D` against the input's
date prefix and returns `null` on mismatch, matching the engine's strict
calendar check. `index.ts` is hand-maintained (NOT auto-synced), so it is
edited directly.

### Verification

- `reproduce.py` (extracts production `parseWaitingUntil`/`isImpeded`, runs
  under Node, compares against the engine): FAIL → PASS, all 5 cells agree
  post-fix.
- Added three calendar-impossible cases to
  `tests/test_openclaw_session_start_hook.py`; the matrix test passes.
- Full suite: 392 tests OK. `python scripts/sync_plugin_assets.py --check` OK
  (index.ts is not a mirror). `uv run goc validate` exit 0.

No project-specific closure rubric applies (the finish-card hook is empty).
Mechanical correctness fix — align a TS port with its Python source contract.

## Closure verification (2026-06-05T05:18:06Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-05 — Closure' present
