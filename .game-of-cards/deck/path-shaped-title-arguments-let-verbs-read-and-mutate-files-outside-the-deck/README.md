---
title: path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck
status: done
stage: null
contribution: high
created: "2026-07-09T02:03:25Z"
closed_at: "2026-07-09T02:18:49Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: "FIXED: every verb now resolves its title argument through a shared `resolve_card_dir` helper that refuses path-shaped titles (absolute, `../`, any multi-part path) with exit 2 before any read or write; previously the bare `DECK_DIR / title` join let such titles read and MUTATE files outside the deck, then crash the auto-commit path with an unhandled ValueError after the write."
definition_of_done: |
  - [x] TDD: reproduce.py exits non-zero (defect no longer fires) — `goc show`/`goc wait`/`goc done` with an absolute or `../`-relative title refuse with a clear error before any read or write
  - [x] TDD: a shared title-resolution helper rejects any title whose resolved card dir is not strictly inside `DECK_DIR`, and every verb that currently inlines `DECK_DIR / title` goes through it (new/move keep their existing richer slug validation)
  - [x] TDD: regression test covers at least one read verb (`show`), one overlay verb (`wait`), and one closure verb (`done`) with absolute and `../` titles
  - [x] MECHANICAL: no remaining bare `DECK_DIR / title` resolution of a user-supplied title outside the helper (grep-verified)
worker: {who: "claude[bot]", where: main}
---

# path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck

> Resolved: `resolve_card_dir` (goc/engine.py, next to `load_card_or_exit`)
> now guards every title-argument resolution; path-shaped titles exit 2
> before any read or write.

## Location

`goc/engine.py` — pre-fix, every verb that took a `<title>` argument
resolved it blindly (line numbers as filed):

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

## What was broken

No verb checked that `DECK_DIR / title` stays inside `DECK_DIR`. Per
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

`uv run python .game-of-cards/deck/path-shaped-title-arguments-let-verbs-read-and-mutate-files-outside-the-deck/reproduce.py`
(post-fix, exit 1 = defect no longer fires):

```
goc show <abs-path-outside-deck>: exit 2 (refused)
goc wait <abs-path-outside-deck>: exit 2 (foreign file mutated: False; unhandled ValueError after the write: False)
goc new <abs-path>: exit 2 (refused (guard exists only at creation))
defect no longer fires (fixed)
```

Pre-fix, the same script confirmed the escape: `show` read the foreign
file (exit 0) and `wait` mutated its frontmatter, then crashed with the
unhandled `ValueError` in `_git_auto_commit` after the write.

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

## Fix (applied)

One shared helper, `resolve_card_dir(title)` in `goc/engine.py` (directly
after `load_card_or_exit`), refuses with exit 2 when the title has more
than one path component (`len(Path(title).parts) != 1`), is `..`, or when
the resolved `(DECK_DIR / title)` is not a direct child of the resolved
`DECK_DIR` (symlink belt-and-braces). It returns the unresolved
`DECK_DIR / title` join so downstream `relative_to` behavior is unchanged.

Every user-supplied title resolution routes through it: `done` (single +
`--bundle`), `attest`, `status` (title + `--by` successor + commit
targets), `publish`, `new` (after its richer slug/antipattern guard, plus
edge-endpoint commit targets), `_mutate_pair` (covering `advance`,
`unadvance`, supersession, and `new` edge wiring), the
advance/unadvance `_git_auto_commit` endpoint joins, `wait`, `move`
(both `old_title` — previously a rename-a-foreign-dir-into-the-deck
vector — and `new_title`), `decide`, and `show`. Rejecting at resolution
time makes the `_git_auto_commit` `ValueError` crash unreachable.

Remaining bare `DECK_DIR /` joins are deck-internal only (loaded-card
titles, post-`goc move` quality-pass rewrite targets, half-edge repair
titles that must already exist as loaded cards) — none argv-supplied.
Regression test: `tests/test_title_resolution_containment.py`.
