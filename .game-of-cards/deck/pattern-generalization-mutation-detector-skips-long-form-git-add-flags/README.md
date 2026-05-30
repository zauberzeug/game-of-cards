---
title: pattern-generalization-mutation-detector-skips-long-form-git-add-flags
summary: "After the substring→regex rewrite, the pattern-generalization stop hook's matcher `git\\s+add\\s+(?:-[A-Za-z]|\\.)` accepts only short single-letter staging flags (-A, -p, -u) or `.`. The long-form aliases documented in `git-add(1)` — `git add --all`, `--update`, `--patch` — are not matched, so a turn whose only mutating action is `git add --all foo/` bypasses the generalization self-assessment prompt entirely."
status: done
stage: null
contribution: high
created: "2026-05-30T08:00:18Z"
closed_at: "2026-05-30T17:00:19Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (mutation detector returns True on synthetic transcripts whose only Bash call is `git add --all foo`, `--update`, or `--patch`)
  - [x] TDD: the same script still returns True on the short-flag forms `-A`, `-p`, `-u`, `.` and on `git commit ...` (positive baseline preserved); still returns False on `git add -- foo.py` and bare `git add foo.py` (negative baseline preserved)
  - [x] MECHANICAL: `goc/templates/hooks/pattern_generalization_check.py` replaced `_BASH_COMMIT_RE` with a tokenized `shlex.split` parser (`_is_broad_git_mutation` matches `{-A,-p,-u,--all,--update,--patch,.}` per the recorded decision); `claude-plugin/hooks/`, `codex-plugin/hooks/`, and `openclaw-plugin/index.ts` mirror updated via the sync + porter scripts
  - [x] PROCESS: tests/test_pattern_generalization_hook.py adds regression rows for the three long-form flags
  - [x] PROCESS: closure logged in log.md with the reproduce.py before/after output
worker: {who: "claude[bot]", where: main}
---

# pattern-generalization-mutation-detector-skips-long-form-git-add-flags

## Location

`goc/templates/hooks/pattern_generalization_check.py:28-30` —
`_BASH_COMMIT_RE`.

## What's broken

The recent matcher rewrite (sibling card
[`pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging`](../pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging/),
closed 2026-05-30) replaced the substring-containment matcher with an
anchored regex. The new alternation enumerates only the **short
single-letter** staging flags:

```python
# goc/templates/hooks/pattern_generalization_check.py:23-30
# Match `git commit ...` (any form) and the staging forms that mutate the
# index broadly: `git add -A`, `git add -p`, `git add -u`, `git add .`.
# Deliberately reject the pathspec-separator form `git add -- <path>` and
# bare `git add <path>` — those stage explicit paths and are documented
# in AGENTS.md as the safe parallel-agent staging idiom.
_BASH_COMMIT_RE = re.compile(
    r"\bgit\s+commit\b|\bgit\s+add\s+(?:-[A-Za-z]|\.)"
)
```

The character class `[A-Za-z]` matches exactly one letter, so the
alternative `-[A-Za-z]` requires `-` followed by a single letter and
then either a word boundary or any other character — it does **not**
match `--all`, `--update`, or `--patch`. (Tried at the staging-flag
position, the regex engine sees `-` followed by another `-`, fails the
char-class, fails the `\.` alternative, and the overall pattern does
not match.) But `git-add(1)` documents the long-form aliases:

> `-A, --all, --no-ignore-removal` — Update the index not only where
> the working tree has a file matching `<pathspec>` but also where the
> index already has an entry.
>
> `-u, --update` — Update the index just where it already has an entry
> matching `<pathspec>`.
>
> `-p, --patch` — Interactively choose hunks of patch between the
> index and the work tree and add them to the index.

— `git add --help`

These long-form spellings are semantically identical to the short
flags the matcher already catches, but they slip past silently.

## Empirical evidence

`uv run python deck/pattern-generalization-mutation-detector-skips-long-form-git-add-flags/reproduce.py`
constructs synthetic single-turn transcripts whose only assistant tool
call is a Bash invocation with the named git command, then asks
`_had_code_mutation` whether the turn counted as a code mutation:

```
command                        expected   actual     verdict
----------------------------------------------------------------
'git add -A'                   True       True       ok
'git add -p'                   True       True       ok
'git add -u'                   True       True       ok
'git add .'                    True       True       ok
'git add --all foo/'           True       False      DEFECT
'git add --update'             True       False      DEFECT
'git add --patch'              True       False      DEFECT
'git add -- foo.py'            False      False      ok
'git add foo.py'               False      False      ok
'git commit -m msg'            True       True       ok
```

Rows 5-7 are the defect. The positive baseline (short flags + commit)
and the negative baseline (pathspec separator + bare path) are
preserved by the proposed fix below — both are pinned as additional
test rows.

## Why it matters

This is the **third instance** of a matcher-derivation gap on the
same file. Sibling cards in the same family:

- [`pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging`](../pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging/)
  (done 2026-05-30) — substring `"git add -"` overmatched `git add --`.
- [`pattern-generalization-mutation-detector-skips-tool-result-turns`](../pattern-generalization-mutation-detector-skips-tool-result-turns/)
  (open) — transcript-walk logic misses mutations in `tool_result`
  turns.
- [`pattern-generalization-opt-out-regex-matches-anywhere-in-the-file`](../pattern-generalization-opt-out-regex-matches-anywhere-in-the-file/)
  (open) — opt-out matcher anchors are missing.

Reachability path: an agent emits `git add --all goc/` (or `--update`
to restage tracked-but-modified files only) to broadly stage a
multi-file change — exactly the staging shape the hook is meant to
catch. The agent receives no `[GoC | pattern-check]` reminder, skips
the generalization self-assessment, and the broad-pattern card is
never filed. The fact that AGENTS.md's "Parallel-Agent Commit Safety"
guidance explicitly rules out `git add -A`/`git add .` means
agents reading that guidance who reach for the long-form alias
(`--all` is the explicit form documented immediately beside `-A`)
silently bypass the safety the hook was added to provide.

The family also reveals a structural gap in the regression-test set:
`tests/test_pattern_generalization_hook.py` enumerates `-A`, `-p`,
`-u`, `.`, `--`, and bare-path forms (`tests/test_pattern_generalization_hook.py:61-85`)
but has no rows for any long-form flag. Both prior fixes were
test-gated against the same set of short forms, so the same blind
spot recurs each time. Closing this card without also extending the
test coverage to the long forms guarantees a fourth instance.

## Fix

Extend `_BASH_COMMIT_RE`'s staging-flag alternation to include the
three long-form aliases documented by `git-add(1)`:

```python
_BASH_COMMIT_RE = re.compile(
    r"\bgit\s+commit\b|\bgit\s+add\s+(?:-[A-Za-z]|--(?:all|update|patch)|\.)"
)
```

Update the docstring comment immediately above the regex to name the
covered flag set explicitly (so the next reader doesn't have to
re-derive which spellings count as "broad-staging"):

```python
# Match `git commit ...` (any form) and the staging forms that mutate the
# index broadly: short flags (`-A`, `-p`, `-u`), their long-form aliases
# (`--all`, `--update`, `--patch`), and the bare `.` pathspec.
# Deliberately reject the pathspec-separator form `git add -- <path>` and
# bare `git add <path>` — those stage explicit paths and are documented
# in AGENTS.md as the safe parallel-agent staging idiom.
```

After patching `goc/templates/hooks/pattern_generalization_check.py`,
run `pre-commit run --all-files` so `scripts/sync_plugin_assets.py`
mirrors the change into `claude-plugin/hooks/` and `codex-plugin/hooks/`,
and (via the hand-port) `openclaw-plugin/index.ts`. Add three
regression rows to `tests/test_pattern_generalization_hook.py` pinning
the long-form positive cases.

## Decision

*Resolved 2026-05-30T14:00:28Z:* Option 2: replace the git-add regex matcher with a tokenized shlex.split parser that inspects tokens — match when the command is git add with any flag in {-A,-p,-u,--all,--update,--patch} or the bare '.' token, rejecting 'git add foo.py' and 'git add -- foo.py'

*Reasoning:* this code path has churned twice for matcher bugs this quarter; a tokenized parser is resilient to future git long-form alias additions and closes the meta-fix loop so no fourth card in the family is needed, at a cost of ~10 LOC

