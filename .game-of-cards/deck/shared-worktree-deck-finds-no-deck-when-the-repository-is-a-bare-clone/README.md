---
title: shared-worktree-deck-finds-no-deck-when-the-repository-is-a-bare-clone
summary: "Shared worktree-deck mode assumes the parent of git's common directory is the primary working tree. In a bare clone with linked worktrees, a common layout for parallel agents, that parent is just the folder holding the bare repository. With GOC_WORKTREE_DECK=shared, goc then looks for the deck there and reports that no deck exists, naming the worktree it did not search, even when the worktree holds one, and every skill preflight routes that message to Skill(kickoff). The config-file opt-in is never read in this layout."
status: active
stage: null
contribution: medium
created: "2026-11-16T01:01:16Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] EMPIRICAL: a `reproduce.py` builds the layout under Falsification recipe and prints what `goc --status all` and `goc new` do from a linked worktree with `GOC_WORKTREE_DECK=shared`, and with only the worktree's `config.yaml` opt-in. Run it on today's engine, record the verdict in log.md either way, and drop the `unverified` tag once it works.
  - [ ] TDD: if the hypothesis holds, `reproduce.py` exits 0 after the fix: in a bare-clone layout, shared mode either refuses with a message that names the bare repository and says the layout has no primary working tree, or resolves to a documented location. It never reports a missing deck that names a directory it did not search.
  - [ ] TDD: a regression test in `tests/test_project_root_from_subdirectory.py` (or a sibling) pins the bare-clone case for `_detect_worktree_common_root` / `_shared_worktree_deck_root` (`goc/engine.py:53-100`), next to the primary-checkout cases already there.
  - [ ] MECHANICAL: the `worktree_deck` comment in `goc/templates/game_of_cards/config.yaml:49-54` (and the shared-deck docs it points to) says what shared mode does in a bare-clone layout. Plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green).
worker: {who: "claude[bot]", where: main}
---

# Shared worktree-deck mode finds no deck when the repository is a bare clone

Parked as `unverified`. It was reproduced once by hand during an audit-deck
run, but there is no `reproduce.py` yet. The commands and their output are
below.

## Hypothesis

Shared mode finds "the primary working tree" by taking the parent directory
of git's common directory (`goc/engine.py:53-80`):

```python
def _detect_worktree_common_root(cwd: Path) -> Path | None:
    """Return primary working tree root if cwd is inside a git worktree, else None.

    Signal: git rev-parse --git-common-dir differs from --git-dir when cwd is
    a linked worktree; the common dir is then the primary .git directory.
    ...
    if git_dir == common_path:
        return None  # primary working tree, not a worktree
    return common_path.parent
```

In an ordinary clone the common directory is `<primary>/.git`, so its parent
is the primary working tree. In a bare clone with linked worktrees
(`git clone --bare … repo.git`, then `git --git-dir=repo.git worktree add …`)
the common directory is the bare repository. Its parent is just the folder
that holds it, with no checkout and no deck. That layout gives each parallel
agent its own worktree with no checkout privileged over the others.

`_shared_worktree_deck_root` (`goc/engine.py:83-100`) then:

- with `GOC_WORKTREE_DECK=shared` set, returns that folder as the deck root.
  goc looks for `.game-of-cards/deck/` there, finds none, and prints the
  missing-deck notice. `_missing_deck_message` (`goc/engine.py:4822-4829`)
  names `REPO_ROOT`, the worktree's own top level, as the place it searched.
  So the message says no deck exists "from" a worktree that holds one.
- with only the documented `config.yaml` opt-in, reads
  `<that folder>/.game-of-cards/config.yaml` (`:92`), which does not exist.
  The opt-in a worktree carries in its own `config.yaml` is never read, and
  shared mode silently stays off.

The config template promises a primary working tree that this layout does not
have (`goc/templates/game_of_cards/config.yaml:49-54`):

```yaml
  # worktree_deck: shared   # uncomment to share a single deck across all git
  #                         # worktrees of this repo. When set, `goc` running
  #                         # in any linked worktree resolves .game-of-cards/
  #                         # from the primary working tree instead of the
  #                         # worktree's own checkout. Also available as the
  #                         # GOC_WORKTREE_DECK=shared environment variable.
```

## Why it matters

The missing-deck notice carries `MISSING_DECK_PHRASE`
(`goc/engine.py:4819`). Every GoC skill's Preflight matches that phrase and
sends the agent to `Skill(kickoff)`. An agent in such a worktree is therefore
told to set up GoC in a repository that already has a deck.

## Falsification recipe

Run on 2026-11-16 with git 2.56 against `main` at `ada1d2e7`; `goc` is the
repo's `.venv/bin/goc`:

```bash
mkdir -p /tmp/wtprobe/src && cd /tmp/wtprobe/src && git init -q -b main \
  && echo x > f && git add f && git -c user.name=a -c user.email=a@b commit -qm init
cd /tmp/wtprobe && git clone -q --bare src repo.git
git --git-dir=repo.git worktree add -q -b feat wt-feat main
cd wt-feat && mkdir -p .game-of-cards/deck \
  && printf 'workflow:\n  worktree_deck: shared\n' > .game-of-cards/config.yaml
git rev-parse --git-dir --git-common-dir
goc --status all                          # config opt-in only
GOC_WORKTREE_DECK=shared goc --status all
```

Observed:

```
/tmp/wtprobe/repo.git/worktrees/wt-feat
/tmp/wtprobe/repo.git
No cards match (status: all).
goc: no Game of Cards deck found from /tmp/wtprobe/wt-feat upward (no such file or directory: .game-of-cards/deck/). Run `goc install` at the intended project root first (agents: invoke Skill(kickoff)).
No cards match (status: all).
```

The hypothesis is falsified if, with the env var set, goc resolves a deck
that exists, or refuses with a message about the bare layout. It also fails
if the worktree's own `config.yaml` opt-in takes effect.

## Why deferred

This audit run filed
[regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories](../regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories/)
as its card. This one came up during that card's sibling sweep for git
behavior around bare repositories. Its root cause is different, and there was
no budget for a `reproduce.py`. The fix also has to pick a behavior for a
layout with no primary working tree. One option refuses shared mode with a
clear message, the smallest change. The other picks a documented location,
such as the worktree on the default branch. Nearest closed cards, neither
about this layout:
[shared-deck-mode-treats-primary-checkout-subdirectories-as-linked-worktrees](../shared-deck-mode-treats-primary-checkout-subdirectories-as-linked-worktrees/)
and
[goc-new-crashes-with-valueerror-when-deck-lives-in-shared-worktree-root](../goc-new-crashes-with-valueerror-when-deck-lives-in-shared-worktree-root/).

Surfaced by: the audit-deck run's own hunting (main agent), not a hunter
subagent.
