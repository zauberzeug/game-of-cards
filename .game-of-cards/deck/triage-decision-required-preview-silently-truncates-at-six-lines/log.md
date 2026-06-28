# Log

## 2026-06-23 — Closure

Closed via fix-through in a `pull-card` session. The `_cmd_triage`
decision-required preview now advertises its overflow with a `… +N more
lines (see goc show <title>)` marker, matching the repo-wide capped-list
convention. Regression test added; full suite green (538 tests).

## 2026-06-23 — filed and fixed (fix-through)

Surfaced during a `pull-card` session with an empty ready queue (all
`human_gate: none` open cards carried a `waiting_on` overlay). An
audit hunter flagged the silent 6-line cap in the text-mode `goc
triage` decision-required preview.

- **Confirmed** with `reproduce.py`: an 8-line `## Decision required`
  section renders 6 lines and drops 2 with no overflow marker.
- **Fix:** after the 6-line loop in `_cmd_triage` (`engine.py`), append
  a `  > … +N more lines (see goc show <title>)` marker when the
  preview exceeds 6 lines — matching the repo-wide overflow-advertising
  idiom (`render_board`, the tag-sample renderer, `render_active_notice`,
  the validate report).
- **Regression test:** `tests/test_triage_decision_preview_overflow.py`
  — one case asserting the marker + `goc show` pointer appear on a
  long section, one asserting no marker on a 5-line section.
- Re-ran `reproduce.py` → exit 0, overflow PRESENT.
- Full suite green (538 tests). Plugin mirror trees re-synced via
  `scripts/sync_plugin_assets.py`.

finish-card audit: PASS — no principle touched, mechanical fix (matches
the established overflow-advertising display convention; no design
decision).

## Closure verification (2026-06-23T08:39:11Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [ ] log-md-closure-entry FAIL — no '## 2026-06-23 — Closure' section

## Closure verification (2026-06-23T08:39:48Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-23 — Closure' present
