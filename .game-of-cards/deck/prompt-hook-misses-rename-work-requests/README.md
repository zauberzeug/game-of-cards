---
title: prompt-hook-misses-rename-work-requests
summary: "The shipped Claude UserPromptSubmit hook does not recognize `rename the button to Export` as work-initiating, even though the generated AGENTS guidance uses that exact shape as a persistent-work example. Those prompts bypass the silent GoC pipeline reminder."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] `uv run python .game-of-cards/deck/prompt-hook-misses-rename-work-requests/reproduce.py` exits zero
  - [x] The prompt hook emits the GoC reminder for rename-style work requests
  - [x] The hook still stays silent for pure exploration and one-shot tooling prompts
  - [x] Focused tests cover the canonical AGENTS examples: rename, add CSV export, and fix auth bug
---

# prompt-hook-misses-rename-work-requests

## Location

- `goc/templates/AGENTS_GOC.md:12`
- `goc/templates/hooks/user-prompt-submit.py:18`
- `goc/templates/hooks/user-prompt-submit.py:48`
- `goc/templates/hooks/user-prompt-submit.py:78`

## What's broken

The generated AGENTS guidance presents this as a persistent-work example:

```markdown
When the user asks for persistent work ("rename the button to Export", "add
a CSV export", "fix the auth bug"), run the GoC pipeline silently:
```

The Claude `UserPromptSubmit` hook is supposed to inject the GoC reminder
when a user prompt "looks work-initiating". But its `WORK_INITIATING`
regex list does not include `rename`, so the canonical rename request
falls through with no reminder.

## Empirical evidence

Current output from `uv run python deck/prompt-hook-misses-rename-work-requests/reproduce.py`:

```text
'rename the button to Export': exit=0; reminded=False
'add a CSV export': exit=0; reminded=True
'fix the auth bug': exit=0; reminded=True
'explain the auth flow': exit=0; reminded=False
'git status': exit=0; reminded=False
defect present:
- 'rename the button to Export' reminded=False, expected True
```

## Why it matters

Session mode depends on the hook for silent card creation in Claude Code.
If common edit requests such as "rename the button..." are missed, the
runtime behaves inconsistently: some persistent work enters the deck,
while equally valid work requests bypass the deck entirely.

## Fix

Add rename-style verbs to the hook's work-initiating classifier and cover
the three examples named in the AGENTS template:

- `rename the button to Export`
- `add a CSV export`
- `fix the auth bug`

Keep the exploration/tooling exclusions intact so prompts like "explain
the auth bug" and "git status" remain silent.
