---
title: cascade-root-warning-counts-only-cards-in-the-retired-blocked-status
summary: "goc validate's CASCADE_CHAIN_ROOT warning walks down from a gated card only through cards stored as status: blocked, a value the three-axis model retired, so on a deck encoded the current way (dependents stay open) it can never fire. This repo's deck holds no blocked card, yet the decision-gated deck-auto-commit-ignores-card-files-other-than-readme-and-log heads a three-card chain whose closures the advanced-by-closed check holds until it closes, and validate stays silent. The blocked-status deprecation reconciled STALE_BLOCKED and ORPHAN_BLOCKED but never this third class, and no card tracks it."
status: done
stage: null
contribution: medium
created: "2026-11-09T00:52:40Z"
closed_at: "2026-11-09T04:37:25Z"
human_gate: none
advances:
  - remove-blocked-from-the-status-enum-and-validator
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits 0 — the gated chain warns whether its downstream cards are stored as `blocked` or `open`, and the below-threshold and ungated controls stay silent (it exits 1 today).
  - [x] TDD: `tests/test_validate_blocker_coherence.py` gains CASCADE_CHAIN_ROOT cases built the current way — downstream cards `open` (and one `active`), firing at the threshold and transitively — plus negatives where a terminal or draft descendant is neither counted nor walked through; each positive case fails on today's engine.
  - [x] MECHANICAL: the walk in `validate_blocker_coherence` (`goc/engine.py:2722`) continues through every non-terminal, non-draft descendant instead of `status == "blocked"` ones, and the warning text stops calling them blocked cards while keeping the `WARN CASCADE_CHAIN_ROOT <root>:` prefix.
  - [x] MECHANICAL: the function docstring (`goc/engine.py:2654-2671`) no longer says the queue hides a card with an open prerequisite (contradicts `card_is_ready`, `goc/engine.py:3164`), and describes CASCADE_CHAIN_ROOT by the closure gate rather than by `blocked` cards.
  - [x] MECHANICAL: `Skill(card-schema)` reference.md § Three-axis model names CASCADE_CHAIN_ROOT as the blocker-coherence class that outlives the migration and says what it flags; `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` are clean.
  - [x] TDD: the root obeys the same liveness rule as its descendants, and the walk cannot count it: a draft or closed gated card, an ungated card and a cycle back to the root each stay silent (`test_cascade_chain_root_is_never_a_draft_or_closed_card`, `test_cascade_chain_root_needs_a_raised_gate`, `test_cascade_does_not_count_the_root_on_a_cycle_back_to_it`); added during the fix, see Fix.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass, and the closure entry in `log.md` records how many CASCADE_CHAIN_ROOT warnings this repo's deck prints after the fix (one at filing time, see Empirical evidence).
worker: {who: "claude[bot]", where: main}
---

# The cascade-root warning counted only cards in the retired `blocked` status

`goc validate` has one check meant to tell a human which gated card holds up
the most other work: CASCADE_CHAIN_ROOT. It counted only cards stored as
`status: blocked`. The three-axis model retired that value, and this repo's
deck no longer holds a single `blocked` card. So the check stayed silent even
where the cascade it was built to find existed. It now counts every live card
the closure gate holds below a gated root. On this deck it names the one
chain it should, and it can no longer go dead when `blocked` leaves the enum.

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

## What was broken

The walk started from every gated card and moved down through `advanced_by`
edges. It stopped at any card that was not stored as `blocked`:

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

The docstring described the warning by its purpose:

> CASCADE_CHAIN_ROOT: a `human_gate != "none"` card whose `advances`
> transitively reach at least CASCADE_ROOT_THRESHOLD blocked cards.
> One human action at the root cascade-unblocks the whole subtree
> (Lean Andon — surface the cord, not the leaf).

The methodology no longer produced the state the walk needed.
`Skill(card-schema)` says (`SKILL.md:64`):

> `blocked` is deprecated — split into derived dependency-readiness and
> the `waiting_on` overlay

and § Three-axis model (`reference.md:144-149`):

> This decomposition replaces the legacy `status: blocked`. The
> validator findings that policed the legacy value (`STALE_BLOCKED`,
> `ORPHAN_BLOCKED`) are now migration aids — […] Nothing is ever
> steady-state `blocked`.

On a deck that followed this, the walk stopped at the first hop. The cluster
stayed empty and the warning could not fire. The docs named two of the
function's three classes as migration aids and said nothing about the third.
No shipped doc mentioned CASCADE_CHAIN_ROOT at all: a grep over
`goc/templates/`, `README.md`, `goc.md`, `AGENTS.md`, `ABOUT.md` and `site/`
found nothing.

The cascade still existed under the current model. Only the state the
walk tested for had gone. A downstream card cannot close while a card in
its `advanced_by` is open. The card-schema `reference.md:214-216` says so ("a card cannot
move to `done` while any `advanced_by` member is non-terminal"), and the
`advanced-by-closed` attest check enforces it (`goc/engine.py:6435`). A
gated root cannot close until a human lowers its gate: `goc done` refuses
with "run `goc decide` … to lower the gate before closing"
(`goc/engine.py:5515-5521`). So one decision at the root still holds up
the closure of everything below it.

The same docstring had a second stale sentence. Its STALE_BLOCKED entry
(`goc/engine.py:2657-2660`) recommended "to leave the card `open` and let the
queue hide it via the derived predicate". `card_is_ready` says the opposite
(`goc/engine.py:3164-3169`):

> Non-terminal `advanced_by` prereqs do NOT block readiness — an
> `advances` edge is a "should be done first" […] See
> `dependency_blockers` / `dependency_blocked`, which remain as advisory
> display only.

How it drifted:

- `cb5874e1` (2026-05-21) added all three classes, keyed on `blocked`, and
  closed [goc-validate-warns-on-stale-blocked-orphan-blocked-and-cascade-roots](../goc-validate-warns-on-stale-blocked-orphan-blocked-and-cascade-roots/).
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
- The tests never followed. All three cascade tests built their downstream
  cards with `status="blocked"` (`tests/test_validate_blocker_coherence.py:133`,
  `:154`, `:174`/`:179`), so the suite passed while the class did nothing on
  any migrated deck.

## Empirical evidence

`reproduce.py` builds four throwaway decks and runs the real `goc validate`
on each, through the `goc/_launch.py` launcher in a subprocess. Every deck
has a gated root above a chain root → c1 → c2 → c3, with both edge halves
written. Only the stored status of the downstream cards, the chain length
or the root's gate changes. Before the fix (2026-11-09):

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

After the fix, exit 0:

```
Each deck: gated root -> chain of downstream cards (advanced_by edges, both halves written).
Detector under test: `goc validate` stderr line starting 'WARN CASCADE_CHAIN_ROOT'.

[A] legacy: 3 downstream cards stored as `blocked` (control)
    validate exit 0; CASCADE_CHAIN_ROOT fired: True (expected True)  [ok]
    WARN CASCADE_CHAIN_ROOT cascade-root: 3 cards cannot close until this one does (gate=decision)
[B] current: the same chain, downstream cards `open`
    validate exit 0; CASCADE_CHAIN_ROOT fired: True (expected True)  [ok]
    WARN CASCADE_CHAIN_ROOT cascade-root: 3 cards cannot close until this one does (gate=decision)
[C] current: only 2 downstream cards (below threshold 3)
    validate exit 0; CASCADE_CHAIN_ROOT fired: False (expected False)  [ok]
[D] current: 3 downstream cards, root at human_gate none
    validate exit 0; CASCADE_CHAIN_ROOT fired: False (expected False)  [ok]

FIXED: the warning fires for the gated chain whichever status encoding its downstream cards use, and stays silent on the below-threshold and ungated controls.
```

On this repo's deck (2026-11-09: 620 done, 183 open, 8 active, 8 disproved,
6 superseded, 0 blocked), the shipped engine printed no CASCADE_CHAIN_ROOT
warning. The same scratch fix printed exactly one:

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

The fixed engine prints that one warning and no other, in the new wording
(828 cards at closure, still 0 `blocked`):

```
WARN CASCADE_CHAIN_ROOT deck-auto-commit-ignores-card-files-other-than-readme-and-log: 3 cards cannot close until this one does (gate=decision)
```

## Why it matters

- **It was silent where it would help most.** `goc triage` listed 177
  cards waiting on a human, oldest first, and nothing in it says which
  decision holds up the most other work. CASCADE_CHAIN_ROOT is the one
  check written to say that, and on this deck it could not fire. The
  backlog itself is the subject of
  [deck-fills-with-decision-gated-cards-faster-than-they-are-decided](../deck-fills-with-decision-gated-cards-faster-than-they-are-decided/),
  and [ready-leverage-line-goes-silent-when-no-card-is-pullable](../ready-leverage-line-goes-silent-when-no-card-is-pullable/)
  is another Andon signal that went quiet in the same state.
- **Removing `blocked` would have made the gap permanent.** The removal
  card reconciles only STALE_BLOCKED and ORPHAN_BLOCKED. Once `blocked`
  left the enum, `descendant.status != "blocked"` would have been true for
  every card, and the class dead code with a green test suite. This card
  therefore advances
  [remove-blocked-from-the-status-enum-and-validator](../remove-blocked-from-the-status-enum-and-validator/):
  that card should not close while the walk still tests for `blocked`,
  and it no longer does.
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

1. **One liveness rule at both ends of the walk.** A local `live(card)`
   (`goc/engine.py:2724-2725`) is true for a card that is neither terminal
   nor a draft (`card_is_draft`), the way every queue surface excludes
   drafts. The walk counts and passes through only live descendants
   (`goc/engine.py:2740`), so `open`, `active`, gated, waiting and legacy
   `blocked` cards all count: each is work that cannot close before the
   root. A terminal descendant holds nothing up, since the closure check
   passes on a closed prereq. A draft is not yet real work. The walk
   neither counts nor passes through either. `live()` is one more inline
   copy of the live-variant gate that
   [waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift](../waiting-impedes-callers-reimplement-the-terminal-status-liveness-gate-and-drift/)
   tracks. There is no bare live predicate to reuse (`live_impeded` folds
   in the overlay), and the helper's shape is that card's pending
   decision, so the walk keeps a local copy.
2. **The root must be live too** (`goc/engine.py:2728`), which the filed
   plan did not ask for. A closed root holds nothing up. That state is
   already a validate ERROR (`human_gate` must be `none` on a terminal
   card), but without the check the advisory would also claim live cards
   wait on it. A draft root is usually a fresh `goc new` scaffold carrying
   the default `decision` gate. `goc triage` hides it, so a warning naming
   it would point at a card the human cannot find there.
3. **The root is never its own descendant** (`goc/engine.py:2737`). A
   cycle back to the root is a validate ERROR of its own. Counting `open`
   cards would otherwise let the walk count the root and inflate the
   number by one.
4. **The message says what is now true**
   (`goc/engine.py:2745-2750`):
   `WARN CASCADE_CHAIN_ROOT <root>: N cards cannot close until this one does (gate=<gate>)`.
   The prefix is unchanged.
5. **Docstring** (`goc/engine.py:2648-2684`): STALE_BLOCKED and
   ORPHAN_BLOCKED are described as migration aids that fire only on a card
   still stored as `blocked`. The STALE_BLOCKED entry now says a card with
   an open prereq stays `open` and pullable. CASCADE_CHAIN_ROOT is described
   by the closure gate and the `advanced_by` edges the walk reads.
6. **`Skill(card-schema)` reference.md § Three-axis model** gains a
   paragraph (`goc/templates/skills/card-schema/reference.md:151-158`). It
   names CASCADE_CHAIN_ROOT as the blocker-coherence finding that outlives
   the migration and says what it flags. It does not restate the threshold,
   since the warning prints the count. Mirrors were regenerated and
   OpenClaw re-ported.
7. **Tests.** `tests/test_validate_blocker_coherence.py` builds its cascade
   fixtures the current way. Three positive tests fail on the pre-fix
   engine: the threshold case on `open` cards, a mix of `open`, `active`
   and legacy `blocked`, and a transitive `open` chain. The negatives cover
   below-threshold, an ungated root, a terminal descendant (`done` and
   `disproved`), a draft descendant, a draft or closed root, and a cycle
   back to the root. The dead-descendant fixture gives the root exactly two
   live cards, and a third hangs below the dead one. Counting the dead card,
   walking through it, or both reaches the threshold, so one silent
   assertion catches each mishandling. Seven mutants of the fixed walk were
   each caught by at least one test: count and walk through terminal cards;
   the same for drafts; count a dead card without walking through it, or
   walk through without counting it; drop the root's liveness check; drop
   the cycle guard; drop the gate check.

[advances-graph-readers-each-trust-one-field-and-disagree-on-half-edged-decks](../advances-graph-readers-each-trust-one-field-and-disagree-on-half-edged-decks/)
quoted the old docstring as a symptom of its own defect, a docstring naming
`advances` over a walk that reads `advanced_by`. Its README now shows the
walk itself, and its `log.md` records why. The walk still reads one half
only, so that card is unchanged.

**Why retarget instead of retire.** Retiring the class would also be
coherent: call it a migration aid and delete it together with `blocked`.
The evidence points the other way, for three reasons. Its stated purpose
("surface the cord, not the leaf") still describes a real situation under
the current model, through the closure gate shown above. The engine
already has the derived replacement for the stored state:
`dependency_blocked` (`goc/engine.py:2921-2927`, "no stored `blocked`
status required"). And on the live deck the retargeted check makes one
precise, true statement, not noise. Retiring it later would mean rewriting
`reproduce.py`'s success condition too: its legacy control (A) exits 2
when no warning fires.
