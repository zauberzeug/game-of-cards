---
title: run-autonomous-agent-workflows-at-max-effort
summary: "The three autonomous-agent workflows (pull-card, audit-deck, refine-deck) pass no `--effort` in `claude_args`, so every unattended run uses the CLI default. Add `--effort max` to all three so the cloud agents reason at full depth on long-horizon card work. Second axis of the same standing capability decision as float-autonomous-workflows-back-to-opus-alias, which set the model."
status: done
stage: null
contribution: low
created: "2026-07-26T05:56:36Z"
closed_at: "2026-07-26T05:57:58Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra]
definition_of_done: |
  - [x] MECHANICAL: `.github/workflows/pull-card.yml` passes `--effort max` in `claude_args`
  - [x] MECHANICAL: `.github/workflows/audit-deck.yml` passes `--effort max` in `claude_args`
  - [x] MECHANICAL: `.github/workflows/refine-deck.yml` passes `--effort max` in `claude_args`
  - [x] EMPIRICAL: `claude --help` confirms `--effort` accepts `max` on the CLI version the pinned `claude-code-action@v1` resolves to
  - [x] MECHANICAL: closed card float-autonomous-workflows-back-to-opus-alias cross-referenced, so the model and effort axes are discoverable from each other
worker: {who: Rodja Trappe, where: main}
---

# run-autonomous-agent-workflows-at-max-effort

Set `--effort max` on the three cron-driven autonomous agents so
unattended runs reason at full depth instead of the CLI default.

## Location

- `.github/workflows/pull-card.yml:98` — `claude_args` block
- `.github/workflows/audit-deck.yml:74` — `claude_args` block
- `.github/workflows/refine-deck.yml:78` — `claude_args` block

## What changes

Each `claude_args` block gains one line:

```yaml
claude_args: |
  --max-turns 120
  --permission-mode bypassPermissions
  --model opus
  --effort max
```

`--effort` is a first-class Claude Code CLI flag accepting
`low | medium | high | xhigh | max`; without it the session runs at the
CLI default. The workflows pin `anthropics/claude-code-action@v1` — a
floating major tag — so the resolved CLI is recent enough to carry the
flag.

## Why it matters

Effort and model are two axes of the *same* standing decision, and
until now only one of them was set. The fleet's model override has been
deliberately managed across five cards
([pin-opus-on-autonomous-github-workflows](../pin-opus-on-autonomous-github-workflows/)
→ [float-opus-alias-on-autonomous-github-workflows](../float-opus-alias-on-autonomous-github-workflows/)
→ [pin-autonomous-workflows-to-opus-while-fable-5-disabled](../pin-autonomous-workflows-to-opus-while-fable-5-disabled/)
→ [re-pin-autonomous-workflows-to-fable-5-after-re-enable](../re-pin-autonomous-workflows-to-fable-5-after-re-enable/)
→ [float-autonomous-workflows-back-to-opus-alias](../float-autonomous-workflows-back-to-opus-alias/)),
while effort silently rode the default the whole time.

These three workflows are the repo's own dogfood loop — `pull-card`
implements and closes real cards, `audit-deck` files new defect cards,
`refine-deck` mutates card frontmatter and bodies. That is long-horizon
agentic work with no human in the loop to catch shallow reasoning, which
is the workload profile `max` exists for.

## Cost consequence (accepted)

`max` is the most expensive effort level, and it lands on top of a
cadence increase made in the same week: `pull-card` moved from every
12 h to every 3 h (2 → 8 runs/day) and `audit-deck` / `refine-deck`
from every 2 days to daily. Token spend per run rises with effort *and*
run count rises 4× for pull-card, so the two changes compound rather
than trade off. This is the maintainer's explicit call; recorded here so
a future reader looking at a spend spike finds the cause rather than
re-deriving it.

The mitigating factor already in place is `MAX_ITERATIONS` on
`pull-card.yml`, which bounds the self-retrigger chain per cron tick —
see [cap-daily-autonomous-pull-queue-at-four-cards-to-cut-token-spend](../cap-daily-autonomous-pull-queue-at-four-cards-to-cut-token-spend/).
If spend needs trimming later, that cap and the cadence are the levers
to reach for before dropping effort back.

## Fix

Three one-line `claude_args` additions, one per workflow. Repo-local CI
only — no engine, template, or plugin-mirror surface is touched, and
`goc install` does not ship these files. `claude.yml`,
`claude-code-review.yml`, and the `release.yml` smoke jobs keep the
action default and stay out of scope, as in every prior card in this
family.
