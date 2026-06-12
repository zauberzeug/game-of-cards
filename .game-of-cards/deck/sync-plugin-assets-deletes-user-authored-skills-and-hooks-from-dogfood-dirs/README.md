---
title: sync-plugin-assets-deletes-user-authored-skills-and-hooks-from-dogfood-dirs
summary: "The pre-commit sync's dst-only prune deletes ANY file under `.claude/skills/`, `.claude/hooks/`, and `.codex/skills/` that has no template source — including user-authored skills/hooks GoC never owned — then crashes with `git add` exit 128 when the destroyed file was untracked, so the data is gone before the hook even fails. Contradicts the engine's own ownership contract (`_sync_skill_tree`: non-eligible dirs \"must never delete\")."
status: open
stage: null
contribution: high
created: "2026-06-12T05:19:44Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: ownership policy for the dogfood mirror dirs decided and recorded (see Decision required).
  - [ ] TDD: reproduce.py exits zero (user-authored skill + hook survive a sync run, or are rejected up-front per the chosen policy — never silently destroyed).
  - [ ] TDD: regression test — `main()` never passes a nonexistent untracked path to `git add` (no exit-128 crash path remains).
  - [ ] MECHANICAL: AGENTS.md "extend-asset-sync" section states the chosen ownership rule for `.claude/skills/`, `.claude/hooks/`, `.codex/skills/` and the escape hatch for repo-local extras.
---

# sync-plugin-assets-deletes-user-authored-skills-and-hooks-from-dogfood-dirs

## Location

- `scripts/sync_plugin_assets.py:270-272` — the dst-only prune inside `_sync_dir`
- `scripts/sync_plugin_assets.py:171-198` — the dogfood pairs it applies to (`.claude/skills/` with only `_goc-bootstrap.sh` preserved; `.claude/hooks/` with an empty `preserve_files`)
- `scripts/sync_plugin_assets.py:377` — same prune shape in `_sync_codex_skill_tree` for `.codex/skills/` (`rel.parts[0] not in eligible` unlinks non-GoC names)
- `scripts/sync_plugin_assets.py:575` — `subprocess.run(["git", "add", "--"] + rel, check=True, ...)` stages the deletions and crashes on untracked ones

## What's broken

`_sync_dir` removes every dst file without a matching src path:

```python
            if not (src / rel).exists():
                item.unlink()
                changed.append(item)
```

Applied to the dogfood pairs (`goc/templates/skills → .claude/skills`,
`goc/templates/hooks → .claude/hooks`), this deletes any file GoC does
not ship — including a contributor's own repo-local skill or hook. The
engine's consumer-facing contract for the very same directory says the
opposite (`goc/install.py:1186-1188`, `_sync_skill_tree` docstring):

> Non-eligible directories are left untouched — `.claude/skills/` may hold
> user-owned skills (or skills from other tools) that GoC does not own and
> must never delete as a side effect of upgrade.

and `goc/engine.py` (`validate_skill_dir_parity`): "Extras (user-added
skills) are allowed and not reported."

Compounding it, `main()` then stages the carnage:

```python
        subprocess.run(["git", "add", "--"] + rel, check=True, cwd=ROOT)
```

For a deleted file that was **untracked** (the normal state of a skill a
contributor just wrote), the pathspec matches nothing, `git add` exits
128 (`fatal: pathspec ... did not match any files`), and the pre-commit
hook dies — *after* the unrecoverable deletion. If the user file was
previously committed, there is no crash: the deletion is silently
auto-staged into the contributor's unrelated commit.

## Empirical evidence

`uv run python .game-of-cards/deck/sync-plugin-assets-deletes-user-authored-skills-and-hooks-from-dogfood-dirs/reproduce.py`
(runs in a throwaway clone; HEAD = ae6826f):

```
sync script exit code: 1 (expected 0)
    File "/usr/lib/python3.12/subprocess.py", line 571, in run
      raise CalledProcessError(retcode, process.args,
  subprocess.CalledProcessError: Command '['git', 'add', '--', '.claude/skills/my-deploy-helper/SKILL.md', '.claude/hooks/my_custom_hook.py']' returned non-zero exit status 128.
FAIL user skill DELETED by sync: .claude/skills/my-deploy-helper/SKILL.md (contract: user-authored files are not GoC-owned and must never be deleted)
FAIL user hook DELETED by sync: .claude/hooks/my_custom_hook.py (contract: user-authored files are not GoC-owned and must never be deleted)

3 defect signal(s) — sync prunes user-authored files.
```

## Why it matters

Reachability: the script runs as the `sync-plugin-assets` pre-commit
hook on **every commit in this repo**. Any contributor who drops a
repo-local skill into `.claude/skills/` (a pattern the engine contract
and `validate_skill_dir_parity` explicitly bless for consumer repos)
loses it on their next commit — destroyed first, crash second, so the
content is unrecoverable from git. `--check` mode (CI) likewise flags
the user's own skill as drift, turning a blessed layout into a red
build. The dst-only prune was added deliberately by
[sync-plugin-assets-leaves-orphaned-hook-files-and-check-passes](../sync-plugin-assets-leaves-orphaned-hook-files-and-check-passes/)
(commit ae6826f) to remove *retired GoC templates*; user-authored files
were collateral the orphan card never considered. The engine-side
sibling of this bug was already fixed once on the upgrade path
([goc-upgrade-clobbers-non-goc-skills-and-validate-fails-in-plugin-mode](../goc-upgrade-clobbers-non-goc-skills-and-validate-fails-in-plugin-mode/))
via the eligible-set; the repo's own sync script kept the pre-fix
behavior.

## Decision required

How should the dogfood mirror dirs distinguish "retired GoC template
to prune" from "user-authored file to preserve"? The two goals
conflict: a name absent from `goc/templates/` is exactly what both a
retired template AND a user extra look like.

1. **Declare this repo's dogfood dirs GoC-owned (recommended).**
   Document in AGENTS.md that in *this source repo* `.claude/skills/`,
   `.claude/hooks/`, and `.codex/skills/` hold only the GoC mirrors;
   repo-local extras must be added to the pair's `preserve_files` set
   (the mechanism already exists — `_goc-bootstrap.sh` uses it).
   Keep the full prune (preserves ae6826f's orphan guarantee), and fix
   the staging crash by skipping deleted-untracked paths in `main()`
   so the hook fails loudly *without* a 128 mid-stage. Cheapest;
   leaves the consumer contract (engine paths) untouched.
2. **Tracked-only prune.** Only unlink a dst-only file when git tracks
   it (presumption: it was committed by a previous sync). Protects
   untracked WIP and removes the crash, but a *committed* user skill
   is still deleted — the contract violation shrinks, not disappears.
3. **Eligible-set preserve (engine parity).** Never prune names
   outside the current template set, matching `_sync_skill_tree`'s
   contract. Retired templates then linger forever in the dogfood
   dirs — regresses the orphan bug ae6826f just closed.

Option 1 keeps both guarantees with one documented escape hatch;
options 2-3 each give up one of them.
