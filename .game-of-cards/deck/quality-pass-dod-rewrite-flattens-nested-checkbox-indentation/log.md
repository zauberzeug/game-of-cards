# Log

## 2026-06-21 — closed (done)

Surfaced during a pull-card audit pass (queue was all-gated). `_apply_dod_rewrite`
(`goc/engine.py:3604`) lstripped the LLM `fix` text and wrote it back at column 0,
flattening any nested `  - [ ]` sub-item that a verdict targeted — `_dod_box_indices`
counts indented boxes, so nested items are legitimate rewrite targets.

Fix: capture the original line's leading whitespace (`re.match(r"[ \t]*", lines[line_idx])`)
and re-apply it after the lstrip/prefix reconstruction. Leaves the `- [ ]` state
hardcode untouched, so the sibling decision card
[goc-quality-pass-dod-rewrite-silently-unchecks-previously-checked-items] is unaffected.

Evidence: `reproduce.py` flips FAIL→PASS. Regression test
`tests/test_dod_rewrite_preserves_indent.py` (nested item keeps indent; top-level
item stays at column 0). Full suite green (477 tests), `goc validate` OK.
