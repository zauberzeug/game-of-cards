---
title: denied-preamble-block-aborts-skill-load-before-the-preflight-routes-to-kickoff
summary: "Release smoke Path B fails deterministically on the v0.0.28 tag: when Claude Code denies a skill's goc preamble block, it aborts the whole skill load, so the preflight that should route to kickoff never reaches the agent, and kickoff no longer carries the permission remediation. Fresh Claude Code installs without Bash(goc:*) get a bare permission error, and v0.0.28 stays unpublished."
status: active
stage: null
contribution: high
created: "2026-10-14T13:06:23Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] PROCESS: fix shape decided and recorded in this card — e.g. (a) carry the kickoff routing where a denied block cannot hide it (skill description, a hook, or a preamble that needs no permission), (b) give the generic preflight a route to the host complement `claude-kickoff`, or put the permission remediation back into kickoff, (c) align Path B's expectations with the current skills and Claude Code behavior
  - [ ] EMPIRICAL: countercheck recorded — Path B with v0.0.27's skills under current Claude Code, which decides between f20a8920 and a Claude Code behavior change
  - [ ] TDD: Path B passes on main in a workflow run (dry-run release or equivalent)
  - [ ] MECHANICAL: the next release is published to PyPI, npm and ClawHub
  - [ ] MECHANICAL: `uv run goc validate` passes
worker: {who: Rodja Trappe, where: worktree-agent-a5b14c91dd90c4511}
---

# A denied preamble block aborts the skill load before the preflight can route to kickoff

## What happened

The v0.0.28 release has failed twice, and nothing is published (PyPI and npm answer 404 for 0.0.28).

- Run [38411041965](https://github.com/zauberzeug/game-of-cards/actions/runs/38411041965) (2026-10-13,
  `release` mode from main `cf12dd7b`): build green, version commit `8ac4bc69` and tag `v0.0.28`
  pushed. The smoke failed in Path A because the CI's Claude subscription had hit its seven-day limit
  (`rate_limit_event`, `rateLimitType: seven_day`, `status: rejected`). Not a code defect.
- Run [38453406294](https://github.com/zauberzeug/game-of-cards/actions/runs/38453406294)
  (2026-10-13 19:15Z, `tag` mode on `v0.0.28`): Path A passed. Path B failed with
  `FAIL Path B: result.txt missing or wrong` (job 115490011281, step "Assert Path B").

The tool result the Path B agent received for `Skill(audit-deck)` was the denial alone, not the
skill body:

> Shell command permission check failed for pattern "!`b=.claude/skills/_goc-bootstrap.sh; if [ -f $b ]; then sh $b; else goc; fi 2>&1 || true`": Permission to use Bash has been denied because Claude Code is running in don't ask mode.

The agent then explained why it did not write `B:passed` (from the run's final result):

> `Skill(audit-deck)` hit the `goc` `!`-block, and the Bash permission was denied as expected. The
> skill's rendered output carried the denial error, with no preflight text pointing to
> `Skill(kickoff)`. […] `Skill(kickoff)` loaded, but its body contains neither `Bash(goc:*)` nor
> `permissions.allow`. Its Stage 0 halts on a missing `goc` with "install goc and re-run kickoff".

A re-run cannot pass: both findings are properties of the tagged skills, not of the model.

## Why it matters

Two separate gaps meet in Path B:

1. **The preflight is unreachable.** audit-deck's Preflight ("If any `!` block below shows …
   `Permission for this action has been denied` … stop and invoke `Skill(kickoff)` first") lives in
   the skill body. When Claude Code denies a preamble block, it returns the denial instead of the
   skill, so the body never reaches the agent. The guard from
   `skill-preamble-shell-blocks-call-bare-goc-and-abort-skill-load-off-path` (`2>&1 || true`) covers a
   block that runs and fails; a denied block never runs. Every shipped skill with a goc preamble
   (audit-deck, pull-card, next-card, refine-deck, retrospective, standup) behaves the same way for a
   fresh install without `Bash(goc:*)`: the user sees a bare permission error and no route to setup.
2. **kickoff carries no permission remediation.** Since
   `split-claude-specific-content-out-of-generic-kickoff-skill` (b30853e6, 2026-05-09) the
   `Bash(goc:*)` / `permissions.allow` text lives only in `claude-kickoff`, whose Stage 3 has the agent
   write the rule into the project's `.claude/settings.json` itself. Path B still expects kickoff to
   show the user the rule to add to `~/.claude/settings.json`.

## What this run does not decide

`.github/workflows/release.yml` has not changed since v0.0.27, whose smoke passed on 2026-07-14. The
audit-deck preamble did change: f20a8920 (2026-07-15) replaced `` !`goc` `` with the compound call
through `_goc-bootstrap.sh`. Whether the whole-skill abort comes from that change (a compound command
checked as one pattern) or from a newer Claude Code that aborts on any denied preamble is open. The
countercheck is Path B with v0.0.27's skills under today's Claude Code.

## Context

Found while updating an OpenClaw deployment to v0.0.28. The OpenClaw plugin has no `!` blocks and is
not affected; that deployment runs the plugin from the `v0.0.28` tag, unpublished, to get the summary
gate from #12. This card blocks only the publish. Related:
`local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job` (the local mirror of the same smoke).

## Decision

*Resolved 2026-10-22T05:39:15Z:* Fix shape (a)+(b)+(c): every goc-preamble skill pre-approves its own render-time blocks with one exact Bash(<block>) allowed-tools entry each; the Preflight and kickoff route a denied goc call to the host complement claude-kickoff; goc names a missing deck; the smoke allows the namespaced plugin skills

*Reasoning:* Countercheck on Claude Code 2.1.303: any denied render-time block aborts the whole skill load, v0.0.27's plain goc block included, so this is a Claude Code behavior change rather than f20a8920; the documented Bash(goc:*) grant does not cover f20a8920's compound block while it covers v0.0.27's, so main as-is would regress every granted user; exact allowed-tools entries load the body

