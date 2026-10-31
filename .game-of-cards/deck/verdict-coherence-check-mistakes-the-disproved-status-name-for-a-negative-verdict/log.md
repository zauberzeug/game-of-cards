## 2026-10-31T04:35:49Z — Closure

- **What changed**:
  - `goc/engine.py` — `RESCOPE_MARKERS_RE` drops `instead of`, and `no longer` now counts only before a verdict word (`holds`, `stands`, `true`, `valid`, `correct`, `refuted`, `disproved`, `disproven`, `unviable`).
  - New `_names_rather_than_asserts`, read through `negative_verdict` / `rescope_marker`, skips a match that only names something. Any token is skipped inside an inline code span, joined by an underscore, or as one part of a slug of three or more parts. A token equal to a `STATUS_VALUES` entry is also skipped in a status list, after a status cue, or when it qualifies a card or a status noun.
  - `validate_decision_verdict_coherence`, `_rescope_reconciliation_notice` and `_cmd_decide` read through the helpers.
  - `goc/templates/skills/decide-card/reference.md` § Re-scope reconciliation lists the narrowed markers and says status names never need rewording. Mirrors were synced and the OpenClaw skills re-ported.
  - Tests: 7 new cases in `tests/test_validate_decision_contradicts_verdict.py`, 5 subprocess and 2 in-process tables. 2 new cases in `tests/test_decide_rescope_reconciliation.py`.
- **Verification**:
  - `reproduce.py` exits 0. Against the pre-fix engine (temporary worktree at b5d96fe9) the new tests fail: 6 failures, plus 30 errors in the helper tables because the helpers did not exist yet. The true-positive guards pass before and after.
  - Replaying the 2026-10-22 `decide:` commits through the pre-fix regexes finds exactly the five cards the card describes: the terminal-status-guard hub (38e4cdb0) and its four children. Each pairs a status-list summary with "no longer refuses", and 413a2026 reworded that to quiet the check.
  - Deck-wide (823 cards), 37 of 43 verdict-token spans only name a status, and all 37 are now skipped. The 6 kept are the five real verdicts on `disproved` cards and one prose "now-refuted" on a done card.
  - `goc validate` exits 0 with no `DECISION_CONTRADICTS_VERDICT`.
- **Design notes**:
  - The status-name rules apply only to tokens that are themselves status values, read from the schema-derived `STATUS_VALUES`, so no status literal is restated.
  - The code and identifier rules apply to every token, which also quiets `superseded_by`, `status:superseded` and card-slug noise on the decision side.
  - A verdict spelled with the status word ("DISPROVED: …", "Verdict: DISPROVED", "was disproved by the benchmark") matches no rule and still warns.
  - Residue: a status name with no list, cue or noun beside it ("keeps blocking superseded") still reads as a marker. It matters only next to a real negative verdict on the same card.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1453 passed / 0 failed / 0 xfailed
- **Bundled with**: none

## Closure verification (2026-10-31T04:36:01Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-31 — Closure' present
