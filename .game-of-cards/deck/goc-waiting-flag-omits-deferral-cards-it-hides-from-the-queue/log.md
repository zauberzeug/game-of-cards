# Log

## 2026-06-24 — filed and closed (fix-through)

Surfaced during a `pull-card` audit round (queue was empty: all open
`human_gate: none` cards carried deliberate `waiting_on` overlays).

The `--waiting` filter in `_cmd_list` kept cards on `t.waiting_on is not None`,
diverging from the canonical `waiting_impedes()` predicate used by
`card_is_ready`, `card_is_workable_for_scheduler`, the board ⏳ marker, and the
leverage line. The divergence ran both ways: a bare deferral
(`goc wait <t> --until <future>`, no `--reason`) is impeded but was omitted
from `--waiting`; an elapsed `waiting_until` (resurfaced, no longer impeded)
was still listed.

Fix: the filter now calls `waiting_impedes(t)`, so the set `--waiting` shows is
exactly the set hidden from `--ready` and painted ⏳. Help text updated to
match. No new decision — the shared predicate already existed; this call site
was the lone hand-rolled outlier.

Verified: `reproduce.py` flips FAIL → PASS; new regression test
`test_waiting_matches_impedes_predicate` in
`tests/test_waiting_filter_status_scope.py` guards both directions; full suite
(583 tests) green; `goc validate` clean; plugin mirror + OpenClaw port checks
green after `scripts/sync_plugin_assets.py`.

Noted but out of scope: the standup skill's JSON filter
(`[c for c in cards if c.get('waiting_on')]`) has the same blind spot for bare
deferrals — a downstream skill-template parallel, not the engine flag this card
fixes.
