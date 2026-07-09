---
title: path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck
status: open
stage: null
contribution: high
created: "2026-07-09T02:03:25Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
draft: true
summary: "Every verb except new/move resolves its title argument as `DECK_DIR / title` with no containment check, so an absolute or ../-relative 'title' reads and MUTATES files outside the deck; the auto-commit path then crashes with an unhandled ValueError after the write, leaving the mutation uncommitted."
definition_of_done: |
  - [ ] TDD: reproduce.py exits non-zero (defect no longer fires) — `goc show`/`goc wait`/`goc done` with an absolute or `../`-relative title refuse with a clear error before any read or write
  - [ ] TDD: a shared title-resolution helper rejects any title whose resolved card dir is not strictly inside `DECK_DIR`, and every verb that currently inlines `DECK_DIR / title` goes through it (new/move keep their existing richer slug validation)
  - [ ] TDD: regression test covers at least one read verb (`show`), one overlay verb (`wait`), and one closure verb (`done`) with absolute and `../` titles
  - [ ] MECHANICAL: no remaining bare `DECK_DIR / title` resolution of a user-supplied title outside the helper (grep-verified)
---

# path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck

## Location

`goc/engine.py` — every verb that takes a `<title>` argument resolves it
blindly:

- `engine.py:4178` (`_cmd_done`), `engine.py:4254`, `engine.py:4984`,
  `engine.py:5173` (`_cmd_status`), `engine.py:5262`, `engine.py:5383`,
  `engine.py:5633` (`_cmd_wait`), `engine.py:5951` (`_cmd_decide`),
  `engine.py:6094` (`_cmd_show`), plus the edge endpoints at
  `engine.py:5716` / `engine.py:5731` — all of the form:

  ```python
  card_dir = DECK_DIR / title
  ```

- Downstream crash site: `engine.py:4384` in `_git_auto_commit`:

  ```python
  str(p.relative_to(DECK_ROOT))
  ```

## What's broken

No verb checks that `DECK_DIR / title` stays inside `DECK_DIR`. Per
pathlib semantics, joining an **absolute** path replaces `DECK_DIR`
entirely (`DECK_DIR / "/tmp/x"` == `/tmp/x`), and a `../`-relative
title walks out of the tree. Only the creation verbs validate: `goc
new` and `goc move` run the slug/antipattern guard and refuse
path-shaped titles (exit 2). Every other verb — `show`, `wait`,
`status`, `done`, `decide`, `attest`, `advance`, … — accepts the same
string and operates on whatever file it lands on.

Consequences, in increasing severity:

1. **Read escape** — `goc show /some/abs/path` dumps any
   README.md-bearing directory on the filesystem.
2. **Write escape** — `goc wait <outside-path> --reason external`
   rewrites the foreign `README.md` frontmatter in place;
   `goc done <outside-path>` (DoD permitting) stamps `status: done` +
   `closed_at` on it. The engine mutates files that belong to no deck.
3. **Broken atomicity after the write** — with `workflow.auto_commit:
   true`, `_git_auto_commit` calls `p.relative_to(DECK_ROOT)` on the
   escaped path and raises an unhandled `ValueError` *after* the
   frontmatter write has landed, so the mutation exists on disk but
   the documented mutate+commit atomic step is torn, and the user gets
   a raw traceback instead of an error message.

## Empirical evidence

`uv run python .game-of-cards/deck/path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck/reproduce.py`:

```
goc show <abs-path-outside-deck>: exit 0 (read the foreign file)
goc wait <abs-path-outside-deck>: exit 1 (foreign file mutated: True; unhandled ValueError after the write: True)
goc new <abs-path>: exit 2 (refused (guard exists only at creation))
DEFECT CONFIRMED: title arguments resolve outside DECK_DIR; mutation lands on the foreign file, then auto-commit crashes.
```

## Why it matters

Reachability is mundane, not adversarial: agents drive `goc` with
programmatic title arguments, and in multi-repo or multi-worktree
setups an agent that copy-pastes a card *path* (tab-completion,
`deck/<title>` from another checkout, a stale absolute path from a
transcript) instead of a bare title silently edits the other tree's
card — or any unrelated directory that happens to contain a
`README.md` with frontmatter-ish content. The failure is worst in the
auto-commit configuration this repo itself dogfoods: the foreign file
is mutated, nothing is committed, and the verb dies with a traceback,
which violates both the "engine never mutates outside the deck"
expectation and the mutate+commit atomicity that `_git_auto_commit`
exists to provide.

## Fix

Add one shared resolution helper in `goc/engine.py`, e.g.:

```python
def resolve_card_dir(title: str) -> Path:
    card_dir = (DECK_DIR / title).resolve()
    if card_dir.parent != DECK_DIR.resolve() or not TITLE_RE.match(title):
        print(f"ERROR: invalid card title {title!r}", file=sys.stderr)
        sys.exit(2)
    return card_dir
```

and route every `card_dir = DECK_DIR / title` site (and the
`_git_auto_commit` endpoint joins at `engine.py:5716`/`5731`) through
it. Rejecting at resolution time keeps the fix single-site and makes
the `_git_auto_commit` crash unreachable; `new`/`move` keep their
existing richer antipattern guard.
