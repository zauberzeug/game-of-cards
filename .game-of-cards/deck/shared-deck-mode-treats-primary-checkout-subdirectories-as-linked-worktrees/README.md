---
title: shared-deck-mode-treats-primary-checkout-subdirectories-as-linked-worktrees
summary: "From any subdirectory of the primary checkout, git prints --git-dir as an absolute path and --git-common-dir as a relative one, and _detect_worktree_common_root compared the raw strings, so it read the primary checkout as a linked worktree. With the shared-deck opt-in on (workflow.worktree_deck or GOC_WORKTREE_DECK), deck resolution then jumped to the git top level: goc new beside a nested deck silently filed into the top-level deck, goc install in a sub-project scaffolded the top level, and a workspace deck vanished one directory below the repo's top level. The engine and both Python hook copies now compare the resolved paths, pinned by tests over the primary checkout, a linked worktree, and both symptoms."
status: done
stage: null
contribution: medium
created: "2026-10-16T04:33:56Z"
closed_at: "2026-10-16T04:42:48Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (no subdirectory of a primary checkout reads as a linked worktree, and all four symptom checks follow the walk)
  - [x] TDD: a regression test pins `_detect_worktree_common_root` in the engine and both Python hooks to None at the primary checkout's top level and in its subdirectories, and to the primary root at a linked worktree's top level and in its subdirectories
  - [x] TDD: a regression test pins the user-visible symptom with the shared-deck opt-in on: `goc new` run beside a nested deck in the primary checkout files into that nested deck, and `goc install` run in a deck-less subdirectory of the primary checkout scaffolds that directory
  - [x] MECHANICAL: the engine and both hook copies carry the same resolved-path comparison, and the plugin mirrors are regenerated (`python scripts/sync_plugin_assets.py --check` green)
  - [x] EMPIRICAL: full regression suite passes (`uv run python -m unittest discover -s tests`)
worker: {who: "claude[bot]", where: main}
---

# Shared-deck mode treats primary-checkout subdirectories as linked worktrees

## Location

- `goc/engine.py:43-70`: `_detect_worktree_common_root`, comparison at `:68`
- `goc/templates/hooks/deck_session_start.py:285-311`: the hook's mirror, comparison at `:309`
- `goc/templates/hooks/pattern_generalization_check.py:100-126`: the same mirror, comparison at `:124`

The detector's only caller is `_shared_worktree_deck_root` (`engine.py:73`), which feeds
`_resolve_project_roots` (`engine.py:107`). That function supplies `REPO_ROOT` / `DECK_ROOT`
to every verb and to `install._project_target` (`install.py:510`), so `goc install` and
`goc upgrade` use the same answer. In the hooks the caller is `_find_project_dir`.

## What was broken

Before the fix, all three copies decided the question on the text git printed:

```python
    git_dir = r_git.stdout.strip()
    common_dir = r_common.stdout.strip()
    if git_dir == common_dir:
        return None  # primary working tree, not a worktree
    common_path = Path(common_dir)
    if not common_path.is_absolute():
        common_path = (cwd / common_path).resolve()
    return common_path.parent
```

The docstring names the signal: "git rev-parse --git-common-dir differs from --git-dir
when cwd is a linked worktree". But git doesn't print the two values in the same form.
Measured with git 2.55:

| cwd | `--git-dir` | `--git-common-dir` |
|---|---|---|
| primary checkout, top level | `.git` | `.git` |
| primary checkout, `a/b` | `/…/main/.git` | `../../.git` |
| linked worktree, top level or `a/b` | `/…/main/.git/worktrees/wt` | `/…/main/.git` |
| submodule, top level or `x/y` | `/…/main/.git/modules/lib` | `/…/main/.git/modules/lib` |

In row 2 the two strings differ, although both name the same directory. The function
therefore reported a linked worktree and returned the checkout's own top level as its
"primary root". The code already knew the common dir can be relative, because it resolved
it two lines later. It just decided the comparison on the unresolved text first.

On its own the wrong answer was often harmless. When the deck sits at the git top level,
the walk from a subdirectory reaches the same root anyway. The damage started when the
shared-deck opt-in was on. `_shared_worktree_deck_root` then sent deck resolution to the
git top level from a checkout that isn't a linked worktree. The docs describe the opt-in
as applying to linked worktrees only:

> `goc/templates/game_of_cards/config.yaml:50-51`: "When set, `goc` running in any linked
> worktree resolves .game-of-cards/ from the primary working tree instead of the
> worktree's own checkout."

> `goc/templates/skills/kickoff/reference.md:55-58`: "By default each git worktree sees its
> own checkout's deck. Set `workflow.worktree_deck: shared` in `.game-of-cards/config.yaml`
> (or export `GOC_WORKTREE_DECK=shared`) to make all linked worktrees share the deck in the
> primary working tree."

Everywhere else, `_resolve_deck_root`'s docstring promises the nearest-ancestor walk.

## Evidence

Every probe in `reproduce.py` runs in a primary checkout that has no linked worktree at
all. Before the fix (exit 1):

```
1. _detect_worktree_common_root in a primary checkout (expected: None everywhere)
   from repo: --git-dir='.git' --git-common-dir='.git'
     engine                         -> None     [ok]
     deck_session_start             -> None     [ok]
     pattern_generalization_check   -> None     [ok]
   from repo/src/pkg: --git-dir='/tmp/tmp7fe0ni9x/repo/.git' --git-common-dir='../../.git'
     engine                         -> repo     [DEFECT]
     deck_session_start             -> repo     [DEFECT]
     pattern_generalization_check   -> repo     [DEFECT]
2. worktree_deck: shared in the top-level config; `goc new` run in mono/service,
   which holds its own deck: card filed into mono/.game-of-cards/deck (expected mono/service) [DEFECT]
3. GOC_WORKTREE_DECK=shared; `goc install` run in mono2/packages/foo:
   .game-of-cards/ scaffolded in ['mono2'] (expected ['mono2/packages/foo']) [DEFECT]
4. GOC_WORKTREE_DECK=shared; workspace deck in ws/, git repo ws/app has no deck:
   `goc --status all` from ws/app     lists workspace-card: True
   `goc --status all` from ws/app/src lists workspace-card: False
   top level and subdirectory agree: False [DEFECT]

defect fires in 6 check(s)
```

After the fix (exit 0), every line reads `[ok]`: the three readers return `None` from
`repo/src/pkg`, check 2 files into `mono/service/.game-of-cards/deck`, check 3 scaffolds
`mono2/packages/foo`, and in check 4 both starting points list `workspace-card`.

## Why it mattered

**The misfiling was silent.** Check 2 can be reached with nothing but first-party steps:

1. Run `goc install` in `mono/service`.
2. Run `goc install` at `mono`.
3. Uncomment the template's `worktree_deck: shared` line in the top-level config.
4. Run `goc new service-card` from `mono/service`.

The last command exited 0 and printed `created .game-of-cards/deck/service-card/`. Read
from `mono/service`, that path names the service's own deck, but the card was written to
`mono/.game-of-cards/deck/`. The printed path is relative to the redirected `REPO_ROOT`,
so even the one line of output pointed at the wrong deck.

**The env var opt-in follows the shell, not the repo.** The kickoff reference tells users
to `export GOC_WORKTREE_DECK=shared`. That setting outlives the repo it was meant for. In
any other repo whose deck isn't at the git top level, it caused two problems:

- `goc install` in a monorepo sub-project scaffolded the git top level instead of cwd
  (check 3). This broke `_project_target`'s "with no enclosing deck it is cwd" contract.
- A workspace deck above the repo showed up at the repo's top level but disappeared one
  directory down (check 4). Readers exited 0 with zero cards, which looks the same as a
  drained deck. `tests/test_subdirectory_deck_resolution.py` was written to rule out
  exactly that confusion.

**One checkout gave two answers.** In checks 2–4 the result depended on whether `goc` ran
at the git top level or one directory below it.

The two Python hooks shared the comparison, so the session-start reminder and the Stop
hook's config read followed the same wrong root.

## What changed

- `goc/engine.py:65-70`, `goc/templates/hooks/deck_session_start.py:306-311`,
  `goc/templates/hooks/pattern_generalization_check.py:121-126`: all three copies resolve
  both outputs against the directory git ran in, then compare the paths:

  ```python
      # `cwd / p` is `p` itself when git printed an absolute path.
      git_dir = (cwd / r_git.stdout.strip()).resolve()
      common_path = (cwd / r_common.stdout.strip()).resolve()
      if git_dir == common_path:
          return None  # primary working tree, not a worktree
      return common_path.parent
  ```

  `cwd / <absolute path>` is the absolute path itself, so one expression handles both
  output forms. `resolve()` also absorbs a symlinked cwd (for example a `/tmp` that is a
  symlink to `/private/tmp`). Each docstring now says the comparison is on resolved paths
  and why. The change avoids `git rev-parse --path-format=absolute`, which needs git 2.31
  or later. `rev-parse` echoes a flag it doesn't know back as an output line and still
  exits 0 (checked with `--bogus-flag=absolute`), so on older git that flag would
  silently corrupt the parse.
- `tests/test_project_root_from_subdirectory.py:343-386`, class
  `PrimaryCheckoutIsNotALinkedWorktreeTest`:
  - `test_only_a_linked_worktree_reports_a_primary_root` runs the engine and both hooks
    against real git: None at the primary checkout's top level and in `src/pkg`, and the
    primary root at a linked worktree's top level and in its `src/pkg`.
  - `test_new_beside_a_nested_deck_files_into_it_under_the_config_opt_in` covers check 2.
  - `test_install_in_a_subdirectory_scaffolds_it_under_the_env_opt_in` covers check 3.

  Run against the pre-fix tree, the three tests fail with exactly five failures: the
  `repo/src/pkg` subtest for each of the three readers, plus the two symptom tests. The
  linked-worktree subtests pass on both sides of the change.
- The plugin and dogfood mirrors were regenerated by `scripts/sync_plugin_assets.py`:
  three engine copies and four copies of each hook.

## Related

- [session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/)
  tracks hook⟷engine drift. This defect was not drift: all three copies agreed and were
  wrong together, and they still agree after the fix.
- [openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution](../openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution/)
  is about the OpenClaw port, which has no worktree probe yet. Its Option A names the
  `deck_session_start.py` block as the code to port, and that block now carries the
  resolved-path comparison.
