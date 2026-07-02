## 2026-07-02T02:10:00Z — Closure

- **What changed**: `goc/engine.py:915` (`load_card`) — coerce the title
  with `fm.get("title") or card_dir.name` instead of `fm.get("title",
  card_dir.name)`, so a bare `title:` (parses to `None`, key present) falls
  back to the dir name instead of yielding `Card.title == None`. This makes
  `title` the fourth member of the status/contribution/human_gate
  renderer-coercion family (matching comment added inline). Mirrors regenerated
  into the three plugin trees via `scripts/sync_plugin_assets.py`.
- **Verification**: reproduce.py exits 0 (was crashing `render_table` /
  `render_board` with `TypeError: 'NoneType' object is not iterable`).
  `Card.title` now returns `'card-with-empty-title'`. New regression test
  `tests/test_empty_title_renderer_coercion.py` (3 cases) confirms coercion,
  crash-free rendering of both table and board, AND that `goc validate` still
  flags the malformed title from the raw `fm["title"]`.
- **Audit**: PASS — no principle touched, mechanical fix (renderer-robustness
  coercion; validate contract preserved unchanged).
- **Project impact**: n/a
- **Tests**: 685 passed / 0 failed (full `unittest discover -s tests`); `goc
  validate` exit 0.
- **Bundled with**: none

## Closure verification (2026-07-02T02:01:12Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-02 — Closure' present
