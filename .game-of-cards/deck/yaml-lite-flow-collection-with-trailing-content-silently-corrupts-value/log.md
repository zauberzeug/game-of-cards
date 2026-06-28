# Log

## 2026-06-24 — filed and fixed (fix-through)

Surfaced during a `pull-card` run with an empty ready queue → `audit-deck`
hunt. Confirmed the defect by feeding `tags: [bug, api]# recategorize` and
`worker: {who: a}# note` through `parse_frontmatter`: the sequence case
produced a single phantom element `['[bug, api]# recategorize']`, the mapping
case silently dropped all pairs (`{}`).

Fix: split the paired `startswith(...) and endswith(...)` guard in both
`_parse_flow_sequence` and `_parse_flow_mapping` (`goc/_vendor/yaml_lite.py`).
A leading `[`/`{` with no matching trailing `]`/`}` now raises `ParseError`,
matching the parser's documented fail-loud posture (over-indent, missing
space after colon, tabs, folded scalars). The `not startswith` branch is kept
as a defensive fallthrough — `_parse_scalar` only dispatches to these helpers
when the text already starts with the bracket, so the live behavior change is
the new `endswith` raise.

`parse_frontmatter` wraps the parser's `ParseError` in `FrontmatterError`, so
the reproduce.py catches both at the parse boundary.

Regression test: new `FlowCollectionTrailingContentRejectionTest` in
`tests/test_yaml_lite.py` (trailing-content + mismatched-bracket rejections,
plus a well-formed-still-parses guard including nested collections and a
genuine space-preceded comment). Plugin mirrors re-synced via
`scripts/sync_plugin_assets.py`. Full suite green; `goc validate` OK.

## 2026-06-24 — Closure

All four DoD items satisfied: reproduce.py exits 0 (both malformed flow
collections now raise at the parse boundary), the new
`FlowCollectionTrailingContentRejectionTest` asserts the rejections plus a
well-formed-still-parses guard, the two flow helpers raise `ParseError` on a
leading bracket with no matching close, and `uv run goc validate` +
`uv run python -m unittest discover -s tests` are both green (578 tests).

## Closure verification (2026-06-24T19:07:30Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-06-24 — Closure' section

## Closure verification (2026-06-24T19:07:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-24 — Closure' present
