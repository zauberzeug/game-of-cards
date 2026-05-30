---
title: mutating-verbs-leave-card-modified-on-conflicting-commit-flags
summary: "Five mutating verbs (`status`, `advance`, `unadvance`, `wait`, `decide`) write the card's README (and `decide` also writes `log.md`) BEFORE calling `_commit_override`, which `sys.exit(2)`s when both `--commit` and `--no-commit` are passed. Result: a CLI usage error corrupts on-disk card state and skips the auto-commit, so the mutation lands unattested. Fix: validate flag conflicts before any disk write."
status: open
stage: null
contribution: medium
created: "2026-05-30T10:42:40Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero (the README hash equals the pre-call hash after `goc wait <title> --reason external --commit --no-commit` exits 2)
  - [ ] TDD: equivalent assertion for `goc status`, `goc advance`, `goc unadvance`, `goc decide` — all five verbs must leave the card untouched on flag conflict
  - [ ] MECHANICAL: `_commit_override` (or an equivalent early guard) is called BEFORE the first `write_text` / `_mutate_pair` in each of `_cmd_status`, `_cmd_wait`, `_cmd_advance`, `_cmd_unadvance`, `_cmd_decide`
  - [ ] PROCESS: regression test added to `tests/` covering the flag-conflict ordering invariant for at least one verb (parametrized over the five if practical)
  - [ ] PROCESS: `uv run goc validate` passes
---

# Mutating verbs leave card modified on conflicting `--commit` / `--no-commit`

## Location

- `goc/engine.py:3432-3440` — `_commit_override` (the shared validator that `sys.exit(2)`s on conflict)
- `goc/engine.py:4012` then `:4021` — `_cmd_status` writes README, then validates
- `goc/engine.py:4366` then `:4380` — `_cmd_wait` writes README, then validates
- `goc/engine.py:4404` then `:4406` — `_cmd_advance` calls `_mutate_pair` (which writes both endpoint READMEs), then validates
- `goc/engine.py:4418` then `:4420` — `_cmd_unadvance` mirrors `_cmd_advance`
- `goc/engine.py:4588` then `:4608` then `:4611` — `_cmd_decide` writes README, then writes `log.md`, then validates

## What's broken

`_commit_override` is the canonical gatekeeper for the
`--commit` / `--no-commit` mutual exclusion:

```python
# goc/engine.py:3432-3440
def _commit_override(commit: bool, no_commit: bool) -> bool | None:
    if commit and no_commit:
        print("ERROR: pass only one of --commit / --no-commit", file=sys.stderr)
        sys.exit(2)
    if commit:
        return True
    if no_commit:
        return False
    return None
```

Every mutating verb calls it AFTER the disk has already been
mutated. Concretely in `_cmd_wait`:

```python
# goc/engine.py:4366
(card_dir / "README.md").write_text(emit_frontmatter(fm, body=body))
...
# goc/engine.py:4380
commit_policy = _commit_override(args.commit, args.no_commit)
```

When the caller passes both flags, `write_text` lands first and
then `sys.exit(2)` skips the auto-commit branch entirely. The card
ends up with its overlay (or status, or edge, or decision) mutated
on disk but no commit recording the change — exactly the half-state
that `--commit` / `--no-commit` is supposed to make explicit.

`_cmd_decide` is the worst case: it writes README *and* a
`log.md` deliberation entry before `_commit_override`, so a flag
conflict leaves two files modified.

## Empirical evidence

`reproduce.py` parametrizes the check over the four verbs whose
mutual-exclusion flags fit a no-fixture invocation (`wait`, `status`,
`advance`, `unadvance`). For each, it hashes the card's README,
runs the verb with both `--commit` and `--no-commit`, then re-hashes:

```
$ uv run python .game-of-cards/deck/mutating-verbs-leave-card-modified-on-conflicting-commit-flags/reproduce.py
[wait] FAIL: exit=2 hash_eq=False
  before=16f1fee73234 after=096adc815926
  stderr: ERROR: pass only one of --commit / --no-commit
[status] FAIL: exit=2 hash_eq=False
  before=16f1fee73234 after=23b8bdfab322
  stderr: ERROR: pass only one of --commit / --no-commit
[advance] FAIL: exit=2 hash_eq=False
  before=16f1fee73234 after=b481260aa07b
  stderr: ERROR: pass only one of --commit / --no-commit
[unadvance] FAIL: exit=2 hash_eq=False
  before=b481260aa07b after=16f1fee73234
  stderr: ERROR: pass only one of --commit / --no-commit
$ echo $?
1
```

Exit 2 confirms `_commit_override` did emit the conflict error; the
non-equal hashes confirm the card was already written to disk before
the error was raised. `decide` is omitted from the reproducer
(requires a gate ≠ none plus `--decision` / `--because` arguments)
but shares the same ordering — its body documents the file:line.

## Why it matters

The repo documents `--commit` / `--no-commit` as the explicit
contract for callers that want a CLI mutation to *also* commit the
files it touches (so a parallel-agent worker doesn't sweep
unrelated staged changes into someone else's commit — see the
`Parallel-Agent Commit Safety` section of `AGENTS.md` and the
recently-closed `deck-auto-commit-sweeps-unrelated-staged-files-into-card-commits`).
The flag-conflict path silently violates that contract: the user
asked for a clear yes/no on the commit, got an argparse-style
error, and is left with a modified working tree they didn't intend
to produce. In an autonomous-pull context where the verb is called
from a skill body and the agent moves on after a non-zero exit, the
modified card sits unstaged and unattested until the next
`git status` review surfaces it.

**Reachability path**: every shipping caller of these five verbs.
`Skill(advance-card)`, `Skill(decide-card)`, and `Skill(finish-card)`
all call `goc status`, `goc advance`, `goc wait`, and `goc decide`
from autonomous skill bodies. A typo (`--commit --no-commit` in a
skill body, a hook-script that conditionally appends one of them,
or an operator habit) reaches this path on the next pull.

## Fix

Move the validation ahead of the first mutation in each verb.

Cheapest fix: introduce `_validate_commit_flags(commit, no_commit)`
that does only the conflict check and `sys.exit(2)` — same body as
the first three lines of `_commit_override` — and call it at the
top of each verb (right after argparse arg unpacking, before any
`load_all_cards()` / `_mutate_pair` / `write_text`). The existing
`_commit_override` still returns the resolved policy at the
auto-commit site.

Alternative: re-order the existing call. Move
`commit_policy = _commit_override(...)` to the top of each verb,
before any mutation. The downside is that `_cmd_decide` and
`_cmd_status` have intermediate validations (cycle checks,
schema-lookup errors) that already exit before the mutation; the
re-order is fine but the dedicated early-guard pattern is more
legible.

Recommended: the dedicated `_validate_commit_flags` early guard,
with the existing `_commit_override` left untouched for the late
auto-commit-policy decode (so changes are localized).

Sibling sweep: grep for any other verb that calls `_commit_override`
or directly re-implements the flag-conflict check. Today's
inventory is `_cmd_status`, `_cmd_wait`, `_cmd_advance`,
`_cmd_unadvance`, `_cmd_decide`. `_cmd_new` accepts `--commit` /
`--no-commit` too — confirm whether its ordering is correct
during the fix.
