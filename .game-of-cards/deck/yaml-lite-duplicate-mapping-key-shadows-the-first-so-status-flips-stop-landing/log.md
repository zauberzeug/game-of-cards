## 2026-07-31 — Closure

- **What changed**: `goc/_vendor/yaml_lite.py` — `_parse_block_mapping` and
  `_parse_flow_mapping` now `raise ParseError` on a key repeated within the same
  mapping instead of letting the later value silently overwrite the earlier one.
  The module docstring's `Unsupported (raises ParseError)` list names the case.
  No engine change: `parse_frontmatter` already wraps `ValueError` into
  `FrontmatterError`, so `goc validate` reports the card and exits 1,
  `load_card_or_exit` exits 2 with the path, `load_all_cards` warns per card.
  State repair in the same commit: the stale first of two `summary:` keys removed
  from `autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`.
- **Verification**: `reproduce.py` exits 0 (both arms raise; the over-indent
  control still raises; the reader-split demonstration is now unreachable because
  the fixture no longer parses). 11 new tests in `tests/test_yaml_lite.py` —
  `DuplicateMappingKeyRejectionTest` (7: both arms reject, and nested mappings,
  sibling sequence items and single-occurrence documents still parse),
  `DuplicateTopLevelKeyScanTest` (3: proves the deck scan catches a planted
  offender before its verdict on the real deck is trusted), and
  `DeckRoundTripTest.test_no_card_carries_a_duplicate_frontmatter_key` (1: names
  every offending card and key). Deck scan: 0 of 691 cards carry a duplicate
  top-level key; `uv run goc validate` exits 0.
- **Audit**: no rubric configured; mechanical fix. It does invoke the parser's
  own documented loud-fail posture, so recording that alignment too: the two
  branches immediately above the fix site (`curr > indent`, unrecognizable
  `key: value` line) already raise for the same stated reason: no key may be
  dropped without saying so. Duplicate-key was the last silent key-drop left in
  `_parse_block_mapping`, and the flow arm carried the identical hole.
  Fourth sibling of the tab / over-indent / colon-no-space guards, not a fourth
  instance of one root cause — the four are independent constructs with no shared
  code path to consolidate, so an umbrella meta-fix would have nothing mechanical
  to do.
- **Project impact**: A card that acquires a duplicate key now fails loud rather
  than splitting its readers three ways. Previously `goc status <title> active`
  printed `open → active`, auto-committed, and left the card `open` on every
  surface — the parallel-agent claim lock silently failing open. Consumers whose
  decks already carry the shape will see `goc validate` go red on those cards;
  the repair is to delete the shadowed copy, and `goc validate` names the key and
  the line.
- **Tests**: 873 passed / 0 failed (`uv run python -m unittest discover -s
  tests`). Plugin mirrors regenerated via `scripts/sync_plugin_assets.py`
  (3 files) so `claude-plugin/goc`, `codex-plugin/goc` and
  `openclaw-plugin/goc` stay byte-for-byte; `--check` reports in sync.
- **Bundled with**: n/a

## Closure verification (2026-07-31T05:45:27Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 7/7 ticked
- [x] log-md-closure-entry — '## 2026-07-31 — Closure' present
