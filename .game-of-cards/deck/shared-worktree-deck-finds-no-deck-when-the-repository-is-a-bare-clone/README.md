---
title: shared-worktree-deck-finds-no-deck-when-the-repository-is-a-bare-clone
summary: "Shared worktree-deck mode took the parent of git's common directory to be the primary working tree. A bare clone with linked worktrees, a common layout for parallel agents, has no primary working tree: that parent is just the folder holding the bare repository. With GOC_WORKTREE_DECK=shared goc searched there, reported a missing deck naming the worktree it never searched, and so routed every skill Preflight to Skill(kickoff). The worktree's own config opt-in was dropped without a word. Fixed: the parent counts as the primary only for a non-bare .git, so shared mode stays off in a bare clone, goc uses the worktree's own deck, and a WARNING names the bare repository and says the layout has no primary working tree. The missing-deck notice now names the directory goc actually searched."
status: done
stage: null
contribution: medium
created: "2026-11-16T01:01:16Z"
closed_at: "2026-11-18T04:38:22Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] EMPIRICAL: a `reproduce.py` builds the layout under Falsification recipe and prints what `goc --status all` and `goc new` do from a linked worktree with `GOC_WORKTREE_DECK=shared`, and with only the worktree's `config.yaml` opt-in. Run it on today's engine, record the verdict in log.md either way, and drop the `unverified` tag once it works. — on `186e925b` it exits 1 with eight failures: the env opt-in's `goc new` exits 2, both runs name the unsearched worktree in the missing-deck notice, and the config opt-in is dropped silently. Verdict in log.md, `unverified` dropped.
  - [x] TDD: if the hypothesis holds, `reproduce.py` exits 0 after the fix: in a bare-clone layout, shared mode either refuses with a message that names the bare repository and says the layout has no primary working tree, or resolves to a documented location. It never reports a missing deck that names a directory it did not search. — exit 0. Both opt-ins file and list the card in the worktree's own deck, print `WARNING: … <tmp>/repo.git is a bare repository, so this layout has no primary working tree …`, and print no missing-deck notice.
  - [x] TDD: a regression test in `tests/test_project_root_from_subdirectory.py` (or a sibling) pins the bare-clone case for `_detect_worktree_common_root` / `_shared_worktree_deck_root` (`goc/engine.py:53-100`), next to the primary-checkout cases already there. — the two functions now span `goc/engine.py:53-150`. `BareCloneHasNoPrimaryWorkingTreeTest` (4 tests) runs four layouts: `repo.git`, `.bare`, a bare `.git`, and `--separate-git-dir`. It covers the engine and all three hooks, both opt-ins, the CLI, and an ordinary-clone control. 11 failures and 1 error on `186e925b`, green after.
  - [x] MECHANICAL: the `worktree_deck` comment in `goc/templates/game_of_cards/config.yaml:49-54` (and the shared-deck docs it points to) says what shared mode does in a bare-clone layout. Plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green). — the comment is now at `config.yaml:49-58`, and this repo's own `.game-of-cards/config.yaml` matches it. `Skill(kickoff)` reference § Worktrees gained a bare-clone paragraph. `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` are both green.
worker: {who: "claude[bot]", where: main}
---

# Shared worktree-deck mode finds no deck when the repository is a bare clone

## What was broken

Verified on 2026-11-18 by `reproduce.py` (git 2.56.1, `main` at `186e925b`).
Shared mode found "the primary working tree" by taking the parent of git's
common directory (`_detect_worktree_common_root`). In an ordinary clone the
common directory is `<primary>/.git`, so its parent is the primary working
tree. A bare clone with linked worktrees (`git clone --bare … repo.git`, then
`git --git-dir=repo.git worktree add …`) is a common way to give each parallel
agent its own worktree. There the common directory is the bare repository.
Its parent is just the folder that holds it, with no checkout and no deck.

- **`GOC_WORKTREE_DECK=shared`:** goc looked for the deck in that folder.
  `goc new` exited 2 and `goc --status all` printed `No cards match`. Both
  said `no Game of Cards deck found from <tmp>/wt-feat upward`. That names a
  worktree that holds a deck and that goc never searched. The message carries
  `MISSING_DECK_PHRASE`, and every skill Preflight routes that phrase to
  `Skill(kickoff)`, so an agent was told to set up GoC in a repository that
  already had a deck.
- **Only `worktree_deck: shared` in the worktree's own `config.yaml`:** goc
  read the opt-in from `<folder>/.game-of-cards/config.yaml`, which does not
  exist. Shared mode stayed off without a word.

The parent rule is wrong in more layouts than this one. It fails for any
common directory not named `.git`: `.bare` behind a `.git` gitfile,
`--separate-git-dir`, and a submodule's `.git/modules/<name>`. It also fails
for a bare repository cloned as `.git`. Git's own model agrees:
`git worktree list --porcelain` derives the main worktree by stripping `/.git`
from the common directory, and it flags bare repositories.

The missing-deck wording was also wrong in an ordinary clone.
`_missing_deck_message` named `REPO_ROOT`, the linked worktree, even under the
shared redirect, where goc searched only the primary. A linked worktree
holding a deck, run with `GOC_WORKTREE_DECK=shared` against a primary
without one, got a notice naming the worktree.

## Fix

- `_primary_working_tree` (`goc/engine.py:97-112`) returns the parent of the
  common directory only for a non-bare directory named `.git`.
  `_is_bare_repository` (`:83-94`) reads `core.bare` with
  `git config --file`, so no repository discovery runs. Every other layout
  returns None. A bare clone has no primary working tree, and a git directory
  kept apart from its checkout does not sit inside it.
  `_detect_worktree_common_root` (`:115-120`) is now
  `_linked_worktree_common_dir` (`:53-80`) followed by that check. So shared
  mode stays off there, and the walk resolves the worktree's own deck, which
  is goc's per-worktree default. The three runtime hooks carry the same check
  in their mirrors and agree with the engine in every layout below.
- `_unshareable_worktree_deck_warning` (`:153-178`) turns the dropped request
  into a `WARNING:` that `cli()` prints for every deck verb (`:4854-4859`).
  The warning names what made the request: the env var, or the config file
  holding the key. In this layout that file is the worktree's own config,
  the only one there is, so the opt-in the old code never read is now read.
  The warning names the bare repository, says the layout has no primary
  working tree, and says a claim now reaches other worktrees only through a
  merge.
- `_missing_deck_message` (`:4908-4923`) names where goc looked. Under the
  shared redirect that is the primary working tree, with the advice to
  install there. Otherwise it is the walk from `REPO_ROOT` upward, as before.
- Docs: the `worktree_deck` comment in
  `goc/templates/game_of_cards/config.yaml:49-58` (and this repo's own
  `.game-of-cards/config.yaml`) and `Skill(kickoff)` reference § Worktrees
  (`goc/templates/skills/kickoff/reference.md:53-68`) say what shared mode
  does in a bare clone.

**Why refuse rather than resolve.** The DoD allowed either a refusal with a
message or a documented location. A bare clone offers no location that is
both version-controlled and shared. The folder holding the bare repository is
not a working tree, so auto-commit cannot run there. The worktree on the
default branch would move the deck whenever that worktree comes or goes. So
shared mode refuses. It does so as a warning over goc's per-worktree default,
not an exit. A repository that commits `worktree_deck: shared` for its
ordinary-clone users stays usable from a bare clone. The legacy-`deck/`
warning is the precedent for a layout that is degraded but valid.

## Evidence

- `reproduce.py` exits 1 on `186e925b` (eight failures across both opt-ins)
  and 0 after the fix. Both opt-ins then file and list the card in the
  worktree's own deck, and both print the warning naming `repo.git`.
- `tests/test_project_root_from_subdirectory.py`
  `BareCloneHasNoPrimaryWorkingTreeTest` runs four layouts: `repo.git`,
  `.bare` behind a gitfile, a bare `.git`, and `--separate-git-dir`. It pins
  `_detect_worktree_common_root` to None for the engine and all three hooks,
  and pins the engine's and the hooks' deck roots to the worktree under both
  opt-ins. It also pins the warning wording, the CLI end to end, and the
  ordinary-clone control: no warning while the shared deck applies, and a
  missing-deck notice that names the primary. All four tests fail on
  `186e925b` (11 failures, 1 error) and pass after the fix.

## Known limits

- `_is_bare_repository` reads `<common>/config` only. Under
  `extensions.worktreeConfig`, git's documented setup moves `core.bare` into
  the main worktree's `config.worktree`. The name check still catches every
  bare repository not named `.git`. Only a bare repository cloned as `.git`
  with that extension keeps the old behaviour.
- A submodule's linked worktree does have a primary working tree, recorded as
  `core.worktree` in `.git/modules/<name>/config`. goc does not follow it, so
  shared mode refuses there too. Before the fix it resolved to
  `.git/modules`, which never holds a deck.
- `goc install` and `goc upgrade` bypass `engine.cli()`, so they print no
  warning. In this layout they already target the worktree's own root.
- The OpenClaw port implements no shared mode at all
  ([openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution](../openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution/)),
  so it has nothing to mirror.

## Why it matters

A missing-deck notice that names a worktree holding a deck sends every
skill's Preflight to `Skill(kickoff)` in a repository that is already set up.
A dropped opt-in is worse, because nothing shows. Agents that expect one
shared queue then claim cards that other worktrees cannot see. The nearest
earlier cards cover the other layouts this redirect mishandled:
[shared-deck-mode-treats-primary-checkout-subdirectories-as-linked-worktrees](../shared-deck-mode-treats-primary-checkout-subdirectories-as-linked-worktrees/)
and
[goc-new-crashes-with-valueerror-when-deck-lives-in-shared-worktree-root](../goc-new-crashes-with-valueerror-when-deck-lives-in-shared-worktree-root/).
