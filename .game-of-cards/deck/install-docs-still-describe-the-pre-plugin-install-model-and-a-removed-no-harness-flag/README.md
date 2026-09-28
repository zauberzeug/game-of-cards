---
title: install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag
summary: "UNVERIFIED. ABOUT.md documents a --no-harness flag that goc install now rejects (exit 2) and says --agents claude writes .claude/skills/ and gives OpenCode the skill files, while README.md:46 sends OpenCode users to plain goc install; since the plugin became the Claude default, neither invocation vendors any skill. goc.md:89 repeats the old model, and tests/test_guidance_accuracy.py:555 requires that false parenthetical, so correcting it turns the guard red."
status: open
stage: null
contribution: high
created: "2026-09-28T01:34:50Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py extracts every install flag and per-flag effect `ABOUT.md` (lines 72-80), `README.md:46` and `goc.md:89` state, runs each against a scratch repo, and reports the claims the installer contradicts — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] MECHANICAL: the three surfaces describe the plugin-default model: `--agents claude` writes no skills unless `--local-skills` is passed, `--no-harness` is gone, and OpenCode / generic-runner users are told which invocation actually vendors skill files
  - [ ] TDD: `tests/test_guidance_accuracy.py`'s `test_claude_skill_count_matches_payload` no longer requires the false "(same as `goc install --agents claude`)" parenthetical to match; drop the `unverified` tag once reproduce.py lands
---

# Install docs still describe the pre-plugin install model and a removed `--no-harness` flag

> **UNVERIFIED.** Surfaced by an audit hunter on the docs-vs-code seam on
> 2026-09-28. The filing agent re-read and confirmed the citations and
> re-ran the removed flag. No `reproduce.py` was written this round; the
> falsification recipe is below.

## Location

- `ABOUT.md:74`: "`--agents claude` writes `.claude/skills/`,
  `.claude/hooks/` (one script per file under `goc/templates/hooks/`),
  and `CLAUDE.md`."
- `ABOUT.md:76`: "`--no-harness` installs project state and guidance
  only — no skills, no hooks, no agent-specific files."
- `ABOUT.md:78`: "Explicit `--agents`, `--claude`, `--codex`, and
  `--no-harness` flags override detection for scripted installs."
- `ABOUT.md:80`: "OpenCode is a free path: it already reads
  `.claude/skills/`, so `goc install --agents claude` gives OpenCode the
  skill files …"
- `README.md:46`, the Generic CLI bullet: "`goc install` from the project
  root. This is the path for OpenCode, custom runners, or running `goc`
  by hand."
- `goc.md:89`: "**16 GoC skills** (same as `goc install --agents
  claude`)".

What the code actually does:

- `goc/install.py:586-592` (`_should_use_local_skills`): "Claude defaults
  to the plugin path; --local-skills opts in to vendored." It returns
  `agent != "claude" or local_skills`.
- `goc/cli.py:59-73` defines no `--no-harness`. Running
  `goc install --no-harness` exits 2 with
  `goc install: error: unrecognized arguments: --no-harness`. The flag
  was added in 32cbac34 (2026-05-05); e69dc698 (2026-05-07) made the
  plugin the Claude default.
- `tests/test_guidance_accuracy.py:555` requires the false parenthetical
  to be present: its regex is
  `\*\*(\d+) GoC skills\*\* \(same as \`goc install --agents claude\`\)`.
  So correcting `goc.md:89` fails the guard with "goc.md lost its Claude
  plugin skill-count bullet."

## Hypothesis

Three reader-facing surfaces still describe the install model from before
the plugin became the default. As a result:

- A scripted install copied from `ABOUT.md` fails on `--no-harness`.
- OpenCode and other-runtime users who follow `README.md:46` or
  `ABOUT.md:80` get an install with no skill files at all. The hunter's
  scratch run of `goc install --agents claude` found 0 `SKILL.md`, no
  `.claude/` directory, and `skills_source: plugin`.
- The one guard on `goc.md:89` pins the stale wording in place.

`ABOUT.md` is published at `/about/` and linked from `llms.txt`, so the
dead flag is also what an LLM reads when it installs GoC. The closed card
`claude-install-defaults-to-plugin-path` updated `AGENTS.md`, `CLAUDE.md`
and `goc.md`, but not `ABOUT.md`. The closed card
`cli-reference-plugin-sections-describe-a-payload-goc-no-longer-ships`
fixed the count and kept the parenthetical. This is another member of
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/).

## Why deferred

The citations are confirmed, and the removed-flag rejection was re-run by
the filing agent. No `reproduce.py` is committed this round.

## Falsification recipe

In a scratch git repo:

1. Run `goc install --no-harness`. Expect exit 2.
2. In a fresh repo, run `goc install --agents claude` and count
   `SKILL.md` files under the repo.

If the flag is accepted, or the install vendors skill files, the
hypothesis is disproved.

Surfaced by: general-purpose audit hunter (human-facing docs vs code),
2026-09-28.
