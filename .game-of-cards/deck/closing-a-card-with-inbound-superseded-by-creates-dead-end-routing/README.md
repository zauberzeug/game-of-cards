---
title: closing-a-card-with-inbound-superseded-by-creates-dead-end-routing
summary: "Close-time verbs (`goc done`, `goc done --bundle`, `goc status <X> disproved|superseded`) do not check whether the card being closed is the live target of another card's `superseded_by`. After such a close, the predecessor's forward routing pointer lands on a terminal card — exactly the dead-end shape the predecessor card `goc-status-superseded-by-accepts-terminal-status-successor` blocked at set-time. `goc validate` catches the violation reactively via `validate_superseded_by_targets` (engine.py:1412-1446), but the engine that just produced the violation issues no warning."
status: done
stage: null
contribution: medium
created: "2026-05-31T00:07:55Z"
closed_at: "2026-05-31T00:14:14Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: `deck/<title>/reproduce.py` exits zero and asserts that close-time verbs (`goc done`, `goc done --bundle`, `goc status <X> disproved`, `goc status <X> superseded --by <new>`) are rejected when the card being closed is still listed as a live successor in another card's `superseded_by`.
  - [x] TDD: a regression test in `tests/` exercises the new close-time guard across all four close paths (`done`, `done --bundle`, `status disproved`, `status superseded --by`), and confirms the guard's error message points at the inbound holder so the user knows where to retract.
  - [x] MECHANICAL: the guard is implemented via a shared helper called from `_cmd_done`, `_cmd_done_bundle`, and `_cmd_status` (close-into-terminal path) so the three close-time sites share one implementation — no duplication for `goc validate` to later diverge from.
  - [x] PROCESS: regression-test suite green; `goc validate` clean (no new error class introduced beyond what the set-time validator already exposes); plugin mirrors regenerated via `python scripts/sync_plugin_assets.py`.
worker: {who: "claude[bot]", where: main}
---

# Closing a card with inbound `superseded_by` creates dead-end routing

## Location

`goc/engine.py:3387-3438` (`_cmd_done`), `goc/engine.py:3461-3533`
(`_cmd_done_bundle`), and `goc/engine.py:4145-4246` (`_cmd_status`,
the close-into-terminal path).

## What's broken

The recently-closed card
[`goc-status-superseded-by-accepts-terminal-status-successor`](../goc-status-superseded-by-accepts-terminal-status-successor/)
established a two-pronged guard for the invariant "every
`superseded_by` reference must land on a live card":

1. **Set-time guard** in `_cmd_status` (`engine.py:4173-4184`):
   refuses `--by <Y>` when `<Y>.status` is terminal.
2. **Read-time validator** `validate_superseded_by_targets`
   (`engine.py:1412-1446`): scans the corpus and errors on any
   `superseded_by` reference landing on a terminal card.

The set-time guard locks down the forward direction at filing.
The read-time validator surfaces violations during `goc validate`.
Both were necessary — and necessary together — because the link
can be broken from *either* side: pointing a fresh supersession at
a dead target, OR killing the live target a valid supersession
already points to.

The close-time path covers only one of those sides. None of the
three close verbs scans for inbound `superseded_by` references to
the card being closed:

```python
def _cmd_done(args):
    """Flip status → done; set closed_at; enforce DoD-checkbox rule."""
    ...
    if prior in TERMINAL_STATUSES:
        print(f"ERROR: {title}: status is {prior!r} (terminal); ...")
        sys.exit(2)
    if t.human_gate != "none":
        print(f"ERROR: {title}: human_gate is {t.human_gate!r}; ...")
        sys.exit(2)
    _enforce_closure_on_integration_or_exit(title)
    # no inbound-superseded_by check before flipping
    text = mutate_frontmatter_field(text, "status", "done")
```

`_cmd_done_bundle` (`engine.py:3461-3533`) and the close-into-terminal
branch of `_cmd_status` (`engine.py:4145-4246`) have the same shape:
DoD enforcement, terminal-prior check, human-gate check — but no
scan for `superseded_by` pointers landing on this card.

Result: a card B that is currently the live successor of A (i.e.
`A.superseded_by == [B]` with B `open`/`active`) can be closed by
any of `goc done B`, `goc done --bundle B …`, `goc status B
disproved`, or `goc status B superseded --by C` — and the close
succeeds silently. A's forward routing pointer now lands on B's
terminal state.

## Empirical evidence

Run `uv run python .game-of-cards/deck/closing-a-card-with-inbound-superseded-by-creates-dead-end-routing/reproduce.py`
in a clean checkout. The script creates a temporary deck with two
cards, supersedes A by B (set-time clean), then closes B via each
of the four close-time paths in turn. Each path lets the close
land, then `goc validate` errors out reactively with the dead-end
complaint.

## Contradicted documentation

`AGENTS.md` "Deck as scheduler vs deck as record":

> supersession records a typed `superseded_by` / `supersedes` link
> (set atomically by `goc status <old> superseded --by <new>`) so a
> reader landing on a `superseded` card can be routed forward
> without parsing prose.

The "routed forward" guarantee holds only as long as `<new>`'s
status stays non-terminal. The close-time paths break the guarantee
silently.

## Why it matters

This is the asymmetric remaining gap from the predecessor card's
set-time fix. The state-evolution path is the *natural* way
supersession chains break in practice: a successor B turns out to
be wrong and gets disproved, or a new successor C arrives and B
should itself be superseded by C, or the team simply ships B as
`done` without realising A still routes through it. Each of those
is a routine close — there is no path through the CLI that warns
the human about the invariant break, and `goc validate` (which
*does* surface it later) is not a step every contributor runs after
every close. The deck silently accumulates dead-end forward
pointers between scheduled `validate` runs.

Reachability path: any normal `goc done <B>`, `goc done --bundle
<B> …`, `goc status <B> disproved`, or `goc status <B> superseded
--by <C>` invocation on a card `<B>` that another card lists in
`superseded_by`. The pre-existing `validate_superseded_by_targets`
in the read pass is reactive — it catches violations after they
land but never prevents them.

## Fix

Add a shared helper, e.g. `_check_no_inbound_superseded_by(title,
cards)`, that scans `cards` for any `t` with `title in
(t.frontmatter.get('superseded_by') or [])` and errors out with a
message naming each inbound holder so the user knows where to
retract the link (or supersede the holder first). Call it from:

1. `_cmd_done` — right after the human-gate check at
   `engine.py:3423-3430`.
2. `_cmd_done_bundle` — inside the per-card preflight loop at
   `engine.py:3476-3512`, before the `plan.append`.
3. `_cmd_status` — right after the new-status-is-terminal /
   human-gate-gate check at `engine.py:4205-4212`, only when
   `new_status` is in `TERMINAL_STATUSES`.

The helper loads `load_all_cards()` once per close (the same
pattern `_would_create_supersedes_cycle` already uses). The error
message should suggest the retraction path: "retract the
supersession from `<holder>` first, or supersede `<holder>` along
with this close."

## Related cards

- [`goc-status-superseded-by-accepts-terminal-status-successor`](../goc-status-superseded-by-accepts-terminal-status-successor/)
  — the predecessor; covered set-time guard + read-time validator,
  did not include the close-time symmetric guard.
- [`superseded-status-without-by-leaves-no-forward-routing-pointer`](../superseded-status-without-by-leaves-no-forward-routing-pointer/)
  — same invariant family (forward routing must reach live work);
  closed.
