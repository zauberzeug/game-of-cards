---
title: goc-status-superseded-discards-by-override-when-target-already-superseded
summary: "`goc status <t> superseded --by <new>` silently does nothing when `<t>` is already in `status: superseded`. `_cmd_status` early-returns at `engine.py:4294-4303` whenever `prior == new_status`, BEFORE the `_mutate_pair` call at `engine.py:4336-4338` that wires the new typed forward routing pointer. The successor is validated (existence, terminal-status, self-target, cycle) and then dropped — the operator's redirect intent silently no-ops with exit 0. Same architectural class as [goc-status-active-discards-worker-overrides-when-target-already-active](../goc-status-active-discards-worker-overrides-when-target-already-active/), different verb/flag combination."
status: open
stage: null
contribution: medium
created: "2026-05-31T04:43:12Z"
closed_at: null
human_gate: decision
advances:
  - mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` (rewire `superseded_by` to honor the new `--by` and update both endpoints' typed pair, OR exit non-zero with a clear "card already superseded; release first" diagnostic, OR keep silent-drop and document it in `--by`'s help text).
  - [ ] TDD: `reproduce.py` exits zero — the chosen behavior matches expectation across the matrix (already-superseded card with a different `--by`, with the same `--by`, with no `--by`).
  - [ ] TDD: a unittest under `tests/` exercises `goc status <t> superseded --by <new>` on an already-superseded card and asserts the chosen behavior so a future `_cmd_status` refactor cannot reintroduce the silent drop.
  - [ ] MECHANICAL: argparser help text at `engine.py:2630-2633` (`--by`) reads consistently with the chosen behavior.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
---

# `goc status superseded` discards `--by` override when the target is already superseded

## Location

- Early-return path: `goc/engine.py:4294-4303`
- Successor validation that runs but is then discarded: `goc/engine.py:4276-4290`
- Typed-pair mutation that is bypassed: `goc/engine.py:4336-4338` (`_mutate_pair("superseded_by", "supersedes", add=True)`)
- Argparser that advertises the dropped flag: `goc/engine.py:2630-2633` (`--by`)

## What's broken

`_cmd_status` validates the `--by` successor and *then* checks for a no-op transition. When the target is already superseded, the early-return fires and the validated successor is silently dropped:

```python
4279:    if successor is not None:
4280:        successor_dir = DECK_DIR / successor
4281:        successor_card = load_card_or_exit(successor_dir, successor)
4282:        if successor_card.status in TERMINAL_STATUSES:
4283:            print(
4284:                f"ERROR: --by {successor!r} has status {successor_card.status!r} "
...
4290:            sys.exit(2)
4291:    card_dir = DECK_DIR / title
4292:    t = load_card_or_exit(card_dir, title)
4293:    prior = t.status
4294:    if prior == new_status:
4295:        if new_status == "active":
4296:            print(
4297:                f"WARNING: {title}: already active — possible racing claim;"
4298:                f" check `goc --status active` before proceeding",
4299:                file=sys.stderr,
4300:            )
4301:        else:
4302:            print(f"{title}: already {new_status}; nothing to do")
4303:        return
...
4336:    if successor is not None:
4337:        # Maintain typed bidirectional supersession link on both endpoints.
4338:        _mutate_pair(title, successor, "superseded_by", "supersedes", add=True)
```

The argparser advertises `--by` with no caveat that it only takes effect on a status change:

```python
2630:    p_status.add_argument(
2631:        "--by", dest="superseded_by", default=None,
2632:        help="Typed forward routing target when new_status is 'superseded'; required.",
2633:    )
```

A user reading `goc status --help` sees a flag that is described as required when superseding, with no hint that the value is discarded when the target is already in `superseded`.

## Empirical evidence

Reproducer output (`uv run python deck/<title>/reproduce.py`):

```
=== Initial state ===
status: open
superseded_by: <missing>

=== First flip: goc status foo superseded --by bar ===
foo: open → superseded
  superseded_by: bar; bar.supersedes += foo
status: superseded
superseded_by:
  - bar

=== Redirect attempt: goc status foo superseded --by baz ===
exit code: 0
stdout: foo: already superseded; nothing to do
stderr:

=== Post-redirect state ===
status: superseded
superseded_by:
  - bar
bar.supersedes:
  - foo
baz.supersedes: <missing>

DEFECT REPRODUCED: --by baz was silently dropped; exit code 0, foo.superseded_by still points at bar.
```

The redirect attempt passed `--by baz` to an already-superseded card. The engine validated `baz` (exists, status open, not self), then early-returned with exit code 0 and no indication that the `--by` was ignored. `foo.superseded_by` stays pointed at `bar` and `baz.supersedes` never gains `foo`.

## Why it matters

Supersession is the typed forward routing pointer the deck-as-record axis depends on (per the closed cards
[superseded-status-without-by-leaves-no-forward-routing-pointer](../superseded-status-without-by-leaves-no-forward-routing-pointer/)
and [goc-status-superseded-by-accepts-terminal-status-successor](../goc-status-superseded-by-accepts-terminal-status-successor/)).
Operators redirect supersession pointers when:

- The original successor is itself superseded later and the chain
  needs to collapse to the new live target.
- The first supersession recorded the wrong successor (e.g. typo,
  wrong slug) and needs correction without a full unsupersede +
  re-supersede dance.
- A card was bulk-migrated and the migration assigned a placeholder
  successor that needs to be retargeted.

The CLI accepts `--by` and validates it, signaling to the operator that the redirect will be honored. The silent no-op leaves a cold reader walking `foo.superseded_by` at the stale `bar` even though the operator explicitly tried to redirect.

**Reachability:** the early-return at `engine.py:4294-4303` fires on
every `_cmd_status` call where the requested `new_status` equals the
card's current `status`. The path is reached from the user-facing
`goc status <title> superseded --by <new>` verb whenever the card is
already in `superseded` — the most natural attempt at a redirect.

## Family

This is the second confirmed instance of the
**"early-return swallows side-effect flag"** family on `_cmd_status`:

| Card | Verb path | Flag(s) dropped |
|---|---|---|
| [goc-status-active-discards-worker-overrides-when-target-already-active](../goc-status-active-discards-worker-overrides-when-target-already-active/) | `active → active` | `--worker-who`, `--worker-where` |
| this card | `superseded → superseded` | `--by` |

If a third instance surfaces, this card should be marked
`advanced_by` an architectural meta-fix card that rewrites the early-return to either honor side-effect flags uniformly or reject them with a single shared diagnostic.

## Decision required

Three credible fix paths; pick one before implementing.

1. **Honor the override on no-op reclaim** — when `prior == new_status == "superseded"` AND `--by` differs from the existing `superseded_by`, rewire: drop the old pair edge, add the new pair edge, print "foo.superseded_by: bar → baz; bar.supersedes -= foo; baz.supersedes += foo". When `--by` matches the existing successor, the current "already superseded; nothing to do" message is correct. Mirrors how a user expects an idempotent verb to behave.
2. **Refuse the redirect with a clear diagnostic** — exit non-zero with `ERROR: <title> is already superseded by <existing>; to redirect, first release supersession (advance the existing pair edge unwind), then re-supersede with the new --by`. Forces the operator through an explicit release. Aligns with the "terminal cards cannot be moved backward through `goc status`" guard at engine.py:4304-4310, treating `superseded → superseded` as a semantic change that requires the unwind verb.
3. **Document the silent drop** — keep current behavior; add to `--by`'s help text: "Ignored when <title> is already superseded; release first to redirect." Cheapest fix; preserves backward compatibility; leaves the surprise in place.

Option 1 is the lowest-friction for the redirect use case. Option 2 is the safest (forces the operator to acknowledge the unwind). Option 3 is unsatisfying — it documents the trap but doesn't fix it. Pick once for the family so the sibling worker-override card resolves to a consistent answer.

## Fix sketch (option 1 — the recommended path)

Move the early-return *after* the successor application, or inline a redirect branch into the early-return:

```python
4293:    prior = t.status
4294:    if prior == new_status:
4295:        if new_status == "active":
4296:            ...
4297:        elif new_status == "superseded" and successor is not None:
4298:            existing = list(t.superseded_by or [])
4299:            if existing == [successor]:
4300:                print(f"{title}: already superseded by {successor}; nothing to do")
4301:                return
4302:            for prev in existing:
4303:                _mutate_pair(title, prev, "superseded_by", "supersedes", add=False)
4304:            _mutate_pair(title, successor, "superseded_by", "supersedes", add=True)
4305:            print(f"{title}: superseded_by: {existing} → [{successor}]")
4306:            return
4307:        else:
4308:            print(f"{title}: already {new_status}; nothing to do")
4309:        return
```

The implementer also has to decide whether to record the redirect in `log.md` (consistent with how `goc decide` records decisions) and whether to require `--commit` semantics on the rewire as a single atomic commit. Both belong in the same decision.
