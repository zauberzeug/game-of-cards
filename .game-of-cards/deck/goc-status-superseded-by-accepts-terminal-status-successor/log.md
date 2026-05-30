## 2026-05-29T20:12:41Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

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


## 2026-05-30T13:56:52Z: decision recorded

Option B: CLI guard in _cmd_status refuses a terminal --by successor, PLUS a new symmetric validator validate_superseded_by_targets that errors on any terminal superseded_by target — mirrors the 'Both' decision recorded on the sibling card superseded-status-without-by-leaves-no-forward-routing-pointer, keeping the supersession invariant enforced consistently across the pair; the CLI guard blocks the input boundary while the validator catches existing and hand-edited dead-end links. Gate decision → none.
