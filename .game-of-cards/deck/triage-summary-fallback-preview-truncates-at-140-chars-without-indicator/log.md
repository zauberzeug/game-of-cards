# Log

## 2026-06-25 — closed (done)

`goc triage`'s summary-fallback preview (`_cmd_triage`, `goc/engine.py`)
hard-cut the preview at 140 chars with a bare `[:140]` slice and printed the
fragment raw, with no clip indicator — unlike the sibling `decision_required`
branch which already advertises its clip with `… +N more lines (see goc show …)`.
A long summary was therefore truncated mid-word and masqueraded as complete.

Fix: the summary-fallback branch now detects when the preview is shortened
(first line > 140 chars, or extra lines dropped) and appends ` … (see goc show
<title>)`, matching the established convention; short single-line summaries are
printed unchanged. `reproduce.py` confirmed the defect (283-char summary cut to
140 at "laten" with no marker) and now passes. Regression test
`tests/test_triage_summary_preview_overflow.py` covers the clipped and short
cases. Plugin mirrors re-synced; full suite (586 tests) and `goc validate` green.
