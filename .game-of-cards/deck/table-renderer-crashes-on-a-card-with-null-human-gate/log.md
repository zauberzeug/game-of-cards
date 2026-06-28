## 2026-06-26T02:30:00Z — Closure

- **What changed**: `goc/engine.py:754-763` — `Card.human_gate` now coerces a
  `None`/non-string frontmatter value to a string (`"" if v is None else
  str(v)`), mirroring the `Card.status` / `Card.contribution` guards. Fixes
  `render_table` (`_display_width(None)` on the GATE cell) crashing the whole
  deck view on one card with a bare/null `human_gate:`. Completes the sibling
  sweep started by `board-and-table-renderers-crash-on-a-card-with-null-status`
  — `status` and `contribution` were coerced there; `human_gate` was the last
  un-coerced table cell (`stage` is guarded, `created` is `str()`-wrapped).
- **Verification**: reproduce.py exits 0 post-fix (`Card.human_gate == ''`,
  both table verbosities OK); was exit 1 pre-fix (both crashed with
  `TypeError: 'NoneType' object is not iterable`). New regression test
  `test_renderers_tolerate_null_human_gate` in `tests/test_board.py`.
- **Audit**: PASS — no principle touched, mechanical fix (None/non-string
  coercion at a property boundary; coerce-to-`""` preserves the
  `human_gate != "none"` readiness predicate so a malformed gate stays gated).
- **Project impact**: n/a — `goc validate` still flags the invalid raw value;
  coercion only protects the read view.
- **Tests**: 604 passed / 0 failed (plugin mirrors re-synced after the
  engine.py edit).
- **Bundled with**: n/a — surfaced and fixed-through during a pull-card
  session with an empty ready queue.
