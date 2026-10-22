---
title: deciding-a-card-parked-while-active-strands-it-outside-the-pull-queue
summary: "Skill(pull-card) claims a card before it can hit a judgement call, so the Andon cord leaves the card parked at status active behind a raised gate. goc decide lowered the gate but never touched status, leaving active plus human_gate none, the shape of a live agent claim, so the decided card was missing from goc, goc --ready and the pull-card workflow's launch count while the verb's own Next line said any agent could claim it. Verified by reproduce.py and fixed: goc decide now returns a card parked while active to open, keeps its worker, and says so."
status: done
stage: null
contribution: high
created: "2026-09-28T01:32:05Z"
closed_at: "2026-10-01T04:53:17Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [x] TDD: a reproduce.py claims a card, raises its gate by hand (the pull-card Andon step), runs `goc decide`, and asserts the card is reachable by the next `pull-card` (listed by `goc --ready --json`) — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] TDD: a regression test pins the chosen round trip: claim → raise gate → `goc decide` → the card is pullable again, and `goc decide`'s `Next:` line tells the truth about it
  - [x] MECHANICAL: `decide-card/SKILL.md` (lines 16-17, 51, 139), `deck/SKILL.md:167-168` and `deck/reference.md:79-80` describe what happens to a card decided while `active`; drop the `unverified` tag once reproduce.py lands
worker: {who: "claude[bot]", where: main}
---

# Deciding a card parked while active strands it outside the pull queue

> **Verified and fixed 2026-10-01.** `reproduce.py` exits 1 on the
> pre-fix engine (the decided card stays `active` and leaves the queue)
> and exits 0 on the fix. `goc decide` now returns a card parked while
> `active` to `open` and says so.

## Location

- `goc/templates/skills/pull-card/SKILL.md:56-57` claims first:
  "`Skill(advance-card) <title> active` to claim. (The status flip is the
  soft lock against parallel sessions.)"
- `goc/templates/skills/pull-card/SKILL.md:138-140` then raises the gate
  on that claimed card when it hits a judgement call: "raise the gate to
  `decision` or `session`, write a `## Decision required` body section,
  commit the gate-and-body update." Nothing releases the claim.
- `goc/templates/skills/standup/SKILL.md:111-112` names this the ordinary
  shape: "claim → work → hit a judgement call → raise the gate, which
  leaves the card parked at `active`."
- `goc/engine.py:6948` `_cmd_decide` is the fix site. `releases_claim`
  (`:6983`) flips `status` to `open` next to the gate (`:7001`), and the
  `Next:` line for that case (`:7042-7046`) tells a session that wants to
  keep the card how to re-claim it.
- `goc/templates/skills/pull-card/SKILL.md:32-34`: "Treat any listed
  active card as a soft lock. Do not claim the same card …"
- `.github/workflows/pull-card.yml:63` and `:107`: the launch gate counts
  `goc --status open --human-gate none --json`.

## What was broken

The skills promised a round trip that the state machine did not make.
`decide-card/SKILL.md` said "Status stays `open`, so the next `pull-card`
claims and implements per the recorded decision", and `deck/SKILL.md` and
`deck/reference.md` repeated it.

That held only for a card parked while `open`. In the common case the
card is parked while `active`, per the pull-card flow above. There
`goc decide` left `status: active` plus `human_gate: none`, which is
exactly what a live agent claim looks like. As a result:

- `goc` and `goc --ready` never listed the card, because both require
  `status: open`.
- A pull-card session read the card in its `--status active` context
  block as someone's soft lock, and left it alone.
- The scheduled `pull-card.yml` counts `--status open --human-gate none`.
  If nothing else was ready, it never launched at all.
- The verb's own `Next:` line told the human the opposite.

This is a sibling of
[active-state-conflates-being-worked-on-with-parked-at-human-gate](../active-state-conflates-being-worked-on-with-parked-at-human-gate/),
which covers how parked-`active` cards are *labelled* while still gated.
This card covers what becomes of them after the decision.

## Verification

`reproduce.py` drives the real CLI through the pull-card round trip in a
scratch git repo: `goc new` (gate `none`), author the DoD,
`goc status active`, raise `human_gate: decision` by hand and commit,
then `goc decide`. Before the fix:

```text
status / gate after decide:                 active / none
listed by `goc --ready --json`:             False
counted by pull-card.yml's launch query:    False
listed by `goc --status active` (soft lock): True
Next: line promises the card is claimable:  True
FAIL: the decided card is stranded at status active + human_gate none
```

After the fix:

```text
probe-card: decision recorded; gate decision → none
probe-card: active → open (the claim parked behind the gate is released)
Next: gate lowered to none — any agent can now claim this card. goc to see the queue; to keep working it in this session, goc status probe-card active.
status / gate after decide:                 open / none
listed by `goc --ready --json`:             True
counted by pull-card.yml's launch query:    True
listed by `goc --status active` (soft lock): False
PASS: the decided card is back in the pull queue on every surface.
```

`tests/test_decide_releases_parked_active_claim.py` pins the round trip.
It fails on the pre-fix engine and passes on the fix.

## Fix

This takes the recommended direction. When `goc decide` lowers the gate
on an `active` card, it also flips `status` to `open`, in the same write
and the same `decide:` commit:

- **Output.** The verb prints `<title>: active → open (the claim parked
  behind the gate is released)`. Its `Next:` line keeps the "any agent
  can now claim this card" promise, which is now true, and adds
  `goc status <title> active` for a session that decided the card itself
  and wants to keep working it.
- **Journal.** The log entry records `Status active → open` after
  `Gate <prior> → none`.
- **Worker.** The release is the same one `goc status <title> open`
  performs: `worker` stays as the designation, and the next claim
  re-stamps `where`.
- **Untouched.** Cards parked while `open` are unchanged. Terminal cards
  (the gate-repair path) stay closed.

Alternatives not taken:

- Making pull-card release its claim when it raises the gate. That would
  change the documented "parked at `active`" shape that standup and the
  umbrella card build on.
- Teaching `--ready` that `active` + `none` without a live worker is
  pullable. That needs a liveness signal the deck does not carry.

Interaction to keep in mind: the held draft
[escalate-repeatedly-auto-released-cards-without-an-attempt-counter](../escalate-repeatedly-auto-released-cards-without-an-attempt-counter/)
plans to hook the `active → open` release in `_cmd_status`. The release
added here lives in `_cmd_decide` and is a decided handoff, not an
unattended give-up, so it must not arm that ladder.

Surfaced by: general-purpose audit hunter (shipped skills vs CLI
contract), 2026-09-28.
