---
title: openclaw-kickoff-defaults-to-claude-install
summary: "The OpenClaw onboarding path claims the generic kickoff is host-agnostic, but the bundled install engine still defaults to the Claude harness when no repo marker exists. A fresh OpenClaw repo therefore plans `agents: claude` and a `CLAUDE.md` append instead of an OpenClaw-safe scaffold."
status: done
stage: null
contribution: medium
created: "2026-05-18T04:28:15Z"
closed_at: 2026-05-26T13:03:06Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] `python3 .game-of-cards/deck/openclaw-kickoff-defaults-to-claude-install/reproduce.py` exits zero and demonstrates the current wrong default against the OpenClaw-bundled engine.
  - [x] The install/kickoff contract for OpenClaw is decided: either the bundled engine recognizes OpenClaw explicitly, or the kickoff docs stop claiming that plain `goc install` is host-agnostic on OpenClaw.
  - [x] The chosen fix is covered by a regression test that fails if an OpenClaw-hosted fresh repo ever plans `agents: claude` again.
worker: {who: Rodja Trappe, where: main}
---

# openclaw-kickoff-defaults-to-claude-install

## Summary

The OpenClaw-specific kickoff says the generic `kickoff` skill is safe to run
first and that it "runs `goc install` to scaffold `.game-of-cards/`". But the
bundled install engine still treats "no host markers present" as "default to
Claude". In practice, a fresh repo driven from the OpenClaw plugin plans
`agents: claude` and a `CLAUDE.md` append even though the OpenClaw path is
supposed to be plugin-only and explicitly "has no host-specific private-notes
file".

## Location

- `goc/templates/skills/openclaw-kickoff/SKILL.md:7-14`
- `goc/templates/skills/kickoff/SKILL.md:7-10, 152-166, 251-260`
- `goc/install.py:33-47`
- `goc/install.py:325-406`

## What's Broken

The OpenClaw complement promises that the generic kickoff can run first:

> "The generic `kickoff` skill is host-agnostic ... and runs `goc install` to
> scaffold `.game-of-cards/`."

It then states that OpenClaw does not use a Claude-style local-notes file:

> "OpenClaw has no equivalent convention"

But the install engine hard-codes only two supported harnesses:

```python
SUPPORTED_AGENTS = ("claude", "codex")
PLUGIN_ONLY_AGENTS = ("openclaw",)
DEFAULT_AGENTS = ("claude",)
```

And when no markers are present, `_default_install_agents()` returns the
documented default, which is still Claude:

```python
def _default_install_agents(target: Path, *, supported_agents: tuple[str, ...]) -> tuple[str, ...]:
    detected = _detect_agent_surfaces(target, supported_agents=supported_agents)
    if detected:
        return detected
    return tuple(agent for agent in supported_agents if agent in DEFAULT_AGENTS) or DEFAULT_AGENTS
```

That means the OpenClaw-bundled engine contradicts the kickoff contract on a
fresh repo: it plans the Claude harness path rather than an OpenClaw-safe
scaffold.

## Empirical Evidence

`reproduce.py` runs the bundled OpenClaw engine in a temp repo with
`install --dry-run` and prints the planned writes. On 2026-05-18 it reports:

```text
goc install (dry-run) — agents: claude — 19 writes planned
...
Guidance:
  shared append AGENTS.md
  claude append CLAUDE.md
  shared append .pre-commit-config.yaml
```

## Why It Matters

This is the first-run path for an OpenClaw consumer. The docs tell the model to
run the generic kickoff before the OpenClaw complement, but the underlying
engine still assumes Claude semantics when it sees a blank repo. That creates a
false onboarding contract at exactly the moment the host integration is supposed
to feel turnkey. At minimum it produces an unnecessary `CLAUDE.md` artifact;
depending on the eventual fix direction, it may also pin the wrong long-term
install mode into the repo.

This also clashes with the earlier direction that OpenClaw should use a plugin
runtime rather than a first-class `goc install` harness (see the superseded
`install-openclaw-harness` story and the completed
`provide-openclaw-plugin-for-skills-and-hooks` card).

## Possible Fix Directions

This needs a design choice before implementation:

1. Teach `goc install` about OpenClaw as a first-class host context, with a
   guidance-only/default-no-harness mode that never falls back to Claude.
2. Keep OpenClaw out of `SUPPORTED_AGENTS`, but make the OpenClaw plugin pass an
   explicit install mode that only writes `.game-of-cards/` + the chosen
   briefing target.
3. Narrow the kickoff docs so they stop claiming that plain `goc install` is
   host-agnostic on OpenClaw until one of the two options above exists.

## Decision Required

The repo needs one explicit contract for OpenClaw onboarding:

- Should OpenClaw become a first-class install target in `goc install`, or
- Should the plugin keep using a reduced "project-state only" install path that
  bypasses harness selection entirely?

## Decision

*Resolved 2026-05-26T12:52:38Z:* Engine recognizes OpenClaw plugin context and defaults to no harness — write .game-of-cards/ + AGENTS.md only, never CLAUDE.md (card option 1).

*Reasoning:* Keyed on the same _PACKAGE_DIR.parent.name signal _is_plugin_context() already trusts, so it is automatic and correct regardless of how install is invoked; needs no new flag (a user-facing --no-harness flag was previously rejected); honors the kickoff promise that plain goc install is host-agnostic on OpenClaw.

## Resolution

Implemented option 1 in `goc/install.py`:

- New `_is_openclaw_plugin_context()` (true when the engine runs from
  `openclaw-plugin/`, via `_PACKAGE_DIR.parent.name`).
- `install()` and `upgrade()`: when no `--agents` is given and the OpenClaw
  plugin context is detected, the default agent set is `()` (no harness).
  Auto-detection is suppressed too, so a pre-existing `AGENTS.md` (the briefing
  home) is not misread as a Codex surface. Explicit `--agents` still overrides.
- Success/plan messages render the no-harness case ("no agent harness; OpenClaw
  provides skills via its plugin"); `_print_plan` already showed `agents: none`.

A fresh OpenClaw repo now plans `agents: none — .game-of-cards/ + AGENTS.md +
pre-commit`, never `CLAUDE.md`. `reproduce.py` was inverted into a green guard
(exit 0 on the fixed contract; exit 1 if the Claude default returns), matching
the precedent set by `upgrade-default-adds-claude-to-codex-repos`. Regression
coverage: `OpenClawPluginContextTest` in `tests/test_install.py`.

The `openclaw-kickoff` skill template gained a one-clause note confirming the
no-`CLAUDE.md` scaffold is correct, not a missed harness.

> Later evidence: re-porting the skill template surfaced that the
> `openclaw-plugin/skills/` copies (porter output, not covered by the
> byte-for-byte sync tripwire) have silently drifted from the templates. That is
> out of scope here and filed separately as
> `openclaw-plugin-ported-skills-drift-silently-from-templates`.
