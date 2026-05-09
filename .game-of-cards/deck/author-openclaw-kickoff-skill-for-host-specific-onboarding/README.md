---
title: author-openclaw-kickoff-skill-for-host-specific-onboarding
summary: "Author the OpenClaw-specific complement to the host-agnostic `kickoff` skill, parallel to the new `claude-kickoff`. The OpenClaw plugin currently ships only the generic `kickoff/` (ported from `goc/templates/skills/kickoff/`) and has no host-specific finishing-touches step — no equivalent of the Claude permission grant, plugin-update cadence note, or `CLAUDE.local.md`-style private notes file. Establish what those touches are on OpenClaw and ship them as a separate `openclaw-kickoff` skill."
status: active
stage: null
contribution: low
created: 2026-05-09
closed_at: null
human_gate: none
advances:
  - provide-openclaw-plugin-for-skills-and-hooks
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] OpenClaw-specific kickoff finishing touches identified (whether OpenClaw has a permission-grant equivalent, where private/local notes belong, plugin update cadence, etc.)
  - [ ] If touches exist, author `goc/templates/skills/openclaw-kickoff/SKILL.md` and update `scripts/port_skills_to_openclaw.py` so it ports the generic `kickoff/` and registers `openclaw-kickoff` (or, if the script handles it via the agent-prefix convention, document that no script change is needed)
  - [ ] OpenClaw plugin payload (`openclaw-plugin/skills/`) includes both `kickoff/` and `openclaw-kickoff/` after re-running the port script
  - [ ] If OpenClaw has no host-specific kickoff touches, close as superseded with a log entry explaining why no skill is needed
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# Author the OpenClaw-specific kickoff complement

## Why

`split-claude-specific-content-out-of-generic-kickoff-skill` (closed
2026-05-09) refactored `goc/templates/skills/kickoff/SKILL.md` to be
host-agnostic and moved Claude Code-specific UX (`Bash(goc:*)` permission
grant, `/plugin install` cadence, `CLAUDE.md` / `CLAUDE.local.md` merge
prompts) into a new `claude-kickoff` skill. The same refactor established
the per-host complement pattern: `<agent>-kickoff` ships only with that
agent's harness, filtered automatically by `skill_for_agent()` in
`goc/install.py`.

The OpenClaw plugin currently ships only the generic ported `kickoff/`.
Whether it needs an OpenClaw-specific complement depends on what
host-specific touches OpenClaw exposes — for example:

- a permission/sandbox grant analogous to Claude's `Bash(goc:*)` (likely
  no, since OpenClaw exposes `goc` as a registered tool rather than a
  PATH binary, but worth confirming);
- a private-notes file analogous to `CLAUDE.local.md`;
- a plugin update cadence note for ClawHub / npm consumers (parallel to
  Claude Code's `/plugin marketplace update` reminder).

## Investigate first

Before authoring the skill, read upstream OpenClaw docs (skills,
plugins, runtime API) to determine which touches exist. If OpenClaw has
no host-specific finishing-touches step beyond what the generic kickoff
already does, close this card as superseded with a log entry explaining
the conclusion — no skill is better than a stub skill.

## Cross-references

- `split-claude-specific-content-out-of-generic-kickoff-skill` (closed) — established the pattern.
- `provide-openclaw-plugin-for-skills-and-hooks` — parent epic for OpenClaw plugin work.
</content>
