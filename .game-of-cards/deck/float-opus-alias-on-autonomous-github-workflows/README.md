---
title: float-opus-alias-on-autonomous-github-workflows
status: done
stage: null
contribution: low
created: "2026-05-30T19:23:28Z"
closed_at: "2026-05-30T19:24:50Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra, story]
definition_of_done: |
  - [x] MECHANICAL: `.github/workflows/pull-card.yml` passes `--model opus` (not a pinned version) in `claude_args`.
  - [x] MECHANICAL: `.github/workflows/audit-deck.yml` passes `--model opus` (not a pinned version) in `claude_args`.
  - [x] PROCESS: closed card `pin-opus-on-autonomous-github-workflows` amended with a forward pointer (README `> Later evidence:` line + dated `log.md` entry) recording that its "explicit pin over auto-rolling alias" preference was reversed and why.
  - [x] PROCESS: skill bodies remain runtime-agnostic (no `model:` frontmatter, no model name in skill markdown) — unchanged by this card.
worker: {who: Rodja Trappe, where: main}
---

# float-opus-alias-on-autonomous-github-workflows

Switch the two autonomous `claude-code-action` workflows from the
pinned model id `claude-opus-4-7` to the floating alias `opus`, so
cron-driven runs auto-pick the strongest available Opus without a
manual workflow edit each Opus release.

## What changed

`.github/workflows/pull-card.yml` and `.github/workflows/audit-deck.yml`
each passed `--model claude-opus-4-7` in their `claude_args`. That id
went stale the moment Opus 4.8 shipped — the autonomous runners kept
implementing cards on a now-superseded model until a human edited the
YAML. Both lines are now:

```yaml
claude_args: |
  --max-turns <N>
  --permission-mode bypassPermissions
  --model opus
```

`opus` is a Claude Code **floating alias**: "Aliases point to the
recommended version for your provider and update over time." On the
Anthropic first-party platform the CI auth uses, `opus` resolves to the
latest Opus (4.8 today), so the runners track the strongest tier
automatically. (`latest` is **not** a valid `--model` value; `opus` is
the documented way to express "newest/strongest Opus".)

The cheap Sonnet audit pass inside `goc/engine.py`
(`claude --model sonnet -p …`) is unrelated and intentionally left
pinned to the `sonnet` alias.

## Why this reverses a documented decision

The closed card
[pin-opus-on-autonomous-github-workflows](../pin-opus-on-autonomous-github-workflows/)
(2026-05-09) deliberately chose the *pinned* id and explicitly declined
auto-rolling aliases:

> Configurability via `vars.GOC_AUTONOMOUS_MODEL` was considered and
> declined — hardcoding `claude-opus-4-7` is simpler to read in run
> logs and aligned with the dogfooding repo's preference for explicit
> reproducible references over implicit auto-rolling aliases.

That tradeoff was sound when filed (a single current Opus, no drift
yet). It has since inverted: pinning means the autonomous loops silently
run a stale model between releases and someone must remember to bump the
literal each time. The owner's call is now to prefer "always strongest"
over "reproducible pin in logs". The lost property — a self-chosen
version string in the run log — is mitigated because the resolved
concrete id (e.g. `claude-opus-4-8`) still appears in each run's
assistant-turn logs; it is reported rather than pre-declared.

The pin card stays `done` (its work shipped and was correct for its
window); this card records the superseding preference and back-points to
it per the repo's "closure is not frozenness" rule.

## Why it matters

Both workflows run under `--permission-mode bypassPermissions` with no
human in the loop: `pull-card.yml` commits and pushes real code, and
`audit-deck.yml` writes card briefings that downstream Opus runs consume.
Keeping them on the strongest current Opus — without a recurring manual
bump — is where model quality compounds most.

## Out of scope

- `claude.yml` and `claude-code-review.yml` keep the Sonnet default
  (short-lived, human-supervised) — unchanged, matching the pin card's
  original scoping.
- No skill-body or portable-surface change: model choice remains a
  runtime-dispatcher concern living only in the Anthropic-specific
  workflow YAML.
