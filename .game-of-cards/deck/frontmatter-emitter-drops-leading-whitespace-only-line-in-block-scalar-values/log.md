# Log

## 2026-06-24 — Closure (filed and fixed, fix-through)

Surfaced by an `audit-deck` hunter while the pull-card queue was empty
(every `human_gate: none` open card carried a `waiting_on` overlay).
Verified the defect with `reproduce.py` (exit 1, leading whitespace-only
lines collapsed to `""` on re-emit), then fixed it in the same session
since it was gate-free, single-site, and in loaded context.

**Root cause.** `_emit_block_field` (`goc/engine.py:287`) only emitted the
explicit indent indicator (`|2`/`|2-`) when the *first non-blank* content
line began with whitespace. A leading whitespace-only line preceding the
first non-blank line was skipped by the `first_content` selection, so the
bare indicator was kept; on re-parse the vendored parser collapses such a
line to `""` while `block_indent is None`.

**Fix.** Compute `first_idx` (index of the first non-blank line) and also
trigger the explicit indicator when any whitespace-only-but-nonempty line
precedes it. Block emission only fires for multi-line values, so single-line
scalars are unaffected.

**Verification.** `reproduce.py` exits 0; added permanent regression
`tests/test_yaml_lite.py::BlockScalarIndicatorRoundTripTest::test_leading_whitespace_only_line_survives_reemit`;
full suite green (582 tests); `scripts/sync_plugin_assets.py --check` green
after re-syncing the vendored engine into the plugin payloads; `uv run goc
validate` clean.

**Closure audit:** PASS — the fix is minimal, lands in the source-of-truth
engine, carries a TDD regression, and does not regress the two closed
block-scalar sibling cases (their cases are asserted in the same test).

## Closure verification (2026-06-24T19:43:02Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-24 — Closure' present
