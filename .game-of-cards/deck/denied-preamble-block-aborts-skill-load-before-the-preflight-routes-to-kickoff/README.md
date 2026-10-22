---
title: denied-preamble-block-aborts-skill-load-before-the-preflight-routes-to-kickoff
summary: "Release smoke Path B failed deterministically on the v0.0.28 tag: current Claude Code aborts the whole skill load on any denied render-time block (v0.0.27's plain one included), and the documented Bash(goc:*) grant does not cover the compound preamble f20a8920 introduced, so main's goc-preamble skills would not load even for granted users. Fixed by exact allowed-tools entries per block, Preflight and kickoff routing a denied goc call to claude-kickoff, a missing-deck notice in goc, and a smoke that allows the namespaced plugin skills. Open: the CI dry-run and the release itself."
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
  - [x] PROCESS: fix shape decided and recorded in this card — e.g. (a) carry the kickoff routing where a denied block cannot hide it (skill description, a hook, or a preamble that needs no permission), (b) give the generic preflight a route to the host complement `claude-kickoff`, or put the permission remediation back into kickoff, (c) align Path B's expectations with the current skills and Claude Code behavior
  - [x] EMPIRICAL: countercheck recorded — Path B with v0.0.27's skills under current Claude Code, which decides between f20a8920 and a Claude Code behavior change
  - [ ] TDD: Path B passes on main in a workflow run (dry-run release or equivalent)
  - [ ] MECHANICAL: the next release is published to PyPI, npm and ClawHub
  - [x] MECHANICAL: `uv run goc validate` passes
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

## Attribution (countercheck, Claude Code 2.1.303)

Both candidates were measured, not argued (runs isolated from user settings; key lines in `log.md`):

- **The abort is a Claude Code behavior change, not f20a8920.** Path B with v0.0.27's skills aborts
  identically on its plain `` !`goc` `` block. v0.0.27's 2026-07-14 pass is not reproducible today.
- **f20a8920 adds a second break on top.** A user who granted the documented `Bash(goc:*)` loads
  v0.0.27's skills, but not main's: prefix rules do not match the compound bootstrap routing, whether
  granted by flag or settings file. Shipping main as-is would have locked out every granted user.
  Release smoke Path A allows blanket `Bash`, so it could not catch this.
- **A skill can pre-approve its own blocks.** An exact `Bash(<block>)` entry in the skill's
  `allowed-tools` frontmatter loads the body even without any user grant. Claude Code refuses to
  pre-approve command substitution (`$(...)`) and the old standup `python3 -c` filter even with an
  exact rule.
- **Without a deck, goc gave the Preflight nothing to route on.** `goc` printed only `No cards match`,
  the same line as an empty queue.

## Fix

- **(a)** audit-deck, pull-card, next-card, refine-deck, retrospective and standup carry one exact
  `'Bash(<block>)'` entry per `!` block in `allowed-tools`, a YAML single-quoted scalar each.
  standup's branch line now comes from `git status -sb` and its impediment view from
  `goc --waiting`, replacing the two blocks Claude Code would not pre-approve.
  `tests/test_skill_preamble_blocks.py` pins block/entry parity.
- **(b)** The shared Preflight and kickoff Stage 0 route a denied `goc` call to the host complement
  (`claude-kickoff`, which adds `Bash(goc:*)` to `permissions.allow`). goc's read views name a
  missing deck on stderr with the Preflight's `no such file or directory: .game-of-cards/deck/`, and
  `goc new` shares that wording.
- **(c)** The release smoke allows the skills by their namespaced plugin name, which Claude Code
  requires once a skill declares `allowed-tools`. Path B checks that the remediation arrives through
  the kickoff → claude-kickoff hand-off.

Verified locally with this branch's plugin under CI-like conditions: Path A and Path B pass, and the
granted-user run loads the audit-deck body. The CI dry-run and the publish remain.

## Context

Found while updating an OpenClaw deployment to v0.0.28. The OpenClaw plugin has no `!` blocks and is
not affected; that deployment runs the plugin from the `v0.0.28` tag, unpublished, to get the summary
gate from #12. This card blocks only the publish. Related:
`local-release-smoke-script-no-longer-mirrors-the-ci-smoke-job` (the local mirror of the same smoke).

## Decision

*Resolved 2026-10-22T05:39:15Z:* Fix shape (a)+(b)+(c): every goc-preamble skill pre-approves its own render-time blocks with one exact Bash(<block>) allowed-tools entry each; the Preflight and kickoff route a denied goc call to the host complement claude-kickoff; goc names a missing deck; the smoke allows the namespaced plugin skills

*Reasoning:* Countercheck on Claude Code 2.1.303: any denied render-time block aborts the whole skill load, v0.0.27's plain goc block included, so this is a Claude Code behavior change rather than f20a8920; the documented Bash(goc:*) grant does not cover f20a8920's compound block while it covers v0.0.27's, so main as-is would regress every granted user; exact allowed-tools entries load the body

