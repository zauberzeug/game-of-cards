---
title: claude-install-registers-runtime-hooks
summary: "The Claude harness installs a UserPromptSubmit hook script, but it does not write the `.claude/settings.json` hook registration that makes Claude Code run it. Match the working phasor-agents shape by installing Claude hook config for SessionStart and UserPromptSubmit without clobbering user settings."
status: done
stage: null
contribution: high
created: 2026-05-04
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] `goc install --agents claude` writes or merges `.claude/settings.json` hook registrations without clobbering existing user settings
  - [x] Claude install registers `SessionStart -> uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py`
  - [x] Claude install registers `UserPromptSubmit -> uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py`
  - [x] The installed hook scripts exist under `.claude/hooks/` and are packaged from `goc/templates/hooks/`
  - [x] Tests cover fresh Claude install, upgrade re-sync, and preservation of unrelated `.claude/settings.json` keys/hooks
  - [x] README/CLAUDE guidance accurately distinguishes Claude hook registration from `.game-of-cards/config.yaml`
---

# claude-install-registers-runtime-hooks

## Context

Current GoC Claude harness manifest installs:

```json
{
  "source": "hooks/user-prompt-submit.py",
  "target": ".claude/hooks/user-prompt-submit-goc.py"
}
```

and `CLAUDE_GOC.md` says the hook powers silent runtime. But there is no
`.claude/settings.json` registration in the harness, so Claude Code is not
actually told to execute the hook by a fresh GoC install.

The working `../phasor-agents` shape is:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run python ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py"
          }
        ]
      }
    ]
  }
}
```

The user requested this exact runtime wiring. Note the file is Claude
Code's `.claude/settings.json`; `.game-of-cards/config.yaml` remains the
runtime-neutral GoC config for workflow options and closure checks.

## Why it matters

Session-mode promises "silent runtime under user prompts." Installing a
hook script without registering it makes that promise false for fresh
Claude installs: users get files on disk, but Claude Code will not invoke
them.

## Scope

Implement Claude harness hook registration:

- Add/install `deck_prompt_router.py` as the UserPromptSubmit hook. This can
  rename or wrap the current `user-prompt-submit.py` implementation, but the
  installed path should match the configured command.
- Add/install `deck_session_start.py` for the SessionStart hook. It should
  provide a lightweight GoC session reminder or status primer consistent with
  the methodology and avoid noisy output.
- Teach `goc install` / `goc upgrade --agents claude` to merge
  `.claude/settings.json` rather than overwriting unrelated user settings.

Out of scope: Codex/OpenCode/Cursor hook registration. Their runtime hook
systems differ; this card is Claude-specific.

## Relationship to other cards

- Related but distinct:
  [`prompt-hook-misses-rename-work-requests`](../prompt-hook-misses-rename-work-requests/)
  fixes classifier coverage inside the prompt hook.
- Related but distinct:
  [`generated-agents-guidance-overstates-done-commit`](../generated-agents-guidance-overstates-done-commit/)
  fixes stale closure wording in generated guidance.
