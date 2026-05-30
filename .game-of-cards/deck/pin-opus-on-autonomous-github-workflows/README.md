---
title: pin-opus-on-autonomous-github-workflows
summary: "Pin Opus 4.7 on the autonomous claude-code-action workflows so cron-driven implementation work doesn't silently fall back to Sonnet."
status: done
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances: []
advanced_by: []
tags: [infra, story]
definition_of_done: |
  - [x] `.github/workflows/pull-card.yml` adds `--model claude-opus-4-7` to `claude_args`.
  - [x] `.github/workflows/audit-deck.yml` adds `--model claude-opus-4-7` to `claude_args`.
  - [x] Skill bodies remain runtime-agnostic (no `model:` frontmatter, no model name in skill markdown) so Codex / OpenClaw / OpenCode consumers are unaffected.
  - [x] Verified by inspection of a subsequent run log that `"model": "claude-opus-4-7"` replaces the previous `claude-sonnet-4-6` lines (or noted as deferred until next scheduled trigger).
worker: {who: Rodja Trappe, where: main}
---

# pin-opus-on-autonomous-github-workflows

> Later evidence (2026-05-30): the explicit-pin preference recorded
> below was reversed. Both workflows now use the floating `--model opus`
> alias so autonomous runs auto-pick the strongest Opus without a manual
> bump each release. See
> [float-opus-alias-on-autonomous-github-workflows](../float-opus-alias-on-autonomous-github-workflows/).

The autonomous queue-drainer (`pull-card.yml`) and the daily audit
filer (`audit-deck.yml`) both invoke `anthropics/claude-code-action@v1`
without specifying a model. The action's hardcoded default is Sonnet,
so every cron run implements cards as Sonnet 4.6 — confirmed in run
[25593500769](https://github.com/zauberzeug/game-of-cards/actions/runs/25593500769/job/75135295082)
where every assistant turn logs `"model": "claude-sonnet-4-6"`.

Implementation-quality work on autonomous runs should default to
Opus, not Sonnet, given:

1. The pull-card drainer ships actual code changes that get committed
   and pushed without human review.
2. The audit-deck filer writes card bodies that downstream Opus runs
   then consume as briefings; framing quality compounds.
3. The cost delta (~5×) is acceptable for a small project where the
   queue is short and runs are bounded by `--max-turns`.

## Why this is a workflow-level fix, not a skill-level one

`pull-card`, `audit-deck`, and every other GoC skill are deliberately
runtime-agnostic — they wrap `goc <verb>` calls and contain no
runtime-specific configuration (no `--model`, no `--max-turns`, no
`anthropic-api-key`). The same skill markdown installs into Codex,
OpenClaw, OpenCode, and Claude Code without modification.

Model choice is a **runtime dispatcher** concern:

- Local `/loop pull-card` inherits the user's Claude Code session
  model — no fix needed.
- `claude-code-action@v1` in CI has no parent session and defaults to
  Sonnet — fix lives in the workflow YAML, alongside other
  Anthropic-specific knobs (`--max-turns`, OAuth token, runner OS).

`.github/workflows/*.yml` are already Anthropic-specific and have no
counterpart in non-Claude-Code consumer repos, so pinning a Claude
model name there does not leak into the portable surface.

## Out of scope

- `claude.yml` (interactive `@claude` on PRs/issues) and
  `claude-code-review.yml` (PR code-review pass) keep the Sonnet
  default. Both are short-lived, human-supervised flows where Sonnet
  is adequate; bumping them would inflate cost without quality gain
  for the dominant Q&A use case. Can be revisited per-workflow if
  evidence emerges.
- Configurability via `vars.GOC_AUTONOMOUS_MODEL` was considered and
  declined — hardcoding `claude-opus-4-7` is simpler to read in run
  logs and aligned with the dogfooding repo's preference for explicit
  reproducible references over implicit auto-rolling aliases.

## References

- Run log evidence:
  https://github.com/zauberzeug/game-of-cards/actions/runs/25593500769/job/75135295082
- `claude-code-action@v1` docs: the `model:` input is deprecated;
  `claude_args: --model <id>` is the supported lever.
