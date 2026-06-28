## 2026-06-23T19:48:27Z — Closure

- **What changed**: `goc/engine.py` — `parse_closed_since` now wraps the
  `base - timedelta(hours=hours)` construction in `try/except OverflowError`,
  emitting `goc: error: --closed-since: window too large` and `sys.exit(2)`,
  matching the sibling invalid-input branches (`0h`, `abc`).
- **Verification**: `reproduce.py` exits 0 —
  `parse_closed_since("99999999999w")` now raises `SystemExit(2)` with a clean
  diagnostic instead of an uncaught `OverflowError` traceback. Regression test
  `tests/test_closed_since_window_bounds.py` asserts exit 2 + message on the
  oversized window, and that `24h`/`7d`/`2w` and absolute `YYYY-MM-DD` dates
  still parse.
- **Project impact**: `goc/engine.py` mirrored into all three plugin payloads
  via `sync_plugin_assets.py`; `goc validate` clean; full `unittest` suite green.
