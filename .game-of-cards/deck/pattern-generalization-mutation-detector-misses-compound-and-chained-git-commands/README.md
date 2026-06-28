---
title: pattern-generalization-mutation-detector-misses-compound-and-chained-git-commands
summary: "The pattern-generalization Stop hook's `_is_broad_git_mutation` requires `tokens[0] == \"git\"`, so it only fires when the git invocation is the literal first word of the Bash command. Compound/chained/subshell/env-prefixed commands — `cd sub && git commit`, `git add f && git commit`, `echo done; git commit`, `GIT_EDITOR=true git commit` — push `git` off token 0, so the hook silently never fires on a turn that committed code. A distinct axis (shell command structure) from the open recognizer-strategy meta-fix (git argument grammar)."
status: open
stage: null
contribution: medium
created: "2026-06-10T04:55:11Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: human resolves `## Decision required` — choose the decomposition scope (token-list split vs quote-aware raw split) and whether this is folded into the open recognizer meta-fix or fixed standalone; record in log.md
  - [ ] TDD: reproduce.py exits zero — detector returns True on `cd sub && git commit`, `git add f && git commit`, `false || git commit`, `( cd repo && git commit )`, `GIT_EDITOR=true git commit`, `cd build && git add -A`
  - [ ] TDD: positive + negative baselines preserved — still True on `git commit`, `git add -A`, `git add .`, `git commit -m "a|b"` (pipe inside quotes); still False on `git status`, `git add foo.py`, `git add -- foo.py`, `ls && pwd`
  - [ ] MECHANICAL: `goc/templates/hooks/pattern_generalization_check.py` `_is_broad_git_mutation` rewired per the chosen scope; `claude-plugin/hooks/`, `codex-plugin/hooks/` mirrors and the `openclaw-plugin/index.ts` TS port (`isBroadGitMutation`) updated via the sync + porter scripts
  - [ ] PROCESS: `tests/test_pattern_generalization_hook.py` adds regression rows for the compound/chained/subshell/env-prefix shapes; closure logged in log.md with reproduce.py before/after output
---

# pattern-generalization-mutation-detector-misses-compound-and-chained-git-commands

## Location

`goc/templates/hooks/pattern_generalization_check.py:40-70` —
`_is_broad_git_mutation`. Mirrored byte-for-byte in
`claude-plugin/hooks/pattern_generalization_check.py` and
`codex-plugin/hooks/pattern_generalization_check.py`, and ported to
TypeScript in `openclaw-plugin/index.ts` (`isBroadGitMutation`, the
`tokens[0] !== "git"` guard).

## What's broken

The detector tokenizes the whole Bash command and then requires `git`
to be the **literal first token**:

```python
# goc/templates/hooks/pattern_generalization_check.py:54-59
try:
    tokens = shlex.split(cmd, comments=False, posix=True)
except ValueError:
    return False
if len(tokens) < 2 or tokens[0] != "git":
    return False
```

That holds only when the command is a single git invocation. Agents
routinely chain a `cd` or a staging step before the commit, or prefix
an env var — and this repo's own AGENTS.md commit guidance prescribes
multi-step staging (`git add <path>...` then `git commit -- <path>...`).
In all of these, `git` is no longer `tokens[0]`, so the Stop hook
silently never fires and the pattern-generalization self-assessment is
skipped on a turn that actually committed code.

## Empirical evidence

`reproduce.py` against the current code:

```
Compound/chained commands the detector SHOULD fire on:
  False <-MISS  'cd subdir && git commit -m x'
  False <-MISS  'git add foo.py && git commit -m x'
  False <-MISS  'false || git commit -m x'
  False <-MISS  '( cd repo && git commit -m x )'
  False <-MISS  'GIT_EDITOR=true git commit'
  False <-MISS  'cd build && git add -A'

Baseline positives (must stay True):
  True   'git commit -m x'
  True   'git add -A'
  True   'git add .'
  True   'git commit -m "a|b"'

Baseline negatives (must stay False):
  False  'git status'
  False  'git add foo.py'
  False  'git add -- foo.py'
  False  'ls && pwd'

FAIL: 6 missed mutation(s); 0 false-positive(s); 0 regressed baseline(s).
```

## Why it matters — reachability

The hook reads the assistant turn's Bash `tool_use` blocks
(`_is_code_mutating` → `_is_broad_git_mutation`, lines 134-146). The
input is the raw `command` string the model passed to the Bash tool, so
any committing turn that wrote `cd x && git commit ...` or staged then
committed in one Bash call reaches this guard and is silently dropped.
The hook's entire purpose is to nudge generalization-card filing after
code lands; a detector that misses the most common commit idiom
under-fires exactly when it is most needed.

## Distinct from the open recognizer meta-fix

This is **not** subsumed by
[pattern-generalization-mutation-detector-matches-git-staging-by-literal-flag-tokens](../pattern-generalization-mutation-detector-matches-git-staging-by-literal-flag-tokens/)
nor by
[pattern-generalization-mutation-detector-skips-pre-subcommand-git-global-options](../pattern-generalization-mutation-detector-skips-pre-subcommand-git-global-options/).
Those address git's **argument grammar** (flag spellings, bundled short
flags, pre-subcommand global options) — and in every one of their DoD
baselines `git` is still `tokens[0]`. This card is a different root
cause: **shell command structure** — the command is not a single simple
command at all. Even a perfect git-grammar parser would still fail
`cd x && git commit` unless the command is first decomposed into
simple-command segments. So the two axes compose; neither fix delivers
the other.

## Decision required

Two scope questions, coupled:

1. **Decomposition depth.** `shlex.split` (which correctly respects
   quotes) yields `&&`, `||`, `&`, `(`, `)` as standalone tokens when
   space-surrounded, and keeps env-assignment prefixes (`GIT_EDITOR=true`)
   as leading tokens — so a **token-list split** on shell-operator
   tokens + leading-`VAR=` stripping catches all six reproduce cases
   without re-parsing the raw string (and without the quote-regression
   a naive raw-string split would introduce, e.g. breaking
   `git commit -m "a|b"`). It does **not** catch unspaced `;`
   (`echo hi;git commit` — shlex glues `hi;`) or newline-joined commands
   (shlex treats `\n` as whitespace). A **quote-aware raw split** (mask
   quoted regions, then split on operators including unspaced `;` and
   newlines) catches those too, at higher complexity.
   - **Option A (recommended): token-list split + env-prefix strip.**
     Covers the realistic idioms (`&&`/`||`/`&`/subshell, env-prefix),
     regression-safe, ~15 lines. Note the unspaced-`;`/newline gap in a
     comment + log.md as a known limitation.
   - **Option B: quote-aware raw split.** Full coverage; more code and a
     hand-rolled quote scanner — note the existing
     `yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting`
     meta-fix warning before adding another quote scanner.

2. **Standalone vs folded.** This is arguably the 4th instance of the
   "recognizer keeps missing git invocation shapes" family that the
   open high-contribution meta-fix
   (`...matches-git-staging-by-literal-flag-tokens`) governs. Decide
   whether to (a) fix this independently now (the shell-structure axis
   is orthogonal to that card's flag-grammar scope), or (b) fold it into
   the meta-fix so the recognizer is rebuilt once across both axes. If
   (a), wire no edge but cross-reference; if (b), supersede this card or
   add it to the meta-fix DoD.

## Fix (proposed, pending decision — do NOT apply yet)

Under Option A, split the shlex token list into simple-command segments
on a small set of shell-operator tokens and run the existing per-segment
logic (env-prefix stripped) on each:

```python
_SHELL_OPERATOR_TOKENS = frozenset({"&&", "||", ";", "|", "&"})
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

def _is_broad_git_mutation(cmd: str) -> bool:
    try:
        tokens = shlex.split(cmd, comments=False, posix=True)
    except ValueError:
        return False
    segment: list[str] = []
    for tok in tokens:
        if tok in _SHELL_OPERATOR_TOKENS:
            if _segment_is_broad_git_mutation(segment):
                return True
            segment = []
        elif tok in ("(", ")"):
            # subshell boundary — start a fresh simple command
            if _segment_is_broad_git_mutation(segment):
                return True
            segment = []
        else:
            segment.append(tok)
    return _segment_is_broad_git_mutation(segment)
```

where `_segment_is_broad_git_mutation` strips leading `VAR=` tokens then
runs the existing `tokens[0] == "git"` / `commit` / broad-`add` checks.
