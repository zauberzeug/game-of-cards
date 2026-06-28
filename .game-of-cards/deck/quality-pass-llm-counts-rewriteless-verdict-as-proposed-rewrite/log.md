# Log

## 2026-06-21 — fixed and closed

`_render_verdict` (`goc/engine.py`) set `has_rewrite = True` for any
title/summary verdict whose `ok` was falsy, ignoring whether a `rewrite`
string was supplied. The apply path `_apply_verdict_interactive` guards on
`not ok and rewrite`, so the two disagreed: a `{"ok": false}` verdict with no
`rewrite` was counted toward `rewrite_count` ("N with proposed rewrites") and
printed a bogus `title:/summary: REWRITE … proposed: ?` line, while the apply
path offered nothing.

**Before** (reproduce.py): `has_rewrite=True`, REWRITE lines printed,
`proposed: ?` printed, apply offered nothing → over-count fires.

**After**: gated both REWRITE branches on a truthy `rewrite` string, mirroring
the apply-side guard; a rewriteless `ok: false` verdict now prints
`flagged, no rewrite offered — <reason>` and does not set `has_rewrite`.
`has_rewrite=False`, no REWRITE/`proposed: ?` lines → count realigns with the
apply path. reproduce.py inverted to assert the fixed behavior (exits 0).

Regression test `tests/test_render_verdict_rewrite_count.py` added: confirmed
it fails against pre-fix engine (`AssertionError: True is not false`) and
passes after. Full suite: 481 tests OK. Plugin mirrors re-synced via
`scripts/sync_plugin_assets.py` (engine.py copied into claude/codex/openclaw
payloads).
