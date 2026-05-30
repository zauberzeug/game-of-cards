---
title: pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging
summary: "The pattern-generalization stop hook's BASH_COMMIT_TOKENS substring `\"git add -\"` matches the pathspec-separator form `git add -- <path>` — the canonical defensive staging idiom. Turns that only stage a file (no Edit/Write, no commit) trigger the generalization self-assessment reminder, training the agent to ignore it."
status: done
stage: null
contribution: medium
created: "2026-05-30T07:46:12Z"
closed_at: "2026-05-30T07:52:07Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (mutation detector returns False on a synthetic transcript whose only Bash call is `git add -- foo.py`)
  - [x] TDD: the same script still returns True on `git commit -- foo.py` and on `git add -A` (intended hits preserved)
  - [x] MECHANICAL: `goc/templates/hooks/pattern_generalization_check.py` matcher anchors the staging-flag check (e.g. regex `git\s+add\s+-[A-Za-z]` or token list excluding the bare `git add -`); `claude-plugin/hooks/`, `codex-plugin/hooks/`, and `openclaw-plugin/index.ts` mirror updated via the sync script
  - [x] PROCESS: tests/ adds a regression case for the `git add -- <path>` non-mutation path
  - [x] PROCESS: closure logged in log.md with the reproduce.py before/after output
worker: {who: "claude[bot]", where: main}
---

# pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging

## Location

`goc/templates/hooks/pattern_generalization_check.py:23` (the
`BASH_COMMIT_TOKENS` constant) and `:73` (the substring `in` check
inside `_is_code_mutating`).

## What's broken

The stop-hook detects "this turn mutated code" by checking the most
recent assistant turn for an `Edit`/`Write` tool call OR a `Bash` tool
call whose command contains a token from `BASH_COMMIT_TOKENS`:

```python
CODE_MUTATING_TOOLS = frozenset({"Edit", "Write"})
BASH_COMMIT_TOKENS = ("git commit", "git add -", "git add .")
...
def _is_code_mutating(tool_name: str, entry: dict) -> bool:
    if tool_name in CODE_MUTATING_TOOLS:
        return True
    if tool_name == "Bash":
        ...
        for block in content:
            ...
            cmd = (block.get("input") or {}).get("command", "")
            if any(tok in cmd for tok in BASH_COMMIT_TOKENS):
                return True
    return False
```

The token `"git add -"` is presumably intended to catch `git add -A`
and `git add -p` (flag forms that stage everything or interactively).
But Python's `in` operator is plain substring containment, so
`"git add -"` ALSO matches `"git add -- foo.py"` — the explicit
pathspec-separator form that this repo's own `AGENTS.md` prescribes
as the safe staging idiom for parallel-agent commit windows:

> When it is your turn, stage only explicit file paths with
> `git add <path>...`. Do not use `git add .`, `git add -A`,
> directory-wide adds [...] to isolate your work. [...] commit with
> an explicit pathspec: `git commit -- <path>...`. The pathspec is
> the last guard against accidentally bundling unrelated staged
> files.

— `AGENTS.md:354-361` (Parallel-Agent Commit Safety)

Many agents extend the same pathspec-separator discipline to staging
(`git add -- <path>`) for the same reason. Every such call trips
`_is_code_mutating == True` and the generalization reminder fires on
turns that did not edit a file and did not commit.

## Empirical evidence

`uv run python deck/<title>/reproduce.py` constructs a synthetic
transcript with a single assistant Bash turn whose command is
`git add -- foo.py` (no Edit, no Write, no commit), then asks
`_had_code_mutation` whether the turn was code-mutating:

```
git add -- foo.py            -> code_mutation=True   (expected False)
git add -A                   -> code_mutation=True   (expected True)
git commit -- foo.py         -> code_mutation=True   (expected True)
git add foo.py               -> code_mutation=False  (expected False)
```

Row 1 is the defect: a pure-staging turn using the documented-safe
pathspec separator is flagged as a code mutation, so the stop hook
prints `REMINDER` and the agent gets a spurious generalization
self-assessment prompt.

## Why it matters

The reachability path is the canonical happy path of this very repo.
`AGENTS.md` prescribes `git commit -- <path>` and rules out
directory-wide adds; agents that internalize the rule routinely use
`git add -- <path>` on stage-only turns (e.g. preparing a commit
after a previous turn's Edit, or staging a file an external tool
wrote). Each false positive costs a token-budget round trip for the
agent to respond `"no generalization needed"`, and over time trains
the agent to ignore the legitimate firings — exactly the failure
mode that motivated the existing
[`pattern-generalization-stop-hook-reminder-never-reaches-the-agent`](../pattern-generalization-stop-hook-reminder-never-reaches-the-agent/)
card. The substring-match anti-pattern is also documented by sibling
[`pattern-generalization-opt-out-regex-matches-anywhere-in-the-file`](../pattern-generalization-opt-out-regex-matches-anywhere-in-the-file/) —
this is the same shape on a different surface.

## Fix

Replace the substring match with an anchored check. Two equivalent
formulations:

```python
import re
_BASH_COMMIT_RE = re.compile(
    r"\bgit\s+commit\b|\bgit\s+add\s+(-[A-Za-z]|\.)"
)

def _is_code_mutating(tool_name: str, entry: dict) -> bool:
    ...
    if _BASH_COMMIT_RE.search(cmd):
        return True
```

…or keep the token-list shape but make staging-flag detection
explicit:

```python
BASH_COMMIT_PREFIXES = ("git commit",)
BASH_ADD_FLAGS = re.compile(r"\bgit\s+add\s+(-[A-Za-z]|\.)")

...
if any(cmd.lstrip().startswith(p) for p in BASH_COMMIT_PREFIXES) or BASH_ADD_FLAGS.search(cmd):
    return True
```

Either form keeps `git add -A`, `git add -p`, `git add -u`,
`git add .`, and `git commit ...` as positive hits while rejecting
the pathspec-separator form `git add -- <path>` (and the unambiguous
`git add foo.py` — which already does not match today).

After patching `goc/templates/hooks/pattern_generalization_check.py`,
run `pre-commit run --all-files` so `scripts/sync_plugin_assets.py`
mirrors the change into `claude-plugin/hooks/`, `codex-plugin/hooks/`,
and (via the hand-port) `openclaw-plugin/index.ts`. Add a regression
test under `tests/` that pins the four rows from the empirical
evidence table above.
