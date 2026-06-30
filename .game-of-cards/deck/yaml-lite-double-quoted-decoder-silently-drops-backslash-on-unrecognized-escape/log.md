# Log

## 2026-06-30 — filed and fixed (fix-through from empty pull-card queue)

Surfaced during an audit-deck pass (the ready queue was empty). Confirmed
`_parse_double_quoted` in `goc/_vendor/yaml_lite.py` silently dropped the
backslash on any escape outside `{\n, \t, \", \\}` via a `.get(esc, esc)`
fallback, corrupting `"C:\Users"` → `C:Users`, `"a\rb"` → `arb`,
`"café"` → `cafu00e9` with no error.

**Decision (rubric-derived, gate none):** raise `ParseError` on an
unrecognized escape rather than decode the full YAML escape table. The
parser's documented posture — set by the closed sibling
`yaml-lite-flow-collection-with-trailing-content-silently-corrupts-value`
— is fail-loud on unsupported/malformed double-quoted input; this was the
lone remaining silent-corruption holdout in the escape decoder. Decoding
`\r \0 \xNN \uNNNN …` is a feature expansion beyond the lite subset and a
separate decision; out of scope here.

This decoder is NOT one of the three position scanners covered by the
meta-card
`yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting`
(`_split_flow`, `_split_key`, `_strip_comment`), so it is fixed standalone
rather than wired as an Nth instance of that family.

Fix: `goc/_vendor/yaml_lite.py` `_parse_double_quoted` now raises
`ParseError` naming the offending sequence; the four recognized escapes
decode unchanged. Regression test added in
`tests/test_yaml_lite.py::DoubleQuotedUnrecognizedEscapeTest`. Plugin
mirrors re-synced (`scripts/sync_plugin_assets.py`) and the openclaw
engine mirror re-ported. Full suite green (672 tests), `goc validate`
clean, sync `--check` and openclaw port `--check` green.
