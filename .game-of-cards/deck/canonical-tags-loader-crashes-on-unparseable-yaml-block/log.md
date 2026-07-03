# Log

## 2026-07-03 — filed and fixed (fix-through)

Surfaced by a `pull-card` audit round: the ready queue was empty (the
three open `human_gate: none` cards all carry a `waiting_on` overlay), so
the skill's queue-empty path invoked an audit hunt, which found this
sibling of the closed canonical-tags shape-guard family.

**Root cause.** `_load_consuming_repo_tags` (`goc/engine.py:646`) called
`yaml.safe_load(match.group(1))` on every fenced YAML block in the
user-owned `canonical-tags.md` without a `try/except`. The vendored
`yaml_lite` parser raises `ParseError` (a `ValueError`) on YAML features
it doesn't support (folded `>` scalars, anchors/aliases/tags, tab
indentation). Because `load_schema()` runs `_load_consuming_repo_tags()`
at module import time (`_ENUM_SCHEMA = load_schema()`, engine.py:2239),
the exception propagated out of `import goc.engine` and crashed *every*
goc command.

**Why it was the lone gap.** The recent hardening added the
`isinstance(block, dict)` shape guard and the non-string element filter,
but not the parse guard. The sibling loaders all already wrap their
`safe_load`: `load_deck_config` (engine.py:4660-4663 — whose own comment
claims parity with `_load_consuming_repo_tags`), `parse_frontmatter`
(engine.py:169), and `_resolve_deck_root` (engine.py:88). This card
completes the family — every user-facing `safe_load` callsite is now
guarded.

**Fix.** Wrapped the `safe_load` in `try/except Exception: continue`,
mirroring `load_deck_config`. A malformed block is skipped silently while
well-formed sibling blocks still contribute their tags.

**Verification.**
- `reproduce.py`: exit 1 before the fix (ParseError), exit 0 after
  (malformed block skipped, well-formed sibling still contributes
  `real-tag`).
- Two new regression tests in
  `tests/test_consuming_repo_tags_loader.py`
  (`test_unparseable_block_is_skipped_not_raised`,
  `test_unparseable_block_does_not_poison_valid_block`) pass.
- Full suite: 692 tests OK.
- `goc validate`: no FAIL/ERROR.
- Plugin mirrors re-synced (`scripts/sync_plugin_assets.py`); parity
  check green.
