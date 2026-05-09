---
title: claude-md-template-must-import-agents-md-content
summary: "`goc/templates/CLAUDE_GOC.md` (and the deployed `CLAUDE.md` in this repo) currently uses a plain markdown link `[AGENTS.md](AGENTS.md)` to point readers at the shared GoC briefing. Claude Code does not follow markdown links as imports — its docs explicitly say `Claude Code reads CLAUDE.md, not AGENTS.md` and recommend either the `@AGENTS.md` import syntax (which Claude Code resolves at load time) or a `ln -s AGENTS.md CLAUDE.md` symlink. Today's template silently gives Claude *less* GoC context than before the slim-down, because Claude never sees the AGENTS.md content at all. Fix by switching the template to `@AGENTS.md` import (or, if that proves brittle, inlining the briefing back into CLAUDE_GOC.md for Claude only)."
status: active
stage: null
contribution: medium
created: 2026-05-09
closed_at: null
human_gate: none
advances:
  - write-agentsmd-alongside-claudemd
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] `goc/templates/CLAUDE_GOC.md` uses `@AGENTS.md` import (or another mechanism Claude Code actually resolves at load time) so Claude sees the AGENTS.md briefing
  - [ ] The plugin payload copy at `claude-plugin/` is updated in lockstep (the byte-for-byte CI tripwire enforces this)
  - [ ] The deployed `CLAUDE.md` in this repo is regenerated via `goc upgrade` so Claude in this very repo also picks up the briefing
  - [ ] Smoke test: open a Claude Code session in a fresh `goc install`-ed tmpdir; confirm Claude has loaded both the AGENTS.md briefing and the CLAUDE_GOC.md delta (e.g. by asking it about deck-first mode and verifying it cites content that lives only in AGENTS.md)
  - [ ] If `@AGENTS.md` import is brittle (e.g. relative-path resolution fails when CLAUDE.md is in a subdir), fall back to inlining the briefing in CLAUDE_GOC.md and document the duplication in CLAUDE.md
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# Claude is not loading the AGENTS.md briefing

## Why

When `write-agentsmd-alongside-claudemd` shipped, `CLAUDE_GOC.md`
was slimmed by ~60% with the shared content moving to `AGENTS_GOC.md`
and a markdown cross-link left behind:

```markdown
The shared briefing is in [AGENTS.md](AGENTS.md) — three operating
modes (session / autonomous / Andon-cord), the `goc` CLI verb table,
and the deck philosophy apply to every runtime.
```

This was filed under the assumption that Claude Code would read
AGENTS.md. It does not. Per the official Claude Code docs:

> Claude Code reads `CLAUDE.md`, not `AGENTS.md`. If your repository
> already uses `AGENTS.md` for other coding agents, create a
> `CLAUDE.md` that imports it so both tools read the same instructions
> without duplicating them.

The recommended import syntax is `@AGENTS.md` — Claude Code resolves
this at load time and inlines the file's content. A plain markdown
link like the current template is a no-op for context loading.

## Impact

Every Claude Code user with a freshly-installed or upgraded GoC repo
since the slim-down silently gets the Claude-specific delta only —
not the deck-first mode, not the verb table, not the Andon-cord
explanation, not the `pull-card` semantics. The agent has to
re-discover all of this from skill bodies + tool calls.

This is silent: no error, no warning. The user sees nothing wrong;
the agent just performs worse than it should.

## Fix

Replace the markdown link with the `@AGENTS.md` import:

```markdown
@AGENTS.md
```

(Or with a more verbose form that explains the import to a human
reader of CLAUDE.md, if Claude Code accepts it.)

Update the template, the consumer copy in this repo, and the plugin
payload at `claude-plugin/skills/...` (the byte-for-byte CI check
will fail otherwise).

## Validation

Open a fresh tmpdir, run `goc install`, then start a Claude Code
session and ask "what does `goc done` enforce?" — the answer should
cite the DoD checkbox enforcement that lives in AGENTS_GOC.md, not
just whatever the agent guesses from the verb name.

## Cross-references

- Parent: `write-agentsmd-alongside-claudemd` (the card whose
  implementation introduced this regression)
- Plugin duplication: the fix lives in two places (`goc/templates/`
  + `claude-plugin/`); `generate-plugin-payloads-from-templates-on-release`
  would eliminate this lockstep burden.
