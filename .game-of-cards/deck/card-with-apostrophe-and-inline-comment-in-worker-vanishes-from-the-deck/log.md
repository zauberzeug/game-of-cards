# log — card-with-apostrophe-and-inline-comment-in-worker-vanishes-from-the-deck

## 2026-07-26T10:07:24Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py:575` — `_strip_comment`'s
  flow arm now enters quote-mode only at a `_FLOW_NODE_START` position,
  the same gate `_split_flow` already carried; the node-start tuple moved
  to a module-level constant (`yaml_lite.py:452`) so the two scanners read
  it from one place. Mirrored into the three plugin payloads by
  `scripts/sync_plugin_assets.py`.
- **Verification**: `reproduce.py` exits 0 (was 1, `failures: 2`) — the
  defect case now returns `{'who': "o'connor", 'where': 'main'}`, matching
  the no-comment control, and all six regression guards hold.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 778 passed / 0 failed / 0 xfailed
  (`uv run python -m unittest discover -s tests`); `uv run goc validate`
  clean; `python scripts/sync_plugin_assets.py --check` green.
- **Bundled with**: n/a

Surfaced by an `audit-deck` round after the ready queue drained empty, and
fixed through in the same session. Filed as instance #7 of
`yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting`
and wired to it with an `advances` edge; that generalization still owns the
shared-stepping-primitive refactor, which is what would prevent arm #8.

One un-gated arm was deliberately left alone: `_split_key`
(`yaml_lite.py:508`) rejects a mapping key containing an apostrophe, but has
no reachable path in `goc` (frontmatter keys are schema-fixed identifiers,
block-sequence items are title slugs). Recorded in the card body's
"Out of scope" section as one more arm for the generalization to cover
rather than filed as its own card.

## Closure verification (2026-07-26T10:07:53Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-26 — Closure' present
