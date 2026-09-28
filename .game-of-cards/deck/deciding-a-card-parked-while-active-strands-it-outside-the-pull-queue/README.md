---
title: deciding-a-card-parked-while-active-strands-it-outside-the-pull-queue
summary: "UNVERIFIED. Skill(pull-card) claims a card before it can hit a judgement call, so the Andon cord leaves the card parked at status active behind a raised gate; goc decide then lowers the gate but never touches status. The result, active plus human_gate none, is what a live agent claim looks like, so the decided card is missing from goc, goc --ready and the pull-card workflow's launch count, while decide-card, deck and the verb's own Next line promise it is back in the queue."
status: open
stage: null
contribution: high
created: "2026-09-28T01:32:05Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py claims a card, raises its gate by hand (the pull-card Andon step), runs `goc decide`, and asserts the card is reachable by the next `pull-card` (listed by `goc --ready --json`) — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] TDD: a regression test pins the chosen round trip: claim → raise gate → `goc decide` → the card is pullable again, and `goc decide`'s `Next:` line tells the truth about it
  - [ ] MECHANICAL: `decide-card/SKILL.md` (lines 16-17, 51, 139), `deck/SKILL.md:167-168` and `deck/reference.md:79-80` describe what happens to a card decided while `active`; drop the `unverified` tag once reproduce.py lands
---

# Deciding a card parked while active strands it outside the pull queue

> **UNVERIFIED.** Surfaced by an audit hunter on the shipped-skills-vs-CLI
> seam on 2026-09-28. The filing agent re-read and confirmed the
> citations. No `reproduce.py` was written this round; the falsification
> recipe is below.

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
- `goc/engine.py:6900` `_cmd_decide` flips only `human_gate`, then prints
  (`:6977`): "Next: gate lowered to none — any agent can now claim this
  card. goc to see the queue."
- `goc/templates/skills/pull-card/SKILL.md:32-34`: "Treat any listed
  active card as a soft lock. Do not claim the same card …"
- `.github/workflows/pull-card.yml:63` and `:107`: the launch gate counts
  `goc --status open --human-gate none --json`.

## Hypothesis

The skills promise a round trip that the state machine does not make.
`decide-card/SKILL.md:16-17` says:

> Status stays `open`, so the next `pull-card` claims and implements per
> the recorded decision.

The same promise appears at `:51` ("`open` stays `open`"), at `:139`, at
`deck/SKILL.md:167-168` and at `deck/reference.md:79-80`.

That holds only for a card that was parked while `open`. For the common
case, parked while `active` per the pull-card flow above, `goc decide`
leaves `status: active` plus `human_gate: none`. That pair is exactly what
a live agent claim looks like, so:

- `goc` and `goc --ready` never list the card, because both require
  `status: open`.
- A pull-card session reads the card in its `--status active` context
  block as someone's soft lock, and leaves it alone.
- The scheduled `pull-card.yml` counts `--status open --human-gate none`.
  If nothing else is ready, it never launches at all.
- The verb's own `Next:` line tells the human the opposite.

Only the session-start hook lists `active` + `none` as resumable. That
hint then contradicts pull-card's soft-lock rule inside the same session.
The deck carries five cards parked at `active` today (the session-start
banner lists them), so the first human decision on any of them takes this
path.

This is a sibling of
[active-state-conflates-being-worked-on-with-parked-at-human-gate](../active-state-conflates-being-worked-on-with-parked-at-human-gate/),
which covers how parked-`active` cards are *labelled* while still gated.
This card covers what becomes of them after the decision, which that card
does not describe.

## Why deferred

The citations are confirmed. The hunter's scratch run (claim → raise the
gate → commit → `goc decide`) printed these values:

- `status/gate after decide: active none`
- `in goc --ready: False`
- `in goc --status active: True`

No `reproduce.py` is committed this round.

## Fix direction

Recommended: when `goc decide` lowers the gate on an `active` card, it
also returns the card to `open` and says so. The decision hands the work
back to the queue, and the session that claimed and parked it has ended.
That makes the skills' "status stays `open`" promise true for both parking
shapes, with no skill-side change.

Alternatives:

- Make pull-card release its claim when it raises the gate. This changes
  the documented "parked at `active`" shape that standup and the umbrella
  card build on.
- Teach `--ready` that `active` + `none` without a live worker is
  pullable. This needs a liveness signal the deck does not carry.

## Falsification recipe

1. In a scratch repo, run `goc new c --gate none --summary x` and author
   the DoD.
2. Run `goc status c active`.
3. Set `human_gate: decision` by hand (the pull-card Andon step) and
   commit.
4. Run `goc decide c --decision a --because b`.
5. Assert that `c` is in `goc --ready --json`. If it is, the hypothesis is
   disproved.

Surfaced by: general-purpose audit hunter (shipped skills vs CLI
contract), 2026-09-28.
