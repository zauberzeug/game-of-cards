# 2026-05-09 — implementation done, blocked on validate-drift bug

The one-comment edit to `site/llms.txt` is applied: lines 58-59 now
read

```
pipx install game-of-cards
# or: uv tool install game-of-cards
```

DoD items 1, 2, 3 are satisfied by the edit alone. Item 4 (`uv run
goc validate` passes) cannot be ticked: validate fails at HEAD with
`plugin mirror drift: goc vs openclaw-plugin/goc: templates/hooks
(only in goc)`. The drift was introduced upstream by commit
`8277962` and has nothing to do with this card. Filed as
`validate-plugin-mirror-fails-when-openclaw-omits-hooks-dir`
(advanced_by). Once that lands, validate will pass, item 4 ticks,
and this card closes.

## 2026-05-26 — reclassified blocked → open (dependency-wait)

Reclassified off the `status: blocked` axis as part of the three-axis
migration (`migrate-existing-blocked-cards-to-open-or-waiting-overlay`).
The prereq `validate-plugin-mirror-fails-when-openclaw-omits-hooks-dir`
already closed on 2026-05-09, so the dependency-wait is itself
resolved — derived readiness (`card_is_ready`) treats a terminal
`advanced_by` as ready and the card re-enters the pull queue. No
`waiting_on` overlay is needed (this was never an exogenous wait;
it was a card-blocks-card edge the graph already represents).

## 2026-05-26T13:12:20Z — Closure

- **What changed**: `site/llms.txt:95-96` — install snippet already reads `pipx install game-of-cards` first with `# or: uv tool install game-of-cards` as the alternate (no `# preferred` comment); the body of the work landed in the 2026-05-09 edit, this closure ticks the final DoD item now that `uv run goc validate` is clean.
- **Verification**: `uv run goc validate` — all OK across the deck.
- **Audit**: PASS — invokes the recorded `python3` / `pipx` runtime baseline (memory `feedback_runtime_baseline_python3.md`); the llms.txt install snippet now matches.
- **Project impact**: n/a (single doc-comment alignment with recorded baseline).
- **Tests**: `goc validate` green; no pytest suite in this repo.
- **Bundled with**: n/a.

## Closure verification (2026-05-26T13:12:33Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — all 1 done
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
