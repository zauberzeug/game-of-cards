---
title: loop-examples-trail-a-bare-interval-that-claude-code-does-not-parse
summary: "The pull-card skill and the deck skill's reference show `/loop pull-card 30m`, but Claude Code's documented /loop grammar accepts an interval only as a leading bare token (`/loop 30m /pull-card`) or as a trailing clause (`every 2 hours`). The example therefore sits outside the documented grammar, and it now contradicts the interval-first form that kickoff and claude-kickoff show."
status: active
stage: null
contribution: low
created: "2026-10-08T04:45:19Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — no shipped template under `goc/templates/` shows a backticked `/loop` example whose interval trails as a bare token
  - [ ] MECHANICAL: `pull-card/SKILL.md` "Pairs naturally with" and `deck/reference.md` use the documented interval-first form `/loop 30m /pull-card`; plugin and dogfood mirrors regenerated
  - [ ] TDD: a regression test under `tests/` fails on a trailing-bare-interval `/loop` example in any shipped template
worker: {who: "claude[bot]", where: main}
---

# `/loop` examples trail a bare interval that Claude Code does not parse

## Location

- `goc/templates/skills/pull-card/SKILL.md:184`, in "Pairs naturally with":
  `` `/loop pull-card 30m` — drains the queue while the user works in
  another session. ``
- `goc/templates/skills/deck/reference.md:67`: `` runs on `/loop pull-card
  30m` or `/schedule pull-card ...` ``

## What's broken

Claude Code's scheduled-tasks documentation
(`code.claude.com/docs/en/scheduled-tasks`) defines where an interval may
go: "The interval can lead the prompt as a bare token like `30m`, or trail
it as a clause like `every 2 hours`." The bundled `loop` skill's own usage
line gives the leading form, `/loop 5m /foo`. It shows a skill passed as the
prompt, `/loop 20m /review-pr 1234`, re-running the skill each iteration.

`/loop pull-card 30m` does neither. The leading token `pull-card` is not an
interval and the trailing `30m` is a bare token, not an `every …` clause.
Per the documented grammar there is no interval, so the loop treats
`pull-card 30m` as a prompt with a self-chosen cadence. That is not the
fixed 30-minute drain the sentence promises. It also omits the `/` that
makes `pull-card` a skill invocation rather than prose.

`kickoff` Stage 6 and `claude-kickoff`'s autonomy recipe now show the
documented form `/loop 30m /pull-card`. They were fixed by
[kickoff-autonomy-choice-hands-off-to-host-complements-that-carry-no-recipe](../kickoff-autonomy-choice-hands-off-to-host-complements-that-carry-no-recipe/),
which surfaced this card. The shipped skills disagree with each other about
the one command they recommend for a supervised drain.

## Empirical evidence

`reproduce.py` scans every `.md` / `.yaml` file under `goc/templates/` for
backticked `/loop …` examples whose first argument is not an interval
while a bare interval token trails. Before the fix it printed:

```
trailing bare interval: goc/templates/skills/deck/reference.md:67: `/loop pull-card 30m`
trailing bare interval: goc/templates/skills/pull-card/SKILL.md:184: `/loop pull-card 30m`
CONFIRMED: 2 /loop example(s) outside the documented grammar
```

The runtime consequence, a self-paced loop instead of a fixed 30-minute
one, is inferred from the documented grammar. It was not observed: a
headless session cannot exercise `/loop` without scheduling real
recurring work.

## Fix

Rewrite both examples to `/loop 30m /pull-card`, regenerate the mirrors
with `scripts/sync_plugin_assets.py` and `scripts/port_skills_to_openclaw.py`,
and add a regression test that applies the same scan to every shipped
template. `/schedule pull-card weekday 09:00` is left alone because
`/schedule` takes a natural-language description, not the `/loop` grammar.
