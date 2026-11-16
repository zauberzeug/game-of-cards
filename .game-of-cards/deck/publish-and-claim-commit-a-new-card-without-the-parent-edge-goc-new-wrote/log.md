## 2026-11-16T01:30:00Z — Parked as unverified by audit-deck

A hunter candidate: the audit's general-purpose subagent, briefed on the
scheduler core, reproduced it on scratch decks with both `goc publish` and
`goc status <title> active`. The auditing agent read the cited lines
(`goc/engine.py:6872`, `:6925`, `:7097-7098`, `:7116`) and reproduced the
publish path by hand. The output is in the README. Parked without a
`reproduce.py` under the audit's park-or-disprove rule.

- **Dedup**: `commit_targets`, `_git_auto_commit([card_dir]`, `half-edge`
  with publish or claim, and `explicit-pathspec` are all covered.
  [goc-new-with-advances-leaves-parent-card-mutation-uncommitted](../goc-new-with-advances-leaves-parent-card-mutation-uncommitted/)
  (done) assumed the half-edge depends on the agent's own staging. That
  closed card got a post-close amendment pointing here.

## 2026-11-16 — Verified, then fixed in `_git_auto_commit`

- **Verdict**: the hypothesis holds. `reproduce.py` on `main` at `89f16b7e`
  printed `DEFECT: 4 of 4 release paths commit a half-edge` and exited 1. The
  four paths are `--advances` and `--advanced-by`, each released by
  `goc publish` and by `goc status child-card active`. `unverified` dropped.
- **Fix shape**: widen the commit, the only one of the three listed shapes
  that meets the DoD's "no uncommitted edge counterpart" check. The widening
  lives in `_git_auto_commit`, not in the two verbs: the half-edge rule
  belongs to the commit, and `decide`/`wait`/other status flips can commit a
  card the same way.
- **Precision choices**:
  - A counterpart is taken only when its committed README lacks the edge.
    HEAD's copies come from one `git cat-file --batch` call.
  - A tracked counterpart contributes its README only, never its log.md.
  - Counterparts taken are checked in turn.
  - Drafts are never added. That keeps
    `auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft`
    open and unchanged: a copy of its reproducer with `--summary` added still
    prints its DEFECT.
- **Side observation**: that card's own `reproduce.py` now fails during setup,
  before reaching its defect. `goc publish parent-card` refuses a card with no
  `summary`, a rule added after the reproducer was written. Read by the exit
  code alone, that failure says the defect still fires.
- **After**: `reproduce.py` exits 0. 5 new tests in
  `tests/test_new_wires_edges.py`; 3 fail on `89f16b7e` (7 subtests). The two
  precision tests each catch a planted offender, one ignoring the committed
  copy and one admitting drafts.

## 2026-11-16T05:03:01Z — Closure

- **What changed**: `goc/engine.py:5807` — `_git_auto_commit` now also
  commits every edge counterpart that `_uncommitted_edge_counterparts`
  (`:5729`) finds: one whose worktree README holds the other half of an
  edge a committed card records while its committed copy, read by
  `_git_head_texts` (`:5686`), lacks it. A tracked counterpart joins with
  its README only; one HEAD lacks altogether joins whole. Counterparts
  taken are checked in turn, and drafts are never added. The docstring
  also stops listing `goc done` among the auto-committing release verbs,
  because `_cmd_done` leaves the commit to the caller.
  `Skill(create-card)` Step 4 now says the release commit carries the
  other half.
- **Verification**: `reproduce.py` exits 0, with all four release paths
  clean and validating on a fresh clone. It exited 1 with 4 of 4 failing on
  `89f16b7e`. A subdirectory deck and a repository with no commit yet
  were checked by hand.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1506 passed / 0 failed (`uv run python -m unittest discover -s tests`).
  5 new in `tests/test_new_wires_edges.py`.
- **Interactions recorded, not changed**:
  - `failed-auto-commit-leaves-card-files-staged-in-the-shared-git-index`:
    a failing commit can now leave one more file staged, the counterpart
    README.
  - `claim-push-calls-any-failed-rebase-a-claim-race-and-advises-a-reset`:
    a claim commit that carries a parent README can conflict on it during
    the push-retry rebase.
  - Both stay with their gated cards.

## Closure verification (2026-11-16T05:03:03Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-11-16T05:03:01Z — Closure' present
