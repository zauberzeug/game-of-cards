---
title: parked-active-cards-are-missing-from-goc-triage
summary: "`goc triage` is the canonical \"waiting on you (gate ≠ none)\" view, but it filters the candidate set with `t.status == \"open\"`. A card that was claimed (`status: active`), raised its own gate to `decision` or `session` mid-session, and is now parked waiting on a human is silently excluded from the triage output. The closely-related SessionStart hook was just fixed for the symmetric defect (`session-start-hook-shows-gated-active-cards-as-resumable`, closed 2026-05-29) — triage now exhibits the same conflation but in the opposite direction: instead of mislabeling parked active cards as resumable, it hides them entirely from the view designed to surface them."
status: open
stage: null
contribution: medium
created: "2026-05-29T17:38:41Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: pick the fix shape from `## Decision required` and record the choice via `Skill(decide-card)` (lowers the gate to `none`).
  - [ ] TDD: a regression test exercises `_cmd_triage` against a fixture deck containing (a) `status: open` + `human_gate: decision`, (b) `status: active` + `human_gate: decision`, (c) `status: active` + `human_gate: session`. The test asserts the output matches the chosen framing — at minimum, the active+gated cards appear somewhere in the view (or are explicitly labeled per the chosen option).
  - [ ] MECHANICAL: `_cmd_triage` filter (`goc/engine.py:4613`) implements the chosen option; the header count and the rendered bucket totals agree across text and `--json` modes.
  - [ ] EMPIRICAL: re-running `goc triage` on this repo's current deck (which has 2 active+gated cards on 2026-05-29) surfaces those 2 cards under the chosen framing, with the total header reflecting the corrected count.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
---

# parked-active-cards-are-missing-from-goc-triage

## Location

`goc/engine.py:4609-4671` (`_cmd_triage`). The selection filter is on
line 4613:

```python
all_cards = [t for t in load_all_cards() if t.status == "open" and t.human_gate != "none"]
```

## What's broken

`goc triage` is documented as the "what's waiting on the human" view —
the verb's docstring is *"List parked cards (gate ≠ none), grouped by
gate, oldest-first."* and the rendered header literally says
`## Waiting on you (gate ≠ none) — N cards`. The selection filter
requires `status == "open"`, so any card that was claimed and is now
parked behind a raised gate is silently excluded.

A card lands in this state through the normal lifecycle:

1. An agent runs `Skill(pull-card)`, which calls `goc status <title>
   active` to claim a card.
2. The agent reads the card body, discovers the work needs a human
   decision, and (per `Skill(advance-card)` / `Skill(pull-card)`'s
   Andon-cord pattern) raises the gate to `decision` or `session`
   instead of finishing.
3. Status stays `active`. Gate is now ≠ `none`. The card is parked
   waiting on a human.

The `goc triage` view — which exists to enumerate exactly these
cards — does not show it.

## Empirical evidence (current repo state, 2026-05-29)

Two cards are currently in this state:

```
$ uv run goc --status active
TITLE                                                  STATUS  CONTR.  VALUE  GATE      TAGS                           DOD
-----------------------------------------------------  ------  ------  -----  --------  -----------------------------  ---
support-external-game-of-cards-state-location          active  high     15.3  session   epic,story,infra,api-contract  8/9
list-game-of-cards-on-anthropic-community-marketplace  active  high      9.0  decision  story,infra,documentation      3/8
```

Both are `status: active` with `human_gate != none`. Running triage:

```
$ uv run goc triage --json | python3 -c "import json,sys; d=json.load(sys.stdin); \
    print(len(d), [t['title'] for t in d if 'list-game' in t['title'] or 'support-external' in t['title']])"
33 []
```

Neither parked active card appears in the 33-card triage output.
The two highest-value cards in the deck (value 15.3 and 9.0,
both `contribution: high`) — the cards most likely to be the actual
bottleneck for the human's attention — are precisely the ones the
filter hides.

## Why it matters

The reachability path is the normal Andon-cord flow: any
`Skill(pull-card)` invocation that hits a decision-class question
parks the card via `goc advance <title> <gate>` (or its skill
equivalent) without flipping `status` back to `open`. Today, the
recommended pattern in `Skill(pull-card)` explicitly says *"raise
the gate to `decision` or `session`, write a `## Decision required`
body section, commit the gate-and-body update"* — but does not
prescribe flipping `status: active → open`, and there is no engine
support for that combined operation.

So the workflow GoC documents produces cards that `goc triage` is
defined to surface but actively hides. The user running `goc
triage` to find what is waiting on them gets a misleadingly
incomplete answer; the parked active cards remain invisible until
someone reads `goc --status active` and notices the gate column.

Symmetric defect: `session-start-hook-shows-gated-active-cards-as-resumable`
(closed 2026-05-29) addressed the *opposite* misclassification —
that hook saw the parked active cards but mislabeled them as
"resume or close" work an agent could pick up. Both bugs stem from
treating `status` and `human_gate` as a single axis; the fix family
is to make every status/gate consumer interpret them as orthogonal.

## Decision required

Three credible fix paths exist; pick one before any engine edit
lands.

### Option A — Drop the `status == "open"` clause; include all non-terminal cards

```python
# goc/engine.py:4613
all_cards = [
    t for t in load_all_cards()
    if t.status not in TERMINAL_STATUSES and t.human_gate != "none"
]
```

Treat the gate, not the progress status, as the sole inclusion key.
Active+gated cards land in the same gate buckets as open+gated
cards (`### decision (N)`, `### session (N)`). Simplest fix; matches
the verb's documented contract literally ("parked cards (gate ≠
none)").

**Pro:** minimal code change, semantically clean — `triage` becomes
the dual of `--ready`.
**Con:** active+gated and open+gated render identically. A human
reading the view cannot tell which cards have an agent's WIP that
will be lost if the decision splits the work.

### Option B — Include active+gated, but split into a labeled sub-section

Add a third bucket header (or per-gate sub-label) that distinguishes
*claimed-and-parked* from *not-yet-claimed-and-parked*:

```
### decision (21)
  (open — not yet claimed)
  - card-a · ...
  - card-b · ...
  (active — claimed, agent is waiting on you)
  - card-c · ... · claimed by claude[bot]@main
```

Stronger framing for the human; surfaces the worker overlay
(already present on these cards) so they know who/where the WIP
sits.
**Pro:** preserves the visual distinction between virgin queue and
WIP-paused work; pairs with the existing `worker` field.
**Con:** more code and more output noise; requires a render-loop
refactor (line 4654 currently iterates `sorted(by_gate.keys())`).

### Option C — Add a separate top-level "Active and parked" section

Keep `### decision` / `### session` for open+gated; add a new
section above them:

```
## Active and parked — N cards
- support-external-... · session · claimed by ...
- list-game-of-cards-... · decision · claimed by ...

## Waiting on you (gate ≠ none) — M cards (open only)
### decision (M1)
...
```

Most disruptive to existing layout but most legible — a human
scanning triage sees the WIP-paused work as a discrete top-of-page
list, separated from the queue-of-undecided work.
**Pro:** the operational distinction (someone's session is parked
on this) is structurally separated from the un-claimed queue.
**Con:** changes the header schema; any consumer parsing
`--json` (the payload now adds a `claimed` boolean or a separate
top-level key) needs to be updated; pairs poorly with
`--json` if the JSON shape changes.

**Recommendation:** Option A. It is the literal reading of the
verb's docstring (`gate ≠ none`) and matches how
`session-start-hook-shows-gated-active-cards-as-resumable` chose
to handle the parallel misclassification (filter on `human_gate`,
not on `status`). Add the worker overlay to the per-card preview
line for free, since the `worker` field is already loaded on the
`Card`. Option B/C can be revisited if user feedback shows the
flat list buries the WIP-paused cards.

## Reproduce

`deck/parked-active-cards-are-missing-from-goc-triage/reproduce.py`
runs `_cmd_triage` against a synthetic 3-card deck (open+gated,
active+gated, active+none) and prints the JSON payload. The defect
shows as the active+gated fixture being missing from the output.
