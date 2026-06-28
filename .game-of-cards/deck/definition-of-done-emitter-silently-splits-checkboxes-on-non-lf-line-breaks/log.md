## 2026-06-25 — Closure

Fixed the `definition_of_done` branch of `emit_frontmatter` (goc/engine.py)
to guard against non-LF line-break characters, matching the posture every
other multi-line field already takes. The branch now checks
`_contains_line_break(dod.replace("\n", ""))` and routes through the shared
`_yaml_inline` boundary refusal when a non-LF break (CR/VT/FF/FS/GS/RS/NEL/
U+2028/U+2029) is present, instead of silently splitting the value via
`str.splitlines()` and corrupting the checkbox count.

- TDD: `reproduce.py` exits zero (was exit 1 — silently split `\x0b` into a
  newline before the fix).
- TDD: added `test_emit_frontmatter_refuses_dod_with_non_lf_break` and
  `test_plain_lf_dod_still_block_emits_and_round_trips` to
  `tests/test_yaml_lite.py::NonLFLineBreakRefusalTest`.
- MECHANICAL: fix reuses the existing `_contains_line_break` predicate — no
  fresh char list — so it cannot drift from the parser's `str.splitlines()`.
- PROCESS: `uv run goc validate` clean (rc 0); 590 regression tests green;
  `python scripts/sync_plugin_assets.py --check` clean (engine mirrored into
  claude/codex/openclaw plugin payloads, regenerated); openclaw port `--check`
  clean.

Closure audit: no project closure-audit rubric configured (hook empty);
mechanical boundary-guard fix — field-symmetric serialization safety, no
project principle touched.

Surfaced via the pull-card queue-empty audit path (general-purpose hunter).
Fixed through in the same session: gate-free, single-site, determined by the
existing line-break policy. Advances
frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting.

## Closure verification (2026-06-25T07:46:56Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-06-25 — Closure' section

## Closure verification (2026-06-25T07:47:06Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-25 — Closure' present
