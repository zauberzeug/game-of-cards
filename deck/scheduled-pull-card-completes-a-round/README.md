---
title: scheduled-pull-card-completes-a-round
summary: "The cloud Pull Card workflow now reaches the agent step (creds work), but the agent has never finished a `Skill(pull-card)` round end-to-end on GitHub Actions: it gets cut off by `--max-turns`, blocked by tool permission denials, or otherwise stops short of closing a card. This umbrella card grows with each obstacle we discover until a scheduled run actually closes a deck card."
status: open
stage: null
contribution: high
created: 2026-05-05
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, infra, meta-fix]
definition_of_done: |
  - [ ] A scheduled (`schedule:` cron) run of `.github/workflows/pull-card.yml` finishes with `conclusion: success`.
  - [ ] That same run produces at least one commit on `main` whose author is the cloud worker and whose diff closes (or advances) a deck card — i.e. the autonomous worker actually drained one item from the queue.
  - [ ] The verification run URL is recorded in this card's `log.md`.
  - [ ] Every obstacle encountered during this work is captured in this card's `## Findings` section (one entry per obstacle: what failed, run URL, the fix that was tried, and whether it worked).
---

# Scheduled pull-card actually completes a round

## Summary

`unblock-scheduled-pull-card-secret` proved the credential boundary works. The
cloud `pull-card` workflow now reaches the Claude agent step. But the agent
has not yet completed a single `Skill(pull-card)` round end-to-end on GitHub
Actions — every run so far has been cut short before the agent can close a
deck card.

This card is intentionally an *umbrella*: rather than splitting every new
failure mode into its own card up front, we accumulate findings here until
the workflow closes a deck card on schedule. We split into smaller cards only
when the human asks ("let's split this").

## Location

- `.github/workflows/pull-card.yml` (the workflow)
- `.claude/skills/pull-card/SKILL.md` and `goc/templates/skills/pull-card/SKILL.md` (the skill body the agent runs)

## What's broken

### Finding 1 — `--max-turns 40` is too low (run [25358540152](https://github.com/zauberzeug/game-of-cards/actions/runs/25358540152))

A `workflow_dispatch` run on `main` after the credential fix:

```text
{
  "type": "result",
  "subtype": "error_max_turns",
  "is_error": true,
  "duration_ms": 238799,
  "num_turns": 41,
  "total_cost_usd": 0.87819145,
  "permission_denials_count": 1
}
error: Claude Code returned an error result: Reached maximum number of turns (40)
```

Workflow excerpt that capped it:

```yaml
claude_args: |
  --max-turns 40
  --allowedTools "Bash(uv run goc *),Bash(uv run python *),Bash(uv build),Bash(pre-commit run *),Bash(git status *),Bash(git diff *),Bash(git log *),Bash(git config *),Bash(git add *),Bash(git commit *),Bash(git push *),Edit,Write"
```

The agent burned 41 turns over 4m13s and was terminated mid-flight.
`permission_denials_count: 1` confirms the agent also tried at least one
Bash command not in the allowlist and lost a turn to the denial.

### Finding 2 — restrictive `--allowedTools` causes denials mid-round

Same run, `permission_denials_count: 1`. Common candidates the agent likely
needs but can't call: `Bash(gh *)` (PR/issue context), bare `goc ...` (the
allowlist requires the `uv run` prefix), read-only inspection tools
(`Bash(cat *)`, `Bash(grep *)`, `Bash(ls *)`, `Bash(find *)`, `Read`, `Grep`,
`Glob`, `LS`).

A denial is doubly bad in cloud mode: the agent can't fall back to a human
to approve the tool, so it has to retry or work around — burning more turns
on a budget that's already too small.

## Why it matters

The whole point of `pull-card.yml` is to drain the queue without a human
session staying open. If no scheduled run ever closes a card, the autonomous
loop is theoretical only.

## Plan / interventions to try

In rough priority order — **append a new "Finding N" entry to this card after
each attempt, with the run URL and outcome**:

1. **Bump `--max-turns` from 40 → 200.** Rationale (per user): once a round
   is started it's better to push through to a sensible completion than to
   abort mid-flight at turn 41 with $0.88 sunk and no card closed. 200 is
   a generous ceiling that will not be hit by a healthy round; it's a
   safety net against runaway loops, not a budget.
2. **Switch the agent into auto / bypass-permissions mode** so allowlist
   gaps don't cost turns. The cloud runner has no human to approve, and
   the workflow's GitHub-token + ephemeral-VM blast radius is already
   bounded by the runner's permissions. Likely shape: replace the
   `--allowedTools` enumeration with `--permission-mode bypassPermissions`
   (or equivalent) in `claude_args`, OR keep `--allowedTools` but broaden
   it to include `Bash(gh *)`, `Bash(cat *)`, `Bash(grep *)`,
   `Bash(ls *)`, `Bash(find *)`, `Read`, `Grep`, `Glob`, `LS`. Pick
   whichever the `claude-code-action@v1` interface actually supports
   without compromising the runner.
3. **Pre-flight queue check before launching the LLM.** Add a workflow
   step that runs `uv run goc --status open --human-gate none --json | jq 'length'`
   *before* `anthropics/claude-code-action@v1` and skips the agent step
   when the count is zero. The autonomous worker only acts on `human_gate: none`
   open cards; if there are none, the LLM has nothing to do and the
   30-minute tick should exit immediately rather than spend tokens
   discovering an empty queue.
4. After (1)–(3), trigger a manual `workflow_dispatch` and let the agent
   try a real round. Inspect the SDK result event for the next obstacle.

We deliberately *do not* speculate further interventions in advance. Each
new finding gets appended below as we learn it.

## Findings (append-only — grow this card here)

*(Findings 1 and 2 above are the seed; subsequent attempts append here.)*

## Refining the DoD

The DoD intentionally encodes a *behavioral* outcome ("a scheduled run
closes a deck card") not a checklist of fixes. Any number of fixes might be
needed; the only thing that proves we're done is the autonomous worker
actually draining one item from the queue on its own.
