---
title: decide-lowers-a-gate-without-surfacing-unclosed-prerequisites
summary: "The queue renders a dependency-readiness advisory for a card with unclosed `advanced_by` prerequisites, but `goc decide` prints nothing — so a gate can be lowered, and the card handed to an autonomous worker, while a prerequisite that reframes it is still open. Deciding is the more consequential act of the two, because it is what makes the card pullable."
status: open
stage: null
contribution: medium
created: "2026-07-26T13:21:33Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — it builds a card at `human_gate: decision` with a non-terminal `advanced_by` prerequisite, runs `goc decide`, and asserts the output names the unclosed prerequisite. Exits non-zero on current `main`.
  - [ ] MECHANICAL: `_cmd_decide` (`goc/engine.py:6060`-ish) prints an advisory naming each non-terminal `advanced_by` prerequisite before reporting the gate flip, reusing the same liveness rule the queue renderers use for their dependency advisory — derived, not a reimplementation (see the drift cards named below).
  - [ ] MECHANICAL: the advisory is NON-BLOCKING. `goc decide` still succeeds and still lowers the gate; exit code is unchanged. Roughly 80% of `advanced_by` edges are loose value-flow, so refusing would break the common case.
  - [ ] TDD: a regression test asserts the advisory does NOT fire when every `advanced_by` prerequisite is terminal, and that a card with no prerequisites is unaffected.
  - [ ] MECHANICAL: `Skill(decide-card)` step 1 tells the reader to check unclosed prerequisites before recording, and says why. Plugin mirrors synced; `uv run goc validate` clean.
---

# `goc decide` lowers a gate without surfacing unclosed prerequisites

## What's broken

The deck surfaces dependency-readiness when you are about to **work** a
card — the queue and board renderers carry a `⏳` advisory marker
(`goc/engine.py:3249`). Nothing surfaces it when you are about to
**decide** one. `_cmd_decide` reads the card, rewrites the body, flips
`human_gate`, appends to `log.md`, and prints:

```
<title>: decision recorded; gate <prior> → none
Next: gate lowered to none — any agent can now claim this card.
```

There is no mention of `advanced_by` anywhere in the function.

That ordering is backwards relative to consequence. Working a card is
recoverable — the agent reads the body, notices the problem, releases it.
Recording a decision is the act that **removes the human gate**, and the
message says so explicitly: *"any agent can now claim this card."* From
that moment the card is autonomously implementable, so a decision taken
without its prerequisite is a decision an unattended worker may act on
before any human sees it again.

## Why the prerequisite matters even though it does not block

Settled on
[`advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`](../advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/)
(closed 2026-05-26): an `advances` edge is roughly 80% value contribution
and 20% strict prerequisite, and the strict/loose distinction is
**"carried by the body, not the field."**

That decision is right, and it is exactly why an advisory is needed.
Because the field cannot express strictness, the only way to know whether
a given edge is the strict kind is to *open the prerequisite and read it*
— and nothing at decision time prompts anyone to. `card_is_ready`
deliberately does not block on non-terminal `advanced_by`
(`goc/engine.py:2424`), which is correct for the loose majority and
leaves the strict minority silently unguarded.

## Empirical evidence

`uv run python .game-of-cards/deck/decide-lowers-a-gate-without-surfacing-unclosed-prerequisites/reproduce.py`
on current `main`:

```
=== `goc decide gated-card ...` output ===
gated-card: decision recorded; gate decision → none
Next: gate lowered to none — any agent can now claim this card. goc to see the queue.

prerequisite still open:        True
gate was lowered to none:       True
output names the prerequisite:  False   (BUG if False)

FAIL: decide lowered the gate and announced the card is claimable without ever naming the open prerequisite.
```

Exit code 1. The announcement and the silence sit on adjacent lines: the
card is declared claimable by any agent in the same breath that the open
prerequisite goes unmentioned.

## Empirical instance

2026-07-26, in this repo.
[`autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`](../autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish/)
was decided and its gate lowered to `none`. It carried
`advanced_by: [human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property]`
— a card filed that same morning whose own DoD reads "reconcile it with
the sibling card … **whose premise this card corrects**."

The recorded decision adopted a card-level detection lint. The open
prerequisite states that such a lint "would misfire on every mixed card
in a deck," with evidence: the downstream card cited as the canonical
human-only example has eight DoD items, exactly one of them human-only.
The decision had to be rewound the same day — gate raised back by hand,
`## Decision` block removed, DoD un-ticked, and a card filed off the
decision returned to draft.

`goc decide` had every fact needed to prevent this: the edge was in the
frontmatter it parsed. It said nothing.

## Fix

In `_cmd_decide`, before the success line, resolve `advanced_by` and
print an advisory for each non-terminal prerequisite:

```
WARN: 1 unclosed prerequisite — read before relying on this decision:
  - human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property (open)
```

Non-blocking by design: the gate still lowers and the exit code is
unchanged. Refusing would break the ~80% loose-edge case the root card
settled, and the deck's house style for anything short of a schema
violation is advisory — `UNTAGGED_DOD_ITEM` and every other
`BlockerWarning` class are warning-only.

**Derive the liveness rule, do not reimplement it.** Several closed and
open cards in this deck record the same failure mode of hand-rolled
copies of a dependency/liveness predicate drifting from the engine —
[`renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift`](../renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift/)
and
[`waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift`](../waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift/).
This advisory must call the same helper the renderers call.

## Scope boundary

- **Not the gate-raise asymmetry.** That no verb *raises* a gate (this
  instance had to be rewound by hand-editing frontmatter) is already
  owned as a DoD item on
  [`human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property`](../human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property/):
  "a verb raises the gate the way `goc decide` lowers it." Not
  re-filed here.
- **Not the terminal-gate repair path.**
  [`goc-validate-requires-supersession-and-gate-states-no-verb-can-produce`](../goc-validate-requires-supersession-and-gate-states-no-verb-can-produce/)
  (done) covers gate *lowering* on terminal cards — a different
  invariant.
- **Not a change to closure or readiness semantics.** The root card
  settled those; this card adds a read-time advisory only, and
  deliberately touches neither `card_is_ready` nor the closure gate.
