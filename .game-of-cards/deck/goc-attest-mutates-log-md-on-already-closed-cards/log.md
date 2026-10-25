## 2026-05-29T18:08:20Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Three coherent options:

1. **Refuse outright** (sibling-consistent, matches
   `_cmd_done` / `_cmd_status` / `_cmd_decide`). Run the
   `TERMINAL_STATUSES` guard at the top of `_cmd_attest` and exit 2
   with a message naming the replacement path (re-open is forbidden;
   if the closure outcome itself is wrong, file a new card and link
   via `goc status <old> superseded --by <new>`). Pros: matches the
   family. Cons: a caller who genuinely wants to *replay* the
   original attestation (e.g., a CI smoke check) loses that path.

2. **Allow with a "re-attest is read-only" semantic.** On a terminal
   card, print the previously-recorded `## Closure verification`
   block (if any) and exit 0 without writing anything new. Pros:
   keeps the verb usable as a query. Cons: bifurcates the verb's
   behavior by status, which is the same kind of split that
   `goc decide` rejected.

3. **Split into `goc attest` (mutating) and `goc attest --replay`
   (read-only).** Replay reads the existing block; the bare verb
   refuses terminal targets. Pros: clean separation. Cons: new
   surface area for a low-frequency need.

Option 1 is the default unless a caller surfaces a real use case
for replay. The `goc-wait` sibling card uses the same Option-1
default.


## 2026-10-22T05:17:58Z: decision recorded

Decided via parent terminal-status-guard-missing-across-mutation-verbs: option 1, refuse outright — the terminal guard runs at the top of _cmd_attest and writes nothing — The maintainer approved the parent's recommended bundle in a human session on 2026-10-22, which resolves exactly this card's question; implement through the parent's shared _refuse_terminal_mutation helper, whose message is written fresh because _cmd_decide no longer refuses terminal cards. Gate decision → none.

## 2026-10-25T04:39:15Z — Closure

- **What changed**: `goc/engine.py:6158` — `_cmd_attest` calls `_refuse_terminal_mutation(card, "attest")` right after `load_card_or_exit`, ahead of the config load and the empty-config / all-skipped refusals; `goc/engine.py:4262` — `goc attest --help` names a live card. `tests/test_terminal_status_guard.py` adds the attest refusal test and a live-card control; its fixture drops the per-call `--no-commit` (`attest`, `move` and `quality-pass` reject it with exit 2, the guard's own code) for a scratch `config.yaml` with `auto_commit: false` and checks every probe card passes.
- **Verification**: `reproduce.py` exits 0 — both scenarios refused with exit 2 and `log.md` byte-identical; against the pre-fix engine it exits 1 (both scenarios appended a block; the all-pass one exited 0 and printed `Next: goc done`). The new attest test fails for all 3 terminal statuses against the pre-fix engine.
- **Reproducer contract**: `reproduce.py` returned 0 on its defect-present branch and 1 once fixed, inverting the DoD's "exits zero"; rewritten to 0 = defect no longer fires, 1 = fires, 2 = harness broken, and noted on `reproducers-can-exit-zero-while-their-defect-still-fires`.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1371 passed / 0 failed / 0 xfailed; `goc validate` exit 0

## Closure verification (2026-10-25T04:39:21Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-25 — Closure' present
