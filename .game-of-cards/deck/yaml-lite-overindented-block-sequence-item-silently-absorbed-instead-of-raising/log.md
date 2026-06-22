## 2026-06-22T19:35:38Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py:_parse_block_sequence` — added a `curr > indent` branch that raises `ParseError` instead of falling through to consume the line as a same-level item, so an over-indented block-sequence item fails loud rather than being silently absorbed. Mirrors the `_parse_block_mapping` guard added in `119cf31`.
- **Verification**: reproduce.py exits 0 (the over-indented item raises ParseError); full regression suite 523 passed / 0 failed (5 new tests in `OverIndentedSequenceRejectionTest`); `uv run goc validate` clean.
- **Audit**: PASS — no principle touched, mechanical fix (fail-loud parser guard mirroring the sibling mapping guard, the tab guard in `_peek`, and the ambiguous-indent guard in `_parse_block_scalar`).
- **Project impact**: n/a
- **Tests**: 523 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a — surfaced and fixed-through during a pull-card session whose ready queue was empty (all `human_gate: none` cards carried active `waiting_on` overlays).
