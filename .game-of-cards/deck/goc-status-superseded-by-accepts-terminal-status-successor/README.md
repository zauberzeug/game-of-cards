---
title: goc-status-superseded-by-accepts-terminal-status-successor
summary: "`goc status <X> superseded --by <Y>` accepts a successor whose status is already terminal (done, disproved, superseded). The CLI at engine.py:3966-3968 only confirms <Y>'s directory loads; it never inspects `<Y>.status`. `goc validate` does not catch the dead-end link because `validate_supersedes_targets` (engine.py:1276) enforces the reverse direction only. A cold reader walking the forward routing pointer from <X> lands on another terminal card with no live work."
status: open
stage: null
contribution: high
created: "2026-05-29T20:12:41Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `deck/<title>/reproduce.py` exits zero and asserts that `goc status <X> superseded --by <Y>` is rejected when `<Y>.status` is terminal (done / disproved / superseded).
  - [ ] PROCESS: decide the fix path — CLI guard in `_cmd_status` only, OR CLI guard plus a symmetric validator (e.g. `validate_superseded_by_targets`) that catches existing dead-end links during `goc validate`. Record reasoning in log.md. (Note: the sibling card `superseded-status-without-by-leaves-no-forward-routing-pointer` faces the same fix-path pick and should be resolved consistently — pick one approach for both.)
  - [ ] TDD: a regression test in `tests/` exercises the chosen guard for each terminal status (done, disproved, superseded) on the successor.
  - [ ] MECHANICAL: `goc validate` clean across the deck; plugin mirrors regenerated (`python scripts/sync_plugin_assets.py`); pre-commit clean.
---

# `goc status <X> superseded --by <Y>` accepts a terminal-status successor

## Location

`goc/engine.py:3966-3968` (`_cmd_status`, the successor existence
check) and `goc/engine.py:1276-1306` (`validate_supersedes_targets`,
the asymmetric validator).

## What's broken

The CLI accepts `goc status <X> superseded --by <Y>` even when
`<Y>.status` is already terminal (`done`, `disproved`, or
`superseded`). The supersession transition lands: `<X>.status`
becomes `superseded`, `<X>.superseded_by` gains `<Y>`, and
`<Y>.supersedes` gains `<X>`. A reader walking the forward routing
pointer from `<X>` to find the live replacement lands on a dead-end
card with no further work to do.

The successor check at `goc/engine.py:3966-3968`:

```python
if successor is not None:
    successor_dir = DECK_DIR / successor
    load_card_or_exit(successor_dir, successor)
```

`load_card_or_exit` only verifies the directory exists and the
frontmatter parses; it never inspects `successor`'s `status` field.
The two existing guards in the same function (lines 3956-3964) catch
"`--by` passed with the wrong target status" and "`--by` equals the
card being superseded" but not "`--by` is itself a terminal card".

The validator at `goc/engine.py:1276-1306` is **asymmetric**:

```python
def validate_supersedes_targets(cards: list[Card]) -> list[str]:
    """Enforce that every card in `supersedes` is itself `status: superseded`.
    ...
    """
    ...
    if target.status != "superseded":
        errors.append(
            f"{t.title}: supersedes: '{ref}' is not status: superseded "
            f"(target.status={target.status!r}); a typed supersession "
            f"pointer requires the replaced card to be marked superseded"
        )
```

This checks "every card listed in `supersedes` must itself be status:
`superseded`" — i.e. the *replaced* end of the pointer. There is no
matching check that "every card listed in `superseded_by` must be a
*live* card (status: `open` or `active`)". So the validator runs
green on any dead-end forward link.

## Contradicted documentation

`AGENTS.md` "Deck as scheduler vs deck as record":

> supersession records a typed `superseded_by` / `supersedes` link
> (set atomically by `goc status <old> superseded --by <new>`) so a
> reader landing on a `superseded` card can be routed forward
> without parsing prose.

"Routed forward" presupposes the destination is live work the reader
can act on. Landing on a terminal card means the routing terminated
inside the dead-end zone instead of arriving at live work — the
contract is silently violated.

## Why it matters

Supersession is the deck-as-record primitive that lets a cold reader
walk from a closed card to the live work that replaced it. If
`--by` can target a terminal card, the typed forward pointer can
land in a graveyard, defeating the read-pattern guarantee
documented in AGENTS.md. This shares root cause with sibling
`superseded-status-without-by-leaves-no-forward-routing-pointer`
(no `--by` at all): both leave the forward walk unable to terminate
at live work. Together they cover the two ways forward-routing
integrity can break — link missing, or link points at a dead end.

## Reachability path

User-facing flow: `uv run goc status card-a superseded --by card-b`
where `card-b` already has `status: done` (e.g. a card a user
believed replaced `card-a` was itself closed earlier and the user
hadn't noticed). The CLI prints success and writes the dead-end
link. Subsequent `goc validate` reports green. The next agent that
hits `card-a` follows the `superseded_by` pointer to `card-b`, sees
a terminal card, and has to either give up or guess.

## Fix proposal (collapses into the decision below)

See `## Decision required`.

## Decision required

The fix splits cleanly into two paths, mirroring the choice already
open on the sibling card
`superseded-status-without-by-leaves-no-forward-routing-pointer`:

**Option A — CLI guard only.** Add a status check in `_cmd_status`
right after the successor is loaded (`engine.py:3966-3968`):

```python
if successor is not None:
    successor_dir = DECK_DIR / successor
    successor_card = load_card_or_exit(successor_dir, successor)
    if successor_card.status in TERMINAL_STATUSES:
        print(
            f"ERROR: --by {successor!r} is status {successor_card.status!r} "
            f"(terminal); supersession routing must land on a live card "
            f"(status: open or active)",
            file=sys.stderr,
        )
        sys.exit(2)
```

Pros: minimal surface change, blocks the user-facing entry point.
Cons: any existing dead-end links already in the deck (or links
introduced by direct frontmatter edits) stay invisible to
`goc validate`.

**Option B — CLI guard plus symmetric validator.** Same CLI guard
as Option A, plus a new validator `validate_superseded_by_targets`
symmetric to `validate_supersedes_targets` (loops every card's
`superseded_by` list and errors when the referenced target is
terminal). Registered in the same validator dispatch chain.

Pros: closes the loop — `goc validate` catches both new and existing
dead-end links. Symmetric with the existing forward check.
Cons: more code; slight risk of surfacing existing dead-end links
that need cleanup before `goc validate` is clean across the deck.

**Recommended:** Option B, mirroring the recommended path on
`superseded-status-without-by-leaves-no-forward-routing-pointer`.
Whichever option wins on the sibling card should win on this one
too — coordinate the decision so the supersession invariant is
enforced consistently.

## Empirical evidence

`uv run python deck/<title>/reproduce.py` against the current `main`
(commit `66a21b5`) prints:

```
SUCCESSOR.STATUS     EXITCODE   STDERR TAIL
--------------------------------------------------------------------------------
done                 0          (no stderr)
disproved            0          (no stderr)
superseded           0          (no stderr)
```

All three terminal statuses are silently accepted as `--by`
successors. The supersession transition lands and the dead-end link
is written on both endpoints. After the fix, every row must exit
non-zero with an error mentioning the successor's terminal status.
