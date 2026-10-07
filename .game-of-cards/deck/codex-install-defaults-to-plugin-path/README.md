---
title: codex-install-defaults-to-plugin-path
summary: "Every goc install that includes Codex vendors all 16 GoC skills into .codex/skills/, a rule set on 2026-05-07 because Codex had no plugin then. The Codex plugin has shipped since 2026-05-18, with a bundled engine reachable through skills/_goc-bootstrap.sh since 2026-06-09, but the default was never revisited: this is the follow-up claude-install-defaults-to-plugin-path promised for that moment. Whether Codex installs should defer to the plugin the way Claude installs do is a policy call, because Codex plugin hooks are opt-in and Codex puts no plugin bin/ on PATH."
status: open
stage: null
contribution: high
created: "2026-10-07T04:37:00Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: the Codex install default is decided via `goc decide` (option and why recorded on this card)
  - [ ] TDD: `tests/test_install.py` pins the decided rule for `--agents codex` and `--agents claude,codex`, with and without `--local-skills`, and the `goc upgrade` path for an existing vendored `.codex/skills/`
  - [ ] MECHANICAL: `_should_use_local_skills` and `LOCAL_SKILLS_HELP` (`goc/install.py`), `goc.md`, `site/llms.txt` and `Skill(codex-kickoff)` state the decided rule; mirrors re-synced and OpenClaw skills re-ported
  - [ ] PROCESS: `codex-only-install-pins-skills-source-to-plugin-skipping-parity-check` and `codex-install-from-plugin-payload-vendors-skills-and-crashes-on-omitted-templates-skills` are re-read against the decision, each with a log.md entry saying whether it still stands
---

# Codex installs still vendor every skill although the Codex plugin ships

When `claude-install-defaults-to-plugin-path` moved Claude installs to the
plugin path on 2026-05-07, it kept Codex vendored. Its DoD says why: "Codex
has no plugin yet — `publish-codex-plugin` is still session-gated. When that
ships, a follow-up card flips the Codex default analogously". Its notes name
this card: "when `publish-codex-plugin` ships, file a follow-up
`codex-install-defaults-to-plugin-path` card." `publish-codex-plugin` closed
on 2026-05-18, and the card was never filed. A second closed card,
`install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag`,
promised the same filing on 2026-10-03, and that filing never happened either.
[codex-install-guidance-predates-the-codex-plugin-and-its-bundled-engine](../codex-install-guidance-predates-the-codex-plugin-and-its-bundled-engine/)
filed it on 2026-10-07 while fixing the docs that still said "no plugin yet".

## Location

- `goc/install.py` `_should_use_local_skills`: `return agent != "claude" or local_skills`.
  Codex is vendored on every install, and no flag opts out.
- `goc/install.py` `LOCAL_SKILLS_HELP`: now states that rule as it is, with no
  "no plugin yet" premise. It changes with the decision.
- `goc/install.py` `skills_source` pin: `"vendored" if "claude" in local_skills_agents else "plugin"`.
  The key is single-valued and describes only Claude.
- `goc/templates/skills/codex-kickoff/SKILL.md` already covers moving a repo
  "from checked-in Codex skills to the plugin path". Nothing in the engine does that move.

## What's at stake

A plain `goc install` that detects Codex, or `--agents codex`, writes all 16
GoC skill directories plus `_goc-bootstrap.sh` into `.codex/skills/`. That
duplicates what the Codex plugin installs, and version drift between the two is
the user's problem. Claude installs stopped doing this five months ago, for that
reason.

## Decision required

Should Codex installs stop vendoring skills when the Codex plugin is the
intended source?

- **A — keep vendoring (status quo, made deliberate).** Record why: Codex
  plugin hooks are opt-in (`[features] plugin_hooks = true`), and Codex puts no
  plugin `bin/` on PATH, so a vendored tree works with no Codex-side setup. The
  help text already states this rule; the cost is the duplicate skill tree.
- **B — mirror Claude.** Codex installs default to the plugin path and write no
  `.codex/skills/`; `--local-skills` becomes the vendoring opt-in for both hosts.
  `goc upgrade` offers the vendored-to-plugin cleanup for `.codex/skills/` as it
  does for `.claude/skills/`. `skills_source` must then say which host it
  describes, which is the question parked on
  [codex-only-install-pins-skills-source-to-plugin-skipping-parity-check](../codex-only-install-pins-skills-source-to-plugin-skipping-parity-check/).
  Vendoring from inside a plugin engine then becomes the same refusal Claude
  gets, which dissolves the crash parked on
  [codex-install-from-plugin-payload-vendors-skills-and-crashes-on-omitted-templates-skills](../codex-install-from-plugin-payload-vendors-skills-and-crashes-on-omitted-templates-skills/).
- **C — detect per host.** Vendor Codex skills only when no Codex plugin payload
  is found under `~/.codex/plugins/cache/`. This is the `auto` fallback Claude
  uses, applied per host. It is the least disruptive option, but it makes the
  committed tree depend on the machine that ran the install.

Whichever option is picked also answers the two parked cards above, so decide
them together.
