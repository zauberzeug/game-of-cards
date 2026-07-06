---
title: pattern-generalization-mutation-detector-matches-git-staging-by-literal-flag-tokens
summary: "The pattern-generalization Stop hook recognizes broad `git add` staging by exact-equality token matching against a flat flag set (`{-A,-p,-u,--all,--update,--patch}`). It cannot track git's argument grammar, so each new spelling needs another patch: long-form aliases (closed), pre-subcommand global options (open), and now bundled short flags (`git add -Au`) — which the prior tokenized rewrite actually REGRESSED. Architectural meta-fix: parse git's grammar once instead of enumerating flag spellings."
status: open
stage: null
contribution: high
created: "2026-06-08T04:39:38Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging
  - pattern-generalization-mutation-detector-skips-long-form-git-add-flags
  - pattern-generalization-mutation-detector-skips-pre-subcommand-git-global-options
  - pattern-generalization-mutation-detector-misses-compound-and-chained-git-commands
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: human resolves `## Decision required` — recognizer strategy chosen (grammar-aware normalization vs. argparse-style parse vs. broadened token test), recorded in log.md
  - [ ] TDD: reproduce.py exits zero — detector returns True on bundled short flags `git add -Au`, `git add -uA`, `git add -Ap`, AND on the pre-subcommand-global-option shapes (`git -c k=v commit`, `git -C /tmp commit`, `git --no-pager commit`) the open sibling enumerates
  - [ ] TDD: positive + negative baselines preserved — still True on `git commit`, `git add -A`, `git add --all`, `git add .`, `git add -A -u`; still False on `git add path/foo.py`, `git add -- foo.py`, `git status`
  - [ ] MECHANICAL: `goc/templates/hooks/pattern_generalization_check.py` `_is_broad_git_mutation` rewired per the chosen strategy; `claude-plugin/hooks/`, `codex-plugin/hooks/` mirrors and the `openclaw-plugin/index.ts` TS port updated via the sync + porter scripts
  - [ ] PROCESS: the open sibling `pattern-generalization-mutation-detector-skips-pre-subcommand-git-global-options` is superseded by (or folded into) this card if the chosen fix subsumes it; closure logged in log.md with reproduce.py before/after output
---

# pattern-generalization-mutation-detector-matches-git-staging-by-literal-flag-tokens

This is the **architectural meta-fix** for a recurring family. Three
prior cards each patched one git spelling the broad-mutation matcher
failed to recognize; this card replaces the recognition *strategy* so
the family stops generating new instances.

## Location

`goc/templates/hooks/pattern_generalization_check.py:40-70` —
`_is_broad_git_mutation`. Mirrored verbatim in
`claude-plugin/hooks/pattern_generalization_check.py`,
`codex-plugin/hooks/pattern_generalization_check.py`, and the TypeScript
port `openclaw-plugin/index.ts` (`isBroadGitMutation`).

## What's broken

The matcher tokenizes the Bash command with `shlex.split`, then tests
each token for **exact equality** against a flat set of flag spellings:

```python
# goc/templates/hooks/pattern_generalization_check.py:35-37, 64-70
_BROAD_STAGING_FLAGS = frozenset(
    {"-A", "-p", "-u", "--all", "--update", "--patch"}
)
...
    for tok in tokens[2:]:
        if tok == "--":
            return False
        if tok == "." or tok in _BROAD_STAGING_FLAGS:
            return True
    return False
```

The docstring claims this design is extensible:

> The matcher tokenizes via `shlex.split` and inspects tokens by
> equality, so future git long-form alias additions can be picked up by
> extending `_BROAD_STAGING_FLAGS` without re-deriving regex
> alternations.

That claim is false for any spelling that isn't a whole-token literal.
Git's `add` accepts **bundled short flags** — `git add -Au` is exactly
`git add -A -u` — and `-Au` never `==` any single-flag string, so it is
not in the set and slips through. Long-form aliases needed the set
extended (closed sibling); pre-subcommand global options break the
`tokens[1]`-is-the-subcommand assumption (open sibling). Each is the same
root cause: **the matcher enumerates git's surface spellings instead of
modelling git's argument grammar.**

Worse, bundled flags are a *regression*. The original matcher (before the
long-form fix) was the regex `\bgit\s+add\s+(?:-[A-Za-z]|\.)`, which
matched `git add -Au` by matching its `-A` prefix. The
[`skips-long-form-git-add-flags`](../pattern-generalization-mutation-detector-skips-long-form-git-add-flags/)
closure replaced that regex with the exact-equality token test to gain
long-form support — and silently dropped bundled-flag support in the
swap. So a turn whose only index-mutating action is `git add -Au foo/`
now bypasses the generalization self-assessment Stop hook entirely,
where it would have fired before.

## The family (this is the meta-fix)

| Card | Spelling it patched | Status |
|---|---|---|
| [fires-on-pathspec-separator-staging](../pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging/) | `git add -- <path>` false-positive (substring→regex) | done |
| [skips-long-form-git-add-flags](../pattern-generalization-mutation-detector-skips-long-form-git-add-flags/) | `--all` / `--update` / `--patch` (regex→token set) | done |
| [skips-pre-subcommand-git-global-options](../pattern-generalization-mutation-detector-skips-pre-subcommand-git-global-options/) | `git -c k=v commit`, `git -C <path> commit` (self-labelled "fourth instance", tagged meta-fix) | open (decision) |
| **this card** | bundled short flags `git add -Au`, `-uA`, `-Ap` | open (decision) |

Four shape-specific patches against one matcher means the design, not the
data, is wrong. The audit sibling-sweep rule says the Nth instance of a
known family is filed as the architectural meta-fix, not yet another
per-shape card.

## Empirical evidence

`uv run python deck/pattern-generalization-mutation-detector-matches-git-staging-by-literal-flag-tokens/reproduce.py`:

```
True   git add -A -u        (separated short flags — correctly caught)
False  git add -Au          BUG: should be True (bundled = -A -u)
False  git add -uA          BUG: should be True
False  git add -Ap          BUG: should be True (bundled = -A -p)
True   git commit -m x      (baseline)
True   git add -A           (baseline)
True   git add .            (baseline)
False  git add path/foo.py  (baseline — explicit path, correctly ignored)
False  git add -- foo.py    (baseline — pathspec separator, correctly ignored)
```

## Why it matters

The Stop hook (`pattern_generalization_check.py`) walks the live
transcript over each `Bash` tool-call command string
(`_had_code_mutation` → `_is_code_mutating` → `_is_broad_git_mutation`).
`git add -Au` ("stage all incl. deletions + untracked, update tracked")
is an everyday commit idiom an agent reaches for by reflex — no
hand-authored or synthetic input is needed, it is the production
Bash-command path. When that is a turn's only mutating action, the
generalization reminder the hook exists to inject is silently skipped, so
the agent never self-assesses whether its change is an instance of a
broader pattern. The hook's entire purpose is defeated for that turn.

This also keeps re-occurring: as long as recognition is by literal
spelling, each future git syntax an agent uses (`--end-of-options`,
`=`-attached option values, additional global options) is another
silent-bypass card waiting to be filed.

## Decision required

How should the matcher recognize broad git staging robustly, once?

1. **Grammar-aware normalization (recommended).** Skip past
   pre-subcommand global options to find the real subcommand token; for
   `add`, treat any token of the form `-<letters>` (a short cluster) as
   broad if it contains any of `A`/`u`/`p`, and keep the existing
   long-form set membership for `--`-prefixed tokens, the bare `.`, and
   the `--` pathspec-separator negative. Closes bundled short flags and
   the open pre-subcommand sibling together. Small, self-contained, no
   new dependency.
2. **argparse-style git parse.** Model git's documented global-option
   grammar and `add`'s option grammar with a parser. Most faithful, but
   heavier and itself a maintenance surface — arguably over-engineered
   for a heuristic Stop hook.
3. **Broaden the token test minimally.** De-bundle only short clusters
   (strip leading `-`, scan letters) and leave the `tokens[1]` subcommand
   assumption to the open sibling. Rejected framing — it re-splits the
   family into two fixes instead of consolidating, which is the thing
   this meta-fix exists to stop.

The decision also covers whether this card **supersedes** the open
sibling `skips-pre-subcommand-git-global-options` (option 1 subsumes it)
or merely coordinates with it.

## Fix

Do **not** apply until the decision is recorded. Whichever strategy is
chosen, update the source-of-truth hook
(`goc/templates/hooks/pattern_generalization_check.py`) and regenerate
the three mirrors via `scripts/sync_plugin_assets.py` (claude/codex) and
`scripts/port_skills_to_openclaw.py` for the `index.ts` port, then add
regression rows to `tests/test_pattern_generalization_hook.py`.
