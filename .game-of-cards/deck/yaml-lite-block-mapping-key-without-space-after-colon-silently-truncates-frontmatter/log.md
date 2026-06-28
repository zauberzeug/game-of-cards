## 2026-06-24T13:30:00Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py:128` — `_parse_block_mapping`
  now `raise`s `ParseError` (instead of silently `break`-ing) when a line at
  the mapping indent is not a recognizable `key: value` entry — covering both a
  colon with no following space (`status:open`) and a bare scalar with no colon.
- **Verification**: `reproduce.py` exits 0 (all three malformed same-indent
  shapes raise `ParseError`); 5 new tests in
  `tests/test_yaml_lite.ColonNoSpaceMappingRejectionTest` (3 reject, 2 confirm
  valid forms — `key:` empty value and `a: foo:bar` interior colon — still parse).
- **Audit**: PASS — invokes the vendored parser's documented loud-fail posture
  (`yaml_lite.py` module docstring "Unsupported (raises ParseError)"; the tab,
  over-indent, and block-scalar-header guards already raise). This closes the
  one remaining same-indent silent-truncation hole in that posture.
- **Project impact**: n/a
- **Tests**: 571 passed / 0 failed (full `unittest discover -s tests`); plugin
  mirrors regenerated via `scripts/sync_plugin_assets.py` (3 files) so
  `claude-plugin/`, `codex-plugin/`, `openclaw-plugin/` stay byte-for-byte.
- **Bundled with**: n/a

## Closure verification (2026-06-24T13:23:09Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-24 — Closure' present
