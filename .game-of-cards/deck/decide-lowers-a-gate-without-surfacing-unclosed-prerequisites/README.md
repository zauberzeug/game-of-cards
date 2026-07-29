---
title: decide-lowers-a-gate-without-surfacing-unclosed-prerequisites
summary: "RESOLVED. The queue rendered a dependency-readiness advisory for a card with unclosed `advanced_by` prerequisites while `goc decide` printed nothing — so a gate could be lowered, and the card handed to an autonomous worker, with a prerequisite that reframes it still open. `_cmd_decide` now prints a non-blocking advisory naming each unclosed prerequisite and its status before it reports the gate flip, derived from the renderers' own `dependency_advisory` helper (default terminal-gated slice, not the stricter `queue_only` one — an `active` card's decision is exactly one somebody is about to act on). `Skill(decide-card)` step 1 now tells the reader to read those prerequisites *before* recording, since the CLI advisory necessarily arrives as the decision lands."
status: done
stage: null
contribution: medium
created: "2026-07-26T13:21:33Z"
closed_at: "2026-07-29T05:33:07Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — it builds a card at `human_gate: decision` with a non-terminal `advanced_by` prerequisite, runs `goc decide`, and asserts the output names the unclosed prerequisite. Exits non-zero on current `main`.
  - [x] MECHANICAL: `_cmd_decide` (`goc/engine.py:6060`-ish) prints an advisory naming each non-terminal `advanced_by` prerequisite before reporting the gate flip, reusing the same liveness rule the queue renderers use for their dependency advisory — derived, not a reimplementation (see the drift cards named below).
  - [x] MECHANICAL: the advisory is NON-BLOCKING. `goc decide` still succeeds and still lowers the gate; exit code is unchanged. Roughly 80% of `advanced_by` edges are loose value-flow, so refusing would break the common case.
  - [x] TDD: a regression test asserts the advisory does NOT fire when every `advanced_by` prerequisite is terminal, and that a card with no prerequisites is unaffected.
  - [x] MECHANICAL: `Skill(decide-card)` step 1 tells the reader to check unclosed prerequisites before recording, and says why. Plugin mirrors synced; `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# `goc decide` lowers a gate without surfacing unclosed prerequisites

## Resolution

`_cmd_decide` now resolves `advanced_by` from the pre-mutation card and, when
any prerequisite is non-terminal, prints an advisory to stderr *before* the
`decision recorded; gate <prior> → none` line:

```
WARNING: autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish: 1 unclosed prerequisite — read it before relying on this decision:
  - human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property (open)
  An `advances` edge does not record whether it is strict, so whether a prerequisite reframes this card is knowable only by reading it. Advisory only: the gate lowers either way.
```

That is the real deck rendering the 2026-07-26 incident below — the fix names
the exact edge whose silence forced a same-day rewind.

Three properties, each pinned by a test:

- **Non-blocking.** Exit code unchanged, gate still lowered, `## Decision`
  block and `log.md` entry still written. The ~80% loose-edge majority
  settled by the root card is untouched, and this matches the deck's house
  style — every `BlockerWarning` class is warning-only.
- **Derived, not reimplemented.** The liveness rule comes from
  `dependency_advisory` — the same helper `render_table`, `render_board` and
  `render_json` consume. The notice names exactly the blockers the helper
  reports, for every prerequisite status; a test asserts that equivalence
  rather than restating the terminal set.
- **Terminal-gated, not `queue_only`.** The renderers' stricter slice
  suppresses the advisory on `active` cards, because "you may start" has no
  audience once a card is claimed. That is the wrong gate here: an `active`
  card at a raised gate is precisely a card whose decision someone is about to
  act on. The default slice still mutes terminal cards, where `goc decide` is
  the record-axis gate repair and prerequisites are moot.

A dangling `advanced_by` reference renders as `(card not found)` — inherited
from `dependency_blockers`, which conservatively counts an unknown title as a
blocker until the validator reconciles it.

`Skill(decide-card)` step 1 carries the same instruction one step earlier in
the loop, where it can still change the outcome: check `advanced_by` and read
any unclosed prerequisite **before** recording. The CLI advisory is a
backstop, not a substitute — by the time it prints, the decision has landed.

## Why the prerequisite matters even though it does not block

Settled on
[`advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`](../advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/)
(closed 2026-05-26): an `advances` edge is roughly 80% value contribution
and 20% strict prerequisite, and the strict/loose distinction is
**"carried by the body, not the field."**

That decision is right, and it is exactly why an advisory is needed.
Because the field cannot express strictness, the only way to know whether
a given edge is the strict kind is to *open the prerequisite and read it*
— and until this fix, nothing at decision time prompted anyone to.
`card_is_ready` deliberately does not block on non-terminal `advanced_by`
(`goc/engine.py:2444`), which is correct for the loose majority and left
the strict minority silently unguarded.

## What was broken

The deck surfaced dependency-readiness when you were about to **work** a
card — the queue and board renderers carry a `⏳` advisory marker. Nothing
surfaced it when you were about to **decide** one. `_cmd_decide` read the
card, rewrote the body, flipped `human_gate`, appended to `log.md`, and
printed:

```
<title>: decision recorded; gate <prior> → none
Next: gate lowered to none — any agent can now claim this card.
```

`advanced_by` appeared nowhere in the function.

That ordering is backwards relative to consequence. Working a card is
recoverable — the agent reads the body, notices the problem, releases it.
Recording a decision is the act that **removes the human gate**, and the
message says so explicitly: *"any agent can now claim this card."* From
that moment the card is autonomously implementable, so a decision taken
without its prerequisite is a decision an unattended worker may act on
before any human sees it again.

`reproduce.py` on the pre-fix engine printed
`output names the prerequisite: False` and exited 1, with the announcement
and the silence on adjacent lines. It now exits 0.

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
frontmatter it parsed. It said nothing. It now says it.

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
  invariant. This fix deliberately stays silent on that path.
- **Not a change to closure or readiness semantics.** The root card
  settled those; this card adds a read-time advisory only, and touches
  neither `card_is_ready` nor the closure gate.
- **Not the closure gate's own liveness copy.** `_run_derived_check`'s
  `advanced-by-closed` branch (`goc/engine.py:5098`-ish) hand-rolls a
  third variant of the same predicate, and it differs — `t in by_title
  and ...` silently drops dangling references that
  `dependency_blockers` counts as blockers, which is why this fix
  renders them as `(card not found)` while the closure gate reports
  `all N closed`. Already owned: the dangling-drop bug by
  [`attest-treats-dangling-advanced-by-refs-as-closed`](../attest-treats-dangling-advanced-by-refs-as-closed/)
  (open, parked on a `decision` gate), and the reimplementation shape by
  [`renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift`](../renderers-reimplement-the-dependency-advisory-liveness-gate-and-drift/)
  and
  [`waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift`](../waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift/).
  Not re-filed and not folded in here, because changing the closure
  gate changes what `goc done` refuses.

## Artifacts

- reproduce.py
- `tests/test_decide_unclosed_prerequisites.py` — unit contract of the
  notice builder (including the derivation equivalence and the
  slice choice) plus end-to-end CLI coverage of the ordering,
  non-blocking-ness, and both negative cases.
