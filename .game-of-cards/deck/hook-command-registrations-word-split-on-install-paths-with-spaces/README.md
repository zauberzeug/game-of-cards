---
title: hook-command-registrations-word-split-on-install-paths-with-spaces
summary: "Every GoC hook command is registered with an unquoted ${CLAUDE_PROJECT_DIR} / ${CLAUDE_PLUGIN_ROOT} expansion (GOC_CLAUDE_HOOKS in install.py, both plugin hooks.json payloads, the dogfood settings.json). Hook commands run through a shell, so a repo path containing a space word-splits and python3 exits 2 — which on the Stop hook is Claude Code's block channel, so the broken registration actively blocks the agent's stop. Fix is quoting, but the rollout needs a decision on migrating already-installed consumer settings."
status: open
stage: null
contribution: high
created: "2026-07-09T01:13:57Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — every GOC_CLAUDE_HOOKS command succeeds under a project path containing a space
  - [ ] TDD: a regression test asserts the registered hook commands quote the env expansion (install.py source of truth)
  - [ ] MECHANICAL: claude-plugin/hooks/hooks.json, codex-plugin/hooks/hooks.json, and the dogfood .claude/settings.json carry the quoted form
  - [ ] MECHANICAL: `goc upgrade` on a settings.json holding the old unquoted command replaces it with the quoted form (no duplicate registration left behind)
  - [ ] PROCESS: decision on the migration approach recorded below and in log.md
---

# Every GoC hook registration word-splits on install paths with spaces, and the Stop hook turns the failure into a block

## Location

- `goc/install.py:539-543` (`GOC_CLAUDE_HOOKS` — vendored `--local-skills` path)
- `claude-plugin/hooks/hooks.json:8,18,28` (`${CLAUDE_PLUGIN_ROOT}`, hand-maintained)
- `codex-plugin/hooks/hooks.json:8,19,30` (`${PLUGIN_ROOT}`, hand-maintained)
- `.claude/settings.json:8,18,28` (this repo's dogfood copy)

## What's broken

The vendored install merges these commands into the consumer's
`.claude/settings.json`:

```python
GOC_CLAUDE_HOOKS: dict[str, str] = {
    "SessionStart": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py",
    "UserPromptSubmit": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_prompt_router.py",
    "Stop": "python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/pattern_generalization_check.py",
}
```

Claude Code executes hook commands through a shell, where the unquoted
`${CLAUDE_PROJECT_DIR}` expansion word-splits. A repo at any path with
a space — `~/My Project`, Google Drive's `My Drive`, `Documents/My
Project` on Windows — makes every GoC hook die with `python3: can't
open file '/…/My': [Errno 2] No such file or directory`. Claude Code's
own hook documentation quotes the expansion
(`"$CLAUDE_PROJECT_DIR"`) in its examples; GoC's registrations drop
the quotes.

The Stop registration is the sharp edge: python3's can't-open-file
exit code is **2**, and exit 2 from a Stop hook is Claude Code's
*block* channel — so `pattern_generalization_check`, designed to be a
soft opt-in reminder (its config gate never runs because the
interpreter never opens the file), instead blocks the agent's stop and
feeds it the garbled path error on every turn.

The same unquoted shape ships in both plugin payloads
(`${CLAUDE_PLUGIN_ROOT}` / `${PLUGIN_ROOT}`), which break identically
when the plugin install root contains a space.

## Empirical evidence

```
$ uv run python .game-of-cards/deck/hook-command-registrations-word-split-on-install-paths-with-spaces/reproduce.py
DEFECT: SessionStart hook exits 2 under a spaced project path
  command: python3 ${CLAUDE_PROJECT_DIR}/.claude/hooks/deck_session_start.py
  stderr:  python3: can't open file '/tmp/tmpwn6wqzao/My': [Errno 2] No such file or directory
DEFECT: UserPromptSubmit hook exits 2 under a spaced project path
  ...
DEFECT: Stop hook exits 2 under a spaced project path
  ...
note: exit 2 from a Stop hook is Claude Code's block channel — the Stop registration blocks the agent's stop with this garbled error
exit=1
```

## Why it matters

Reachability is the entire vendored-hook surface: `goc install
--local-skills` writes these commands verbatim into every consumer's
settings, and the plugin payloads ship the sibling shape to every
marketplace install. Spaced project paths are routine on macOS and
Windows, and the failure is not a silent degradation — the Stop hook
blocks the agent with an error that names neither GoC nor the actual
cause.

Related but distinct: [vendored-hooks-bake-uv-into-claude-settings-breaking-pipx-only-installs](../vendored-hooks-bake-uv-into-claude-settings-breaking-pipx-only-installs/)
is about the interpreter choice; [goc-upgrade-leaves-stale-prior-version-hook-registrations-in-claude-settings](../goc-upgrade-leaves-stale-prior-version-hook-registrations-in-claude-settings/)
is about cleanup matching — the migration leg below must not recreate
that bug.

## Decision required

The fix itself is determined — quote the expansion
(`python3 "${CLAUDE_PROJECT_DIR}/.claude/hooks/…"`), matching Claude
Code's documented examples; `_HOOK_FILE_RE` (`install.py:545`) is
unanchored and still matches through a leading quote, so GoC-managed
entry detection survives. The open question is the rollout for
already-installed consumers:

1. **Quote-and-migrate:** change `GOC_CLAUDE_HOOKS` and teach
   `_merge_claude_settings` / the upgrade cleanup to treat the old
   unquoted string as the same GoC-managed entry and replace it
   (likely already true via `_HOOK_FILE_RE` matching — must be
   verified with a test), so one `goc upgrade` heals existing
   installs. Preferred if the replace path really is already there.
2. **Quote new installs only:** minimal diff; existing consumers keep
   the broken command until they reinstall. Leaves the Stop-hook
   block live in the field.

Both plugin `hooks.json` files and the dogfood `.claude/settings.json`
are hand-maintained mirrors and need the same one-line quoting either
way.
