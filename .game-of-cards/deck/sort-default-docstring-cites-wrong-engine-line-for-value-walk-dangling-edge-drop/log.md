# Log

## 2026-06-24 — closed (done)

`sort_default`'s docstring cross-referenced "the value walk's dangling-edge
drop at engine.py:1739", but line 1739 had drifted to sit inside
`_would_create_advance_cycle` (cycle detection). The value walk's actual
dangling-edge prune lives in `compute_values`'s nested `value_for`
(then at engine.py:2382).

Fix: replaced the hardcoded line number with a symbol reference —
"in `compute_values`'s `value_for`" — so the citation cannot rot again as
surrounding code shifts. Added `DocstringCitationAccuracyTest` to
`tests/test_guidance_accuracy.py` to guard against any future hardcoded
`engine.py:NNNN` citation in `sort_default.__doc__`. Synced the three plugin
engine mirrors (claude/codex/openclaw) via `scripts/sync_plugin_assets.py`.

`reproduce.py`: FAIL → OK. Full suite (573 tests) green; `goc validate` clean.
