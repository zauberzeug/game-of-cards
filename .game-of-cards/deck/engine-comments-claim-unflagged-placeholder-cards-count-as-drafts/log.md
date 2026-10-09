# log — engine-comments-claim-unflagged-placeholder-cards-count-as-drafts

## 2026-10-08T05:40:20Z — Filed

Surfaced while closing
[queue-table-renders-draft-cards-identically-to-authored-ones](../queue-table-renders-draft-cards-identically-to-authored-ones/),
which edited `card_is_draft`'s docstring and the board's draft mark.
Reading `card_is_draft` next to `is_placeholder_scaffold` showed that
two docstrings in the same file contradict each other. `git log -S` puts
both in commit `e861360e`, and that commit's message settles which one
is the design. Filed at `human_gate: none` because the flag-only rule is
already decided, so the fix is to correct the comments and nothing needs
choosing. It qualifies for fix-through in the session that found it: one
source file, with the code already loaded.

## 2026-10-09T04:37:29Z — Resumed a stale claim

Claimed 2026-10-08T05:41:56Z (commit `ee68e465`) by the fix-through leg
of Pull Card run 37732234867. That run's agent step failed at 05:45:37Z
and landed nothing after the claim. About 23 hours later, local `main`
still matched `origin/main` with a clean tree. Pull Card runs share one
concurrency group, so no live session can hold the claim. Resumed under
the same worker identity rather than left as a dead soft lock, as the
deck has done before
([citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits](../citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits/),
[kickoff-autonomy-choice-hands-off-to-host-complements-that-carry-no-recipe](../kickoff-autonomy-choice-hands-off-to-host-complements-that-carry-no-recipe/)).
`reproduce.py` still exits 1 with all five claims present.

## 2026-10-09T04:42:53Z — Closure

- **What changed**: `goc/engine.py:2764` — the `is_placeholder_scaffold`
  docstring names `goc publish` as its one consumer and says an unflagged
  placeholder scaffold is ordinary queue work. `goc/engine.py:1017` (`Card.draft`)
  and `goc/engine.py:3161` (`filter_cards`) drop their backstop claims, and
  `filter_cards` also drops the stale "board renders the full deck". The two
  fixture docstrings that repeated the claim
  (`tests/test_empty_query_result_line.py:420`, the closed zero-match card's
  `reproduce.py:68`) now give the true reason their cards are authored. The
  closed card's `log.md` carries a forward pointer here. No code changed. New
  test: `tests/test_unflagged_placeholder_scaffold_is_not_a_draft.py`.
- **Verification**: `reproduce.py` exit 1 (5 claims) → 0 (none), with the
  behavior block unchanged. The closed zero-match card's `reproduce.py` still
  exits 0. Both injected backstops turn the new test red: a placeholder
  conjunct in `card_is_draft` fails 7 of 8 tests, and one in the supersede
  guard alone fails the supersede test.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1284 passed / 0 failed / 0 xfailed
  (`uv run python -m unittest discover -s tests`; 8 new)
- **Also green**: `uv run goc validate` exit 0;
  `scripts/sync_plugin_assets.py --check` and
  `scripts/port_skills_to_openclaw.py --check` clean; card-language and
  card-frontmatter-YAML guards clean.
- **Bundled with**: none

## Closure verification (2026-10-09T04:43:00Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-10-09 — Closure' present
