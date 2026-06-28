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

## 2026-05-30T14:38:50Z: fix landed

Implemented Option B (CLI guard + symmetric validator):

- **CLI guard** (`goc/engine.py` `_cmd_status`, right after the existing successor existence check): the loaded successor card's `status` is now inspected; if it sits in `TERMINAL_STATUSES` (`done`, `disproved`, `superseded`) the command exits 2 with `ERROR: --by '<title>' has status '<status>' (terminal); supersession routing must land on a live card ...`. Sits between the existing "`--by` is the same card" guard and the `load_all_cards()` body, so the supersession transition can never reach the README/edge writes when the successor is terminal.

- **Symmetric validator** (`goc/engine.py` `validate_superseded_by_targets`): walks every card's `superseded_by` list and reports each entry whose target's `status` is in `TERMINAL_STATUSES`. Registered next to `validate_supersedes_targets` in the `_cmd_validate` dispatch chain so it runs on every `goc validate` invocation. Mirrors the existing `supersedes` check on the other end of the link.

Regression test: `tests/test_superseded_by_must_be_live.py` (four cases — CLI refusal for each of `done`/`disproved`/`superseded` successors, plus a validator case on a hand-crafted card whose `superseded_by` already points at a `done` card). All four pass; the full 316-test suite is green.

Reproducer now exits 0 after asserting that every terminal successor is rejected with stderr naming the terminal status (BEFORE: exit 0 with three "(no stderr)" rows; AFTER: exit 0 with three exit-code-2 rows whose stderr mentions `terminal`).

### Surfaced data drift (intentional)

The new validator surfaces one pre-existing dead-end forward link, exactly the class of drift the decision wanted to expose:

- `frontmatter-emitter-does-not-quote-integer-looking-string-scalars` (`status: superseded`) → `frontmatter-emitter-does-not-quote-integer-null-or-case-variant-boolean-values` (`status: done`).

This is left in place for separate deck-data hygiene; the validator now flags it on every `goc validate` so a cold reader knows the chain terminates at a closed card. Other validator errors visible on `main` (orphan `status: superseded` with empty `superseded_by`, a `human_gate: session` on terminal cards, and one half-edge) are pre-existing and unrelated to this fix — confirmed by `git stash; goc validate; git stash pop` producing the identical set minus the one new dead-end above.

Plugin mirrors regenerated (`python scripts/sync_plugin_assets.py`); `claude-plugin/goc/engine.py`, `codex-plugin/goc/engine.py`, and `openclaw-plugin/goc/engine.py` updated in lockstep.

## 2026-05-31 — Reversed by `goc-validate-requires-supersession-and-gate-states-no-verb-can-produce`

The set-time `--by` terminal guard in `_cmd_status` and the liveness branch of
`validate_superseded_by_targets` introduced by this card were both removed. A
downstream consumer (goc 0.0.22) showed the "`superseded_by` must land on live
work" invariant is wrong: a supersession's successor is meant to be
*completed*, so the typed forward pointer legitimately terminates at a `done`
card (the resolution) or routes onward through a `superseded` card's own
pointer. The invariant also made the successor of every supersession
permanently un-closeable (via the close-time guard from
`closing-a-card-with-inbound-superseded-by-creates-dead-end-routing`) and
contradicted the shipped AGENTS.md record-axis contract — integrity is
"enforced regardless of either endpoint's status." The relaxed rule is
referential-integrity-only ("target must exist"). The `frontmatter-emitter-…`
dead-end this card's log noted above now validates cleanly. The symmetric
`validate_supersedes_targets` (target-must-be-superseded) was left unchanged —
it is a different, still-correct rule. See the new card for the full rationale.
