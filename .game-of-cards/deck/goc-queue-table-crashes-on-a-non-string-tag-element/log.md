# Log

## 2026-06-21 — Closure (fix-through sibling)

Surfaced alongside
`goc-queue-and-board-crash-on-a-non-string-contribution-value` during the
same empty-queue audit. `render_table` joins `t.tags[:4]` directly, and
the `tags` property only guarantees a list (not string elements), so a
card with `tags: [bug, 42]` crashed the queue view with `TypeError:
sequence item 1: expected str instance, int found`. Only `render_table`
renders tags — `render_board`'s cell omits them and `render_json` emits
the list as-is — so this was a single-site fix.

Fix: `",".join(str(x) for x in t.tags[:4])` at `goc/engine.py:2677`.
Validation's canonical-tag check is unaffected (it still flags the
element). Regression test `test_table_tolerates_non_string_tag_element`
added to `tests/test_board.py`. reproduce.py exits 0 after the fix, 1
before. Plugin mirrors synced byte-for-byte; suite and `goc validate`
clean.

## Closure verification (2026-06-21T19:04:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-21 — Closure' present
