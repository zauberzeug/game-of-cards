## 2026-11-16T01:05:00Z — Parked as unverified by audit-deck

Came up while sweeping siblings for
[regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories](../regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories/),
by checking whether shipped code mishandles bare repositories as the test
fixtures do. It does, but with a different root cause: the shared worktree-deck
walk equates "parent of the common directory" with "primary working tree".
Reproduced once by hand. The commands and output are in the README's
Falsification recipe. Parked without a `reproduce.py` under the audit's
park-or-disprove rule.

- **Dedup**: 12 cards mention `worktree_deck` or `GOC_WORKTREE_DECK`, and none
  covers a bare clone or a layout without a primary working tree.

## 2026-11-18 — Verified: the hypothesis holds on today's engine

`reproduce.py` builds the Falsification-recipe layout (bare clone `repo.git`,
linked worktree `wt-feat` with its own deck and a `worktree_deck: shared`
config) and runs `goc new` then `goc --status all` from the worktree. On `main`
at `186e925b` (git 2.56.1) it exits 1:

- **Config opt-in only:** both runs exit 0 against the worktree's own deck,
  with nothing on stderr. The opt-in is dropped without a word.
- **`GOC_WORKTREE_DECK=shared`:** `goc new` exits 2 and `goc --status all`
  prints `No cards match`. Both say `no Game of Cards deck found from
  <tmp>/wt-feat upward`, a worktree that holds a deck. goc searched the folder
  holding `repo.git`.

A probe of four more layouts shows the parent of git's common directory is
not the primary working tree whenever that directory is not named `.git`:
`.bare` plus a `.git` gitfile, `--separate-git-dir`, and a submodule's
`.git/modules/<name>`. It is also wrong for a bare repository cloned as
`.git`. `git worktree list --porcelain` agrees: git derives the main worktree
by stripping `/.git` from the common directory and flags the bare ones.
Another probe found the same misleading missing-deck wording in an ordinary
clone when the primary has no deck. That message names the linked worktree,
not the primary goc searched.

## 2026-11-18T04:38:17Z — Closure

- **What changed**: `goc/engine.py:97-112` — `_primary_working_tree` counts
  the parent of git's common directory as the primary working tree only when
  that directory is a non-bare `.git`. So `_detect_worktree_common_root`
  (`:115-120`) returns None in a bare clone, and shared mode stays off there.
  `_unshareable_worktree_deck_warning` (`:153-178`) gives `cli()`
  (`:4854-4859`) a WARNING that names the ignored request and the bare
  repository. `_missing_deck_message` (`:4908-4923`) names the directory goc
  searched. The three runtime hooks carry the same check. The config template
  comment and `Skill(kickoff)` reference § Worktrees describe the layout.
- **Decision within the DoD**: refuse, not resolve. The DoD allowed either.
  No location in a bare clone is both version-controlled and shared, so shared
  mode refuses. It does so as a warning over the per-worktree default, not an
  exit, which keeps a repository that commits the opt-in usable from a bare
  clone. The README's Fix section has the reasoning.
- **Verification**: `reproduce.py` exits 1 on `186e925b` (8 failures) and 0
  after. `BareCloneHasNoPrimaryWorkingTreeTest` has 11 failures and 1 error on
  `186e925b` and passes after.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1510 passed / 0 failed / 0 xfailed
  (`uv run python -m unittest discover -s tests`). `sync_plugin_assets.py
  --check`, `port_skills_to_openclaw.py --check`, `goc validate`,
  `check_card_language.py --check` and `check_card_frontmatter_yaml.py
  --check` are all green.
- **Bundled with**: none. A reference-block note went to
  `openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution`,
  whose Option A would port the changed function.

## Closure verification (2026-11-18T04:38:19Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-11-18T04:38:17Z — Closure' present
