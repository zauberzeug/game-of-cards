---
title: pattern-generalization-mutation-detector-skips-pre-subcommand-git-global-options
summary: "After the substring -> shlex.split rewrite, the mutation detector at goc/templates/hooks/pattern_generalization_check.py:58-62 assumes tokens[1] is the subcommand. Pre-subcommand git global options (-c key=val, -C <path>, --no-pager, --git-dir=<path>, -P) push the real subcommand to tokens[2+], so 'git -c gpg.sign=false commit -m foo', 'git --no-pager commit ...', and 'git -C /tmp commit ...' silently bypass the broad-mutation detector and the pattern-generalization Stop hook never fires. Fourth instance in the same matcher-derivation family — directly contradicts the 'tokenized parser closes the meta-fix loop' claim recorded on closed sibling skips-long-form-git-add-flags."
status: open
stage: null
contribution: medium
created: "2026-05-31T04:19:38Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (detector returns True on synthetic transcripts whose only Bash call is one of the six pre-subcommand-global-option git invocations enumerated below)
  - [ ] TDD: the same script still returns True on the bare baselines `git commit`, `git add -A`, `git add .`, and still returns False on `git add path/to/file`, `git add -- foo.py`, and `git status` (positive + negative baselines preserved)
  - [ ] MECHANICAL: `goc/templates/hooks/pattern_generalization_check.py` rewires `_is_broad_git_mutation` to skip past pre-subcommand global options before inspecting the subcommand token (decision required: see body); `claude-plugin/hooks/`, `codex-plugin/hooks/`, and `openclaw-plugin/index.ts` mirror updated via the sync + porter scripts
  - [ ] PROCESS: `tests/test_pattern_generalization_hook.py` adds regression rows for the six pre-subcommand-global-option shapes
  - [ ] PROCESS: closure logged in log.md with the reproduce.py before/after output
---

# pattern-generalization-mutation-detector-skips-pre-subcommand-git-global-options

## Location

`goc/templates/hooks/pattern_generalization_check.py:40-70` —
`_is_broad_git_mutation`.

## What's broken

After the
[`skips-long-form-git-add-flags`](../pattern-generalization-mutation-detector-skips-long-form-git-add-flags/)
closure replaced the substring/regex matcher with a tokenized
`shlex.split` parser (commit `8a4c87a`, 2026-05-30), the detector
reads tokens positionally:

```python
# goc/templates/hooks/pattern_generalization_check.py:54-70
try:
    tokens = shlex.split(cmd, comments=False, posix=True)
except ValueError:
    return False
if len(tokens) < 2 or tokens[0] != "git":
    return False
if tokens[1] == "commit":
    return True
if tokens[1] != "add":
    return False
for tok in tokens[2:]:
    if tok == "--":
        # Pathspec separator: explicit paths follow, not broad staging.
        return False
    if tok == "." or tok in _BROAD_STAGING_FLAGS:
        return True
return False
```

The function assumes `tokens[1]` is always the subcommand. But
`git(1)` documents **pre-subcommand global options** — flags that
sit *between* `git` and the subcommand:

> `git [-v | --version] [-h | --help] [-C <path>] [-c <name>=<value>]
> [--exec-path[=<path>]] [--html-path] [--man-path] [--info-path]
> [-p | --paginate | -P | --no-pager] [--no-replace-objects]
> [--bare] [--git-dir=<path>] [--work-tree=<path>]
> [--namespace=<name>] [--super-prefix=<path>]
> [--config-env=<name>=<envvar>] <command> [<args>]`
>
> — `git --help`

Every such option pushes the real subcommand to `tokens[2]` or
later, so the matcher hits `tokens[1] != "commit"` and `tokens[1]
!= "add"` and returns `False` on shapes that are unambiguously
broad index mutations.

## Empirical evidence

`uv run python deck/pattern-generalization-mutation-detector-skips-pre-subcommand-git-global-options/reproduce.py`
calls `_is_broad_git_mutation` on every shape directly:

```
command                                           expected  actual    verdict
----------------------------------------------------------------------------
'git -c gpg.sign=false commit -m foo'             True      False     DEFECT
'git -c commit.gpgsign=false commit -m foo'       True      False     DEFECT
'git --no-pager commit -m foo'                    True      False     DEFECT
'git -C /tmp/worktree commit -m foo'              True      False     DEFECT
'git --git-dir=/foo commit -m foo'                True      False     DEFECT
'git -P commit -m foo'                            True      False     DEFECT
'git commit -m foo'                               True      True      ok
'git add -A'                                      True      True      ok
'git add .'                                       True      True      ok
'git add path/to/file'                            False     False     ok
'git add -- foo.py'                               False     False     ok
'git status'                                      False     False     ok

6 defect row(s) — exit 1
```

Six DEFECT rows. The positive baseline (bare `git commit`, broad
staging) and the negative baseline (explicit-path staging,
`git status`) are preserved by the proposed fix below — both are
pinned as additional test rows.

## Why it matters

This is the **fourth instance** of a matcher-derivation gap on the
same file:

- [`pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging`](../pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging/)
  (done 2026-05-30) — substring `"git add -"` overmatched `git add --`.
- [`pattern-generalization-mutation-detector-skips-long-form-git-add-flags`](../pattern-generalization-mutation-detector-skips-long-form-git-add-flags/)
  (done 2026-05-30) — regex alternation skipped `--all`, `--update`,
  `--patch`. The closure decision said:

  > a tokenized parser is resilient to future git long-form alias
  > additions and **closes the meta-fix loop so no fourth card in
  > the family is needed**, at a cost of ~10 LOC

  This card is that fourth card. The tokenized parser closed the
  *long-form-alias* axis but inherited the positional `tokens[1] ==
  subcommand` assumption from the prior regex. The meta-fix did
  not actually close the family.

- [`pattern-generalization-mutation-detector-skips-tool-result-turns`](../pattern-generalization-mutation-detector-skips-tool-result-turns/)
  (open) — transcript-walk axis.
- [`pattern-generalization-mutation-detector-skips-notebookedit-tool-calls`](../pattern-generalization-mutation-detector-skips-notebookedit-tool-calls/)
  (open) — tool-type axis.

**Reachability:** A `Bash` tool call emits `git -c commit.gpgsign=false
commit -m foo` (e.g. an agent working in an environment where commit
signing is misconfigured and the only way past the
`gpg failed to sign` error is the inline `-c` override), or
`git --no-pager commit ...` to suppress pager interaction in CI
contexts, or `git -C /path/to/worktree commit ...` when operating
across worktrees. The Stop hook's `_had_code_mutation` walks the
transcript looking for any matching command; finding none, it
silently returns control to the agent without the
`[GoC | pattern-check]` reminder, and the pattern-generalization
self-assessment is never prompted.

`tests/test_pattern_generalization_hook.py` (the regression set
already in place) has **no rows** for any pre-subcommand global
option. The family's coverage continues to be defined by the
shapes that surfaced bugs, not by a derivation of git(1)'s actual
grammar — exactly the failure mode the closed long-form-flags card
predicted in its "Why it matters" section:

> Closing this card without also extending the test coverage to
> the long forms guarantees a fourth instance.

The structural finding is that the test coverage and the matcher
share a positional model of `git <subcommand>`, but git(1)'s
grammar is `git [global-options] <subcommand> [args]`. Until the
matcher derives the subcommand position correctly (or the test
sweep enumerates the global-option prefix axis), a fifth instance
remains possible.

## Decision required

The fix is bounded but admits two credible mechanisms. Pick one:

**Option A — Walk past leading option-shaped tokens before reading
the subcommand.** Treat any token that starts with `-` (and the
value that follows for two-arg options like `-c`, `-C`,
`--git-dir`, `--work-tree`, `--namespace`, `--super-prefix`,
`--config-env`, `--exec-path`) as a global-option prefix; once a
non-`-` token is found, that's the subcommand. Resilient to future
global-option additions, but the two-arg list has to be enumerated
or the tokenizer has to handle both `--git-dir=path` (one token)
and `--git-dir path` (two tokens) shapes.

**Option B — Maintain an explicit allow-set of known git global
options.** Enumerate the set documented in `git(1)`'s synopsis;
skip exactly those tokens (and the value that follows for
known-two-arg options). More precise — `git -nonsense commit`
would not be mis-recognized as a commit — but requires a small
update each time git ships a new global option.

**Option C — Use `git rev-parse --parseopt` or shell-out to git's
own option parser.** Most accurate, but adds a subprocess call on
every transcript walk and a hard dependency on `git` being on
`PATH` at hook time (the hook currently is pure-Python).

The closed sibling's decision section motivated the tokenized
parser specifically by "closes the meta-fix loop so no fourth card
in the family is needed." Whatever option is chosen here, the
follow-on derivation-test contract should also land: the
regression suite should enumerate the canonical surface of git's
*invocation grammar* (subcommand, broad-staging flag set,
global-option set) rather than the union of historically-seen
shapes, so the family's fifth instance can't ship under cover.

## Fix

Apply the chosen option above. After patching
`goc/templates/hooks/pattern_generalization_check.py`, run
`pre-commit run --all-files` so `scripts/sync_plugin_assets.py`
mirrors the change into `claude-plugin/hooks/` and
`codex-plugin/hooks/`. Re-run
`scripts/port_skills_to_openclaw.py` is **not** needed — the
OpenClaw plugin hand-ports the Python hook into TypeScript
(`openclaw-plugin/index.ts`), so that file must be updated by hand
to mirror the new parser. Add six regression rows to
`tests/test_pattern_generalization_hook.py` pinning the
pre-subcommand-global-option positive cases.
