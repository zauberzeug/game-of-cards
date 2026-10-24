## 2026-05-29T15:56:05Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

The fix is mechanical (5-line guard mirroring `_cmd_decide`), but the
*semantic* the guard enforces is a real choice. Three options:

1. **Strict terminal-status guard (sibling-consistent).** `goc wait`
   against a terminal card exits non-zero with a message like:
   ```
   ERROR: <title>: status is 'disproved' (terminal);
   `goc wait` records a *live-card* impediment — terminal cards have no
   further work to wait on. To revisit a closed card, file a new card
   and supersede this one via `goc status <old> superseded --by <new>`.
   ```
   Pros: aligns with `_cmd_decide`, `_cmd_status`, `_cmd_done`. The
   validator's terminal-skip at `engine.py:1471` becomes defensible —
   terminal overlays cannot be created, only inherited from a
   pre-closure live state, and that's history. Cons: blocks the
   legitimate-but-rare workflow of post-hoc annotating *why* a closed
   card was closed (which arguably belongs in `log.md` anyway).

2. **Allow as historical annotation.** Treat `goc wait` on a terminal
   card as a documented operation. Requires `validate_waiting_overlay`
   to drop its terminal skip (or stay as it is, accepting that future
   `waiting_until` dates on closed cards never warn). Pros: keeps the
   verb maximally permissive. Cons: the overlay is documented as the
   live-pull signal everywhere else in the model; reusing it as a
   historical-annotation channel adds a second meaning. The same
   downstream-misread risk that motivated the board fix re-emerges.

3. **Split — allow `--clear`, reject the setters.** Lets a maintainer
   *remove* a stale overlay from a terminal card (cleanup) but not
   *set* one (no new contradictions). The board sibling fix explicitly
   left stored overlay fields untouched at close; this option provides
   the cleanup path without re-opening the "set after close" surface.

Sibling-shape audit (out of scope here; track separately): `_cmd_advance`
(engine.py:6565) and `_cmd_unadvance` (engine.py:6587) also lack
`TERMINAL_STATUSES` guards. Supersession records `superseded_by` /
`supersedes` edges atomically, so those verbs probably *should* accept
terminal targets — but the convention deserves its own card if option 1
or 3 lands here.


## 2026-10-22T05:17:57Z: decision recorded

Decided via parent terminal-status-guard-missing-across-mutation-verbs: option 1, strict terminal-status guard — goc wait refuses terminal targets for the setters and --clear alike; validate_waiting_overlay keeps its terminal skip — The maintainer approved the parent's recommended bundle in a human session on 2026-10-22, which resolves exactly this card's question; implement through the parent's shared _refuse_terminal_mutation helper, whose message is written fresh because _cmd_decide no longer refuses terminal cards. Gate decision → none.


## 2026-10-24T05:05:16Z — Closure

- **What changed**: `goc/engine.py` — new `_refuse_terminal_mutation(card, verb)`, the parent epic's shared terminal guard (live card passes; closed card gets one message naming card, status, verb and forward path, then exit 2 before any write). `_cmd_wait` calls it right after `load_card_or_exit`, so the setters and `--clear` are refused alike. `validate_waiting_overlay` keeps its terminal skip; its docstring now says why that is sound. `goc wait --help` names a live card's overlay. Synced to the three plugin engine mirrors.
- **Forward path departs from the fix sketch**: the sketch and the parent's agreed shape named `goc status <old> superseded --by <new>`, but that command exits 2 on every terminal card ("terminal cards cannot be moved backward through `goc status`", checked against a `done` card on 2026-10-24). The message names the `Skill(finish-card)` "After closure" path instead: a new card plus a dated post-close amendment in the closed card's log.md. `tests/test_terminal_status_guard.py` pins the premise. The parent's README and log record the correction, along with dropping the `replacement="supersede"` keyword it made moot.
- **DoD wording**: the TDD item said `reproduce.py` "exits non-zero" for the fixed state, the reverse of the deck's reproducer contract (0 = defect no longer fires, 1 = fires, 2 = harness broken). It now says "exits zero", and `reproduce.py` follows the contract.
- **Verification**: `reproduce.py` — 9/9 closed-card calls (`done` / `disproved` / `superseded` × `--reason` setter, bare `--until`, `--clear`) exit 2 with the README byte-identical, and the open-card control still writes its overlay. Before the fix it exited 1 with all 9 rewritten. `tests/test_terminal_status_guard.py` (5 tests) fails 16 ways against the pre-fix engine and passes now.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1369 passed / 0 failed (`uv run python -m unittest discover -s tests`)
- **Surfaced**: `goc done` and `goc done --bundle` answer a `disproved` / `superseded` card with "use the supersede/disprove workflow", a workflow `goc status` refuses for that same card. Filed and fixed through as `goc-done-on-a-closed-card-suggests-a-supersede-workflow-that-refuses-it`.

## Closure verification (2026-10-24T05:05:32Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-10-24 — Closure' present
