# log — queue-table-renders-draft-cards-identically-to-authored-ones

## 2026-10-08T05:37:59Z — Closure

- **What changed**: `goc/engine.py:3530` — `render_table` suffixes a
  draft's TITLE cell with the new `DRAFT_MARKER` (`:2799`, `✎`) at every
  verbosity; `goc/engine.py:3781` — the board's mark keys on
  `card_is_draft` alone (the `live` gate dropped), so table, board and
  the JSON `draft` field mark the same cards. `card-schema/SKILL.md`,
  `card-schema/reference.md` and `create-card/reference.md` name the
  table mark.
- **Verification**: `reproduce.py` exited 1 before the fix, with all 3
  verbosities identical once titles are masked, and exits 0 after.
  `tests/test_queue_table_draft_marker.py` has 6 tests. Five injected
  offenders were run against them: the pre-fix engine, the board's
  `live` gate restored, `not_ready` ignoring the draft mark, the mark
  only at `-v`+, and the mark appended outside the padded cell. Every
  offender failed at least one test, and the fixed engine passed all 6.
- **Audit**: PASS — no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1276 passed / 0 failed; `uv run goc validate` exits 0
  (pre-existing warnings only). The mirror and OpenClaw port `--check`
  runs are clean.

**Hypothesis confirmed.** The filing audit left the card UNVERIFIED with
a falsification recipe. The reproducer used a stricter version of that
recipe: two cards identical in every rendered field except the `draft`
flag. A `goc new` placeholder would differ at `-vv` through its stub DoD
text, which is incidental content rather than a draft signal.

**Board gate.** Dropping `live` from the board's draft mark changes only
a terminal card still flagged `draft: true`. `goc validate` rejects that
state, but `--done` hides such a card as a draft, and JSON already
reported it. `not_ready` was `live and not (live and draft)` before and
is `live and not draft` now, so `⏳` is unchanged for every card. A test
pins that a live gated draft still shows `✎` instead of `⏳`.

**First full-suite run had one failure; the rerun was green.** That
first run overlapped with the rewrite of this card's README, and its
failure details were cut off by the output tail. The rerun on the final
tree ran 1276 tests with 0 failures, and the deck-scanning suites
(frontmatter YAML, card language, skill size, mirror parity) were green
when run on their own.

## Closure verification (2026-10-08T05:38:16Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-08 — Closure' present
