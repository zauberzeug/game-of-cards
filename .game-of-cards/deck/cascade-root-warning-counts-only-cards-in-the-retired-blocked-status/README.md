---
title: cascade-root-warning-counts-only-cards-in-the-retired-blocked-status
summary: "goc validate's CASCADE_CHAIN_ROOT warning walks down from a gated card only through cards stored as status: blocked, a value the three-axis model retired, so on a deck encoded the current way (dependents stay open) it can never fire. This repo's deck holds no blocked card, yet the decision-gated deck-auto-commit-ignores-card-files-other-than-readme-and-log heads a three-card chain whose closures the advanced-by-closed check holds until it closes, and validate stays silent. The blocked-status deprecation reconciled STALE_BLOCKED and ORPHAN_BLOCKED but never this third class, and no card tracks it."
status: active
stage: null
contribution: medium
created: "2026-11-09T00:52:40Z"
closed_at: null
human_gate: none
advances:
  - remove-blocked-from-the-status-enum-and-validator
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits 0 — the gated chain warns whether its downstream cards are stored as `blocked` or `open`, and the below-threshold and ungated controls stay silent (it exits 1 today).
  - [ ] TDD: `tests/test_validate_blocker_coherence.py` gains CASCADE_CHAIN_ROOT cases built the current way — downstream cards `open` (and one `active`), firing at the threshold and transitively — plus negatives where a terminal or draft descendant is neither counted nor walked through; each positive case fails on today's engine.
  - [ ] MECHANICAL: the walk in `validate_blocker_coherence` (`goc/engine.py:2722`) continues through every non-terminal, non-draft descendant instead of `status == "blocked"` ones, and the warning text stops calling them blocked cards while keeping the `WARN CASCADE_CHAIN_ROOT <root>:` prefix.
  - [ ] MECHANICAL: the function docstring (`goc/engine.py:2654-2671`) no longer says the queue hides a card with an open prerequisite (contradicts `card_is_ready`, `goc/engine.py:3164`), and describes CASCADE_CHAIN_ROOT by the closure gate rather than by `blocked` cards.
  - [ ] MECHANICAL: `Skill(card-schema)` reference.md § Three-axis model names CASCADE_CHAIN_ROOT as the blocker-coherence class that outlives the migration and says what it flags; `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` are clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass, and the closure entry in `log.md` records how many CASCADE_CHAIN_ROOT warnings this repo's deck prints after the fix (one at filing time, see Empirical evidence).
worker: {who: "claude[bot]", where: main}
---

# The cascade-root warning counts only cards in the retired `blocked` status

`goc validate` has one check meant to tell a human which gated card holds up
the most other work: CASCADE_CHAIN_ROOT. It only counts cards stored as
`status: blocked`. The three-axis model retired that value, and this repo's
deck no longer holds a single `blocked` card. So the check stays silent even
where the cascade it was built to find exists.

## Location

- `goc/engine.py:2712-2732`: the CASCADE_CHAIN_ROOT walk in
  `validate_blocker_coherence` (defined at `:2647`, threshold
  `CASCADE_ROOT_THRESHOLD = 3` at `:2571`). The status test is at `:2722`.
- `goc/engine.py:2654-2671`: the docstring of the same function.
- `goc/templates/skills/card-schema/reference.md:144-149` (§ Three-axis model)
  and `goc/templates/skills/card-schema/SKILL.md:64`: the deprecation the walk
  never caught up with.
- `tests/test_validate_blocker_coherence.py:122-187`: the three cascade
  tests, all built on `status="blocked"`.

## What's broken

The walk starts from every gated card and moves down through `advanced_by`
edges. It stops at any card that is not stored as `blocked`:

```python
    for root in cards:
        if root.human_gate == "none":
            continue
        cluster: set[str] = set()
        stack = list(unblocks.get(root.title, []))
        while stack:
            title = stack.pop()
            if title in cluster:
                continue
            descendant = by_title.get(title)
            if descendant is None or descendant.status != "blocked":
                continue
            cluster.add(title)
            stack.extend(unblocks.get(title, []))
        if len(cluster) >= CASCADE_ROOT_THRESHOLD:
```

The docstring describes the warning by its purpose:

> CASCADE_CHAIN_ROOT: a `human_gate != "none"` card whose `advances`
> transitively reach at least CASCADE_ROOT_THRESHOLD blocked cards.
> One human action at the root cascade-unblocks the whole subtree
> (Lean Andon — surface the cord, not the leaf).

The methodology no longer produces the state the walk needs.
`Skill(card-schema)` says (`SKILL.md:64`):

> `blocked` is deprecated — split into derived dependency-readiness and
> the `waiting_on` overlay

and § Three-axis model (`reference.md:144-149`):

> This decomposition replaces the legacy `status: blocked`. The
> validator findings that policed the legacy value (`STALE_BLOCKED`,
> `ORPHAN_BLOCKED`) are now migration aids — […] Nothing is ever
> steady-state `blocked`.

On a deck that follows this, the walk stops at the first hop. The cluster
stays empty and the warning cannot fire. The docs name two of the
function's three classes as migration aids and say nothing about the third.
No shipped doc mentions CASCADE_CHAIN_ROOT at all: a grep over
`goc/templates/`, `README.md`, `goc.md`, `AGENTS.md`, `ABOUT.md` and `site/`
finds nothing.

The cascade still exists under the current model. Only the state the
walk tests for has gone. A downstream card cannot close while a card in
its `advanced_by` is open. The card-schema `reference.md:214-216` says so ("a card cannot
move to `done` while any `advanced_by` member is non-terminal"), and the
`advanced-by-closed` attest check enforces it (`goc/engine.py:6435`). A
gated root cannot close until a human lowers its gate: `goc done` refuses
with "run `goc decide` … to lower the gate before closing"
(`goc/engine.py:5515-5521`). So one decision at the root still holds up
the closure of everything below it.

The same docstring has a second stale sentence. Its STALE_BLOCKED entry
(`goc/engine.py:2657-2660`) recommends "to leave the card `open` and let the
queue hide it via the derived predicate". `card_is_ready` says the opposite
(`goc/engine.py:3164-3169`):

> Non-terminal `advanced_by` prereqs do NOT block readiness — an
> `advances` edge is a "should be done first" […] See
> `dependency_blockers` / `dependency_blocked`, which remain as advisory
> display only.

How it drifted:

- `cb5874e1` (2026-05-21) added all three classes, keyed on `blocked`.
- `1fbf7d1e` (2026-05-26) derived dependency-readiness and wrote the "let the
  queue hide it" sentence. `04957091`, the same day, stopped readiness from
  gating the queue, and the sentence stayed.
- The deprecation epic
  [blocked-status-conflates-dependency-external-wait-and-deferral](../blocked-status-conflates-dependency-external-wait-and-deferral/)
  and its children reconcile only the other two classes: the epic's child
  table says "repurpose `STALE_BLOCKED`/`ORPHAN_BLOCKED`";
  [derive-dependency-readiness-instead-of-storing-blocked-status](../derive-dependency-readiness-instead-of-storing-blocked-status/)
  ticks "`STALE_BLOCKED` is reconciled"; and
  [remove-blocked-from-the-status-enum-and-validator](../remove-blocked-from-the-status-enum-and-validator/)
  has "`STALE_BLOCKED` / `ORPHAN_BLOCKED` code paths reconciled" as a DoD item.
  [migrate-existing-blocked-cards-to-open-or-waiting-overlay](../migrate-existing-blocked-cards-to-open-or-waiting-overlay/)
  then moved every `blocked` card to `open` or the wait overlay.
- The tests never followed. All three cascade tests build their downstream
  cards with `status="blocked"` (`tests/test_validate_blocker_coherence.py:133`,
  `:154`, `:174`/`:179`), so the suite passes while the class does nothing on
  any migrated deck.

## Empirical evidence

`reproduce.py` builds four throwaway decks and runs the real `goc validate`
on each, through the `goc/_launch.py` launcher in a subprocess. Every deck
has a gated root above a chain root → c1 → c2 → c3, with both edge halves
written. Only the stored status of the downstream cards, the chain length
or the root's gate changes:

```
Each deck: gated root -> chain of downstream cards (advanced_by edges, both halves written).
Detector under test: `goc validate` stderr line starting 'WARN CASCADE_CHAIN_ROOT'.

[A] legacy: 3 downstream cards stored as `blocked` (control)
    validate exit 0; CASCADE_CHAIN_ROOT fired: True (expected True)  [ok]
    WARN CASCADE_CHAIN_ROOT cascade-root: 3 blocked cards rooted here (gate=decision)
[B] current: the same chain, downstream cards `open`
    validate exit 0; CASCADE_CHAIN_ROOT fired: False (expected True)  [DEFECT]
[C] current: only 2 downstream cards (below threshold 3)
    validate exit 0; CASCADE_CHAIN_ROOT fired: False (expected False)  [ok]
[D] current: 3 downstream cards, root at human_gate none
    validate exit 0; CASCADE_CHAIN_ROOT fired: False (expected False)  [ok]

DEFECT: the same gated chain warns when its downstream cards are stored as the retired `blocked` status (A) and stays silent when they are `open`, the encoding the three-axis model prescribes (B). On a migrated deck the warning can never fire.
```

Exit 1. To check that the reproducer can tell a fix from a non-fix, it was
also run against a scratch copy of `goc/` with `:2722` changed to skip
only terminal descendants. Against that copy it exits 0. Against a copy
that also drops the root's gate test, it exits 1 (D fires). With no repo
root above it, it exits 2.

On this repo's deck (2026-11-09: 620 done, 183 open, 8 active, 8 disproved,
6 superseded, 0 blocked), the shipped engine prints no CASCADE_CHAIN_ROOT
warning. The same scratch fix prints exactly one:

```
WARN CASCADE_CHAIN_ROOT deck-auto-commit-ignores-card-files-other-than-readme-and-log: 3 blocked cards rooted here (gate=decision)
```

That is the chain
[deck-auto-commit-ignores-card-files-other-than-readme-and-log](../deck-auto-commit-ignores-card-files-other-than-readme-and-log/)
→ [card-rename-leaves-a-duplicate-of-the-old-card-in-the-shared-deck](../card-rename-leaves-a-duplicate-of-the-old-card-in-the-shared-deck/)
→ [goc-move-leaves-cross-reference-rewrites-uncommitted](../goc-move-leaves-cross-reference-rewrites-uncommitted/)
→ [goc-repair-edges-apply-leaves-edge-repairs-uncommitted](../goc-repair-edges-apply-leaves-edge-repairs-uncommitted/).
All four cards are `open` at `human_gate: decision`, and none of the
three below the root can close before it does.

## Why it matters

- **It is silent where it would help most.** `goc triage` lists 177
  cards waiting on a human, oldest first, and nothing in it says which
  decision holds up the most other work. CASCADE_CHAIN_ROOT is the one
  check written to say that, and on this deck it cannot fire. The
  backlog itself is the subject of
  [deck-fills-with-decision-gated-cards-faster-than-they-are-decided](../deck-fills-with-decision-gated-cards-faster-than-they-are-decided/),
  and [ready-leverage-line-goes-silent-when-no-card-is-pullable](../ready-leverage-line-goes-silent-when-no-card-is-pullable/)
  is another Andon signal that went quiet in the same state.
- **Removing `blocked` would make the gap permanent.** The removal card
  reconciles only STALE_BLOCKED and ORPHAN_BLOCKED. Once `blocked` leaves
  the enum, `descendant.status != "blocked"` is true for every card, and
  the class becomes dead code with a green test suite. This card therefore
  advances
  [remove-blocked-from-the-status-enum-and-validator](../remove-blocked-from-the-status-enum-and-validator/):
  that card should not close while the walk still tests for `blocked`.
- **A different root cause from the half-edge card.**
  [advances-graph-readers-each-trust-one-field-and-disagree-on-half-edged-decks](../advances-graph-readers-each-trust-one-field-and-disagree-on-half-edged-decks/)
  lists this walk among the readers that use `advanced_by` only. That card
  is about which half of an edge the walk reads. This one is about which
  statuses it walks through. Fixing either leaves the other.

How the input arises: every card `goc new` writes starts `open`, and the
skills tell agents to keep a card with an open prerequisite `open`. The
only way to get a `blocked` card is a deliberate `goc status <title>
blocked`, which the docs call deprecated.

## Fix

1. `goc/engine.py:2722`: walk through every live descendant, meaning one
   that is not terminal and not a draft, the way every other queue
   surface excludes drafts:
   `if descendant is None or descendant.status in TERMINAL_STATUSES or card_is_draft(descendant): continue`.
   `active` and legacy `blocked` descendants still count. Each is live
   work that cannot close before the root.
2. `goc/engine.py:2727-2732`: the message should say what is now true,
   for example `3 cards cannot close until this one does (gate=decision)`.
   Keep the `WARN CASCADE_CHAIN_ROOT <root>:` prefix; tests and readers
   grep for it.
3. `goc/engine.py:2654-2671`: rewrite the docstring. STALE_BLOCKED and
   ORPHAN_BLOCKED are migration aids for the legacy value.
   CASCADE_CHAIN_ROOT is a closure-gate signal. Drop the "let the queue
   hide it" sentence.
4. `goc/templates/skills/card-schema/reference.md` § Three-axis model:
   add one sentence naming CASCADE_CHAIN_ROOT as the class that outlives
   the migration and what it flags. Then regenerate the mirrors and
   re-port OpenClaw.
5. Tests, as in the DoD.

**Why retarget instead of retire.** Retiring the class would also be
coherent: call it a migration aid and delete it together with `blocked`.
The evidence points the other way, for three reasons. Its stated purpose
("surface the cord, not the leaf") still describes a real situation under
the current model, through the closure gate shown above. The engine
already has the derived replacement for the stored state:
`dependency_blocked` (`goc/engine.py:2921-2927`, "no stored `blocked`
status required"). And on the live deck the retargeted check makes one
precise, true statement, not noise. If a reviewer prefers retirement,
raise the gate. `reproduce.py` then exits 2 on its control, and it says
so: its success condition must be rewritten to match that choice.
