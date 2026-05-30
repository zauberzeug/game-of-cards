## 2026-05-30T02:15:24Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Two reasonable fix paths.

1. **Restore the closed-card fix verbatim on `deck_prompt_router.py`.**
   Re-apply the `14864cc` diff to the new filename. Adds the six verbs to
   the three pattern locations (patterns 1, 3, 6 — pattern 7 `please …`
   too). Smallest possible diff; keeps WORK_INITIATING's structure intact.

2. **Refactor WORK_INITIATING to a shared `WORK_VERBS` constant.** Same
   semantics, but extract `WORK_VERBS = r"(add|fix|build|create|write|
   implement|refactor|introduce|rename|update|change|remove|delete|move
   |ship|extract)"` and reference it from every pattern. Makes the next
   "you missed verb X" miss a one-line fix and lets the TypeScript port
   in `openclaw-plugin/index.ts` mirror the same constant. Slightly
   bigger diff; reduces the chance of a third regression by collapsing
   four edit sites into one.

Option 2 is the meta-fix path — it removes the maintenance shape that
caused the original miss. Option 1 is the literal "restore the closed
card's fix" path.

### Sibling defect (separately filed)

The same WORK_INITIATING list is also mis-tuned in the **opposite**
direction — pattern 4 (`i (want|need) (to|a|an|the|this)`) matches purely
exploratory prompts like `I want to understand X`. Tracked as
[deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts](../deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts/).
A single coordinated rewrite of WORK_INITIATING (option 2 above) can
fix both, but the two cards stay separate because the decision-required
trade-offs differ (over-fire vs under-fire, conservative whitelist vs
liberal whitelist).


## 2026-05-30T14:00:15Z: decision recorded

Option 2 (meta-fix): extract a shared WORK_VERBS regex constant (including rename/update/change/remove/delete/move/ship/extract) and reference it from every WORK_INITIATING pattern site; mirror the same constant in the openclaw-plugin TS port — collapses the four-edit-site maintenance shape that caused the original regression into one source of truth, makes the next missing-verb a one-line fix, keeps the TS port in lockstep, and enables a coordinated rewrite that can also address the sibling over-fire card. Gate decision → none.

## 2026-05-30T16:45:14Z — Closure

- **What changed**: `goc/templates/hooks/deck_prompt_router.py:16-35` — extracted `WORK_VERBS` constant (16 verbs incl. rename/update/change/delete/remove/move/extract) and wired it into the five alternation sites of `WORK_INITIATING`. Mirrored in `openclaw-plugin/index.ts:243-262`. The 5 plugin/dogfood copies regenerated via `python scripts/sync_plugin_assets.py`. Predecessor card `prompt-hook-misses-rename-work-requests/log.md` amended with forward pointer.
- **Verification**: `reproduce.py` exits 0 (7/7 prompts fire, was 2/7). Over-fire sibling reproducer unchanged (5 BUGs as before — same defect class, not regressed by this fix).
- **Audit**: PASS — no rubric configured; mechanical fix (templates regex meta-fix; no project principle touched beyond the dogfood sync contract already enforced by `sync_plugin_assets.py --check`).
- **Project impact**: n/a
- **Tests**: 318 passed / 0 failed / 0 xfailed (`uv run python -m unittest discover -s tests`).
- **Bundled with**: (none)

## Closure verification (2026-05-30T16:45:30Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
