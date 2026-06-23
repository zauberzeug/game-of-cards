# Log

## 2026-06-23 — filed and fixed (fix-through during empty-queue pull-card)

Surfaced by a general-purpose hunter agent during an empty-queue
`pull-card` session, then fixed through in the same session (gate-free,
single-site, context loaded).

- **Diagnosis:** `_resolve_upgrade_briefing_target` (`goc/install.py`)
  converted the advertised 1-based `Pick [1-N]` selection with
  `found[int(raw) - 1]`. Python negative indexing made `0` →
  `found[-1]` (last candidate) and negatives wrap around, so the
  `except (ValueError, IndexError)` abort branch never fired for
  out-of-range non-positive input. The picker silently selected the
  wrong briefing home and stripped the block from the others — the
  opposite of the abort contract one line below. Reachable
  non-interactively via piped `0\n` (non-TTY `sys.stdin.readline()`).
- **Fix:** bounds-check `1 <= idx <= len(found)` before indexing,
  raising `IndexError` into the existing abort branch. One function,
  one guard.
- **Tests:** added `tests/test_upgrade_briefing_target_picker.py`
  (zero / negative / out-of-range-positive abort with exit 2; in-range
  `2` → `CLAUDE.md`; empty → default `AGENTS.md`). `reproduce.py` now
  exits 0. Full suite (534 tests) green; `goc validate` clean.
- **Mirrors:** `scripts/sync_plugin_assets.py` regenerated the three
  bundled-engine copies (`claude-plugin/`, `codex-plugin/`,
  `openclaw-plugin/` `goc/install.py`).
