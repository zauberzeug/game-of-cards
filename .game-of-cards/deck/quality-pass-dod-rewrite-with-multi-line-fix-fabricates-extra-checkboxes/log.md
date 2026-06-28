# Log

## 2026-06-28 — closed (done)

Fixed `_apply_dod_rewrite` (`goc/engine.py:3858-3866`) so an LLM-authored
`fix` containing embedded newlines no longer fabricates extra DoD
checkboxes. A DoD item is a single line and this function replaces one
item by index; a multi-line `fix` previously survived into a single line
slot, then split into multiple physical lines on `"\n".join(lines)` /
re-emit, and any checkbox-shaped line was counted by `count_dod_boxes` /
`_dod_box_indices` as a real box — inflating the closure count (a
fabricated *open* box could later make `goc done` refuse to close a card
whose authored work was complete, and shifts the index space for
subsequent rewrites in the same batch).

Fix: collapse embedded newlines (and surrounding whitespace) to a single
space (`re.sub(r"\s*\n\s*", " ", ...)`) before the prefix/indent logic,
so a single-item rewrite stays one physical line. Existing behavior
(indent restoration, `- [ ]` prefix injection, empty-fix no-op) is
preserved.

Reachability: `fix` strings come from `_run_sonnet_quality_pass`
(`claude --model sonnet ... --output-format json` → `json.loads`), so a
multi-line `fix` is real LLM-reachable input.

- `reproduce.py`: before, 3 open boxes from a 2-item DoD; after, stays 2.
- Regression test: `tests/test_dod_rewrite_multiline_fix.py` (2 of 3
  assertions fail pre-fix, all pass post-fix).
- Plugin mirrors (`claude-plugin/`, `codex-plugin/`, `openclaw-plugin/`)
  re-synced via `scripts/sync_plugin_assets.py`.
- `uv run goc validate` exits 0; full suite (637 tests) green.

Filed and closed in the same pull-card session (fix-through).
