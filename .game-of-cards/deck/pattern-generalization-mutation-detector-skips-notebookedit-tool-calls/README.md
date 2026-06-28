---
title: pattern-generalization-mutation-detector-skips-notebookedit-tool-calls
summary: "The pattern-generalization stop hook's `CODE_MUTATING_TOOLS` set lists only `Edit` and `Write`. Claude Code's `NotebookEdit` tool — the canonical mutator for Jupyter notebook cells — is absent, so an assistant turn whose only mutating action is a `NotebookEdit` call bypasses the generalization self-assessment prompt entirely. Same gap mirrored in the OpenClaw TS port."
status: done
stage: null
contribution: medium
created: "2026-05-30T08:30:36Z"
closed_at: "2026-05-30T08:54:33Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (mutation detector returns True on a synthetic transcript whose only assistant tool call is a `NotebookEdit` invocation)
  - [x] TDD: the same script still returns True on the existing `Edit` / `Write` / `Bash git commit` baseline (positive baseline preserved) and still returns False on a read-only-tools-only turn (negative baseline preserved)
  - [x] MECHANICAL: `goc/templates/hooks/pattern_generalization_check.py` `CODE_MUTATING_TOOLS` extends to `frozenset({"Edit", "Write", "NotebookEdit"})`; `claude-plugin/hooks/` and `codex-plugin/hooks/` mirrors regenerated via the sync script; `openclaw-plugin/index.ts` `CODE_MUTATING_TOOLS` mirror updated by hand (it is hand-ported, not auto-synced)
  - [x] PROCESS: tests/test_pattern_generalization_hook.py adds a regression row for `NotebookEdit`
  - [x] PROCESS: closure logged in log.md with the reproduce.py before/after output
worker: {who: "claude[bot]", where: main}
---

# pattern-generalization-mutation-detector-skips-notebookedit-tool-calls

## Location

`goc/templates/hooks/pattern_generalization_check.py:22` —
`CODE_MUTATING_TOOLS` frozenset.

Mirror: `openclaw-plugin/index.ts:292` —
`const CODE_MUTATING_TOOLS = new Set(["Edit", "Write"]);`.

## What's broken

The stop hook fires its "is this turn an instance of a broader
pattern?" reminder only on turns that included a code-mutating tool
call. The current tool-name set lists exactly two:

```python
# goc/templates/hooks/pattern_generalization_check.py:22
CODE_MUTATING_TOOLS = frozenset({"Edit", "Write"})
```

and the detection helper short-circuits on a hit:

```python
# goc/templates/hooks/pattern_generalization_check.py:70-72
def _is_code_mutating(tool_name: str, entry: dict) -> bool:
    if tool_name in CODE_MUTATING_TOOLS:
        return True
    ...
```

Claude Code ships a third file-mutating tool, `NotebookEdit`, which
edits cells of a Jupyter notebook (`.ipynb`). It is the canonical
mutator for notebook source the same way `Edit` is for `.py` / `.md` /
`.ts` source. The hook's docstring frames the intent as "turns that
included code-mutating tool calls (Edit or Write, or Bash containing
a git-commit)" — the docstring enumerates the two-element set and
makes the same omission as the data.

The TypeScript port in the OpenClaw plugin mirrors the gap:

```typescript
// openclaw-plugin/index.ts:292
const CODE_MUTATING_TOOLS = new Set(["Edit", "Write"]);
// ...
// openclaw-plugin/index.ts:504
if (CODE_MUTATING_TOOLS.has(tc?.name)) return true;
```

## Empirical evidence

`uv run python deck/pattern-generalization-mutation-detector-skips-notebookedit-tool-calls/reproduce.py`
constructs single-turn synthetic JSONL transcripts whose only
assistant tool call is one of `Edit`, `Write`, `NotebookEdit`, or
`Read` (a non-mutating control), then asks `_had_code_mutation`
whether the turn counted as a code mutation:

```
tool                expected   actual     verdict
--------------------------------------------------
Edit                True       True       ok
Write               True       True       ok
NotebookEdit        True       False      DEFECT
Read                False      False      ok
```

The `NotebookEdit` row is the defect. Positive baselines (`Edit`,
`Write`) and the negative baseline (`Read`) are preserved by the
proposed fix below and are pinned as additional test rows.

## Why it matters

This is the **fourth instance** of a matcher-scope gap in the same
hook. Sibling cards in the same family:

- [`pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging`](../pattern-generalization-mutation-detector-fires-on-pathspec-separator-staging/)
  (done 2026-05-30) — substring `"git add -"` overmatched `git add --`.
- [`pattern-generalization-mutation-detector-skips-long-form-git-add-flags`](../pattern-generalization-mutation-detector-skips-long-form-git-add-flags/)
  (open) — `_BASH_COMMIT_RE` accepts only single-letter staging flags.
- [`pattern-generalization-mutation-detector-skips-tool-result-turns`](../pattern-generalization-mutation-detector-skips-tool-result-turns/)
  (open) — transcript-walk logic misses mutations in `tool_result`
  turns.

The prior three cards all touch the Bash-command matching or the
transcript-walk shape; this card is the first to touch the tool-name
set itself. Together they reveal the structural blind spot: every
detection-scope decision in this hook is hand-enumerated against the
set of tools the author had in mind on the day it was written, with
no test that fails when Claude Code (or any host) introduces a new
mutating tool.

Reachability path: an assistant turn on a notebook-heavy repo (data
science, ML research, anywhere `.ipynb` is the primary editable
artifact) uses `NotebookEdit` to mutate a cell. The Stop hook reads
the transcript, walks the most recent assistant turn, sees only a
`NotebookEdit` tool call (no `Edit` / `Write` / `Bash` companion), and
exits silently with `_had_code_mutation` returning `False`. The
[GoC | pattern-check] reminder never appears. The agent never
self-assesses whether the notebook change was an instance of a
broader pattern; no generalization card is filed. The hook is a
strict no-op on the entire notebook-editing workflow.

## Fix

Extend `CODE_MUTATING_TOOLS` to include `NotebookEdit`:

```python
# goc/templates/hooks/pattern_generalization_check.py:22
CODE_MUTATING_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})
```

Update the module docstring's enumeration to match (so the next
reader sees a consistent intent):

```python
"""Stop hook — prompt agent to file generalization cards for pattern instances.

Fires only on turns that included code-mutating tool calls (Edit, Write,
or NotebookEdit, or Bash containing a git-commit). ...
"""
```

After patching `goc/templates/hooks/pattern_generalization_check.py`,
run `pre-commit run --all-files` so `scripts/sync_plugin_assets.py`
mirrors the change into `claude-plugin/hooks/` and
`codex-plugin/hooks/`. The OpenClaw TS port at
`openclaw-plugin/index.ts:292` is hand-ported (not auto-synced) so
update its `CODE_MUTATING_TOOLS` literal by hand to match. Add a
regression row to `tests/test_pattern_generalization_hook.py`
pinning the `NotebookEdit` positive case.

Codex's mutating tool surface is different from Claude Code's
(`apply_patch`, not `Edit`/`NotebookEdit`), so adding `NotebookEdit`
to the Codex mirror is harmless — a `NotebookEdit` tool name will
never appear in a Codex transcript, so the set membership check is
a strict no-op there.
