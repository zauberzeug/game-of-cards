## 2026-10-22T05:20:23Z: decision recorded

Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: strict-refuse — goc wait with an --until instant that has already elapsed exits 2 and writes nothing, judged by the engine's own waiting read guard — The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question; this card's DoD defers the shape to the parent. Gate decision → none.


## 2026-10-29T04:53:25Z — Closure

- **What changed**: `goc/engine.py` `_cmd_wait` — when the call passes `--until`, the card as it would be written goes to `waiting_impedes`; if the read guard says the wait would not impede, the verb refuses through the parent epic's shared `_refuse_invalid_input` before the write: `ERROR: <title>: --until '<value>' has already elapsed (a bare date is midnight UTC at the start of that day), so the wait would not hide <title> from the queue — pass a later --until, or --reason alone for an open-ended wait`, exit 2, nothing written, no commit. The parenthetical is printed only for a bare date. The `_cmd_wait` and `_refuse_invalid_input` docstrings name the case, and `--until`'s help text says a bare date is midnight UTC and an elapsed one is refused. Synced to the three plugin engine mirrors.
- **Shape**: strict-refuse, applied as the parent decided it for the family on 2026-10-22 rather than re-derived: it is the precondition-failure shape the engine already uses (exit 2), and the only one that protects `--commit`-driven scripts and agents, which trust the exit code.
- **Predicate**: `waiting_impedes` itself, on a `Card` built from the in-memory frontmatter — not a fourth copy of `until_dt > now`, the comparison the hook readers drifted from. It runs only when `--until` is passed, so a bare `--reason` over a stale elapsed date, the open question of `goc-wait-does-not-clear-stale-elapsed-waiting-until`, is untouched. It sits after the closed-card refusal and the `--reason`/`--until` shape checks, since it needs a well-formed date.
- **Docs**: `Skill(advance-card)` Step 6 says an elapsed `--until` is refused and that a bare date is midnight UTC, so deferring through today takes tomorrow's date. Its examples carried a literal `2026-06-15`, elapsed since June and now a refusal; they use a `<YYYY-MM-DD>` placeholder instead. Template edited, mirrors regenerated, OpenClaw port re-run. `Skill(card-schema)`'s overlay paragraph describes the read semantics, which did not change, so it stays as is.
- **Reproducer**: rewritten to the 0/1/2 contract. As filed it exited 1 on a broken harness: at the start of this session `goc publish` refused its summary-less probe cards and the script crashed with exit 1, which reads as the defect firing. It also counted any non-zero `goc wait` exit, or the word "impede" in the output, as fixed. It now passes `--summary`, exits 2 on a setup failure or an outcome matching neither verdict, keys the fixed verdict on exit 2 + `ERROR:` naming `--until` + an untouched README, and adds a future-date control that must still hide its card.
- **Verification**: `reproduce.py` exits 0 — both elapsed values refused with the README untouched, the control hidden from `--ready` and listed by `--waiting`. Against the pre-fix engine (HEAD in a scratch worktree) it exits 1: both cases exit 0 with the success line while the card stays in `--ready`. With `goc` unimportable it exits 2. `WaitCliTest` (7 tests): the 4 refusal tests fail against the pre-fix engine; the 3 controls pass on both.
- **Re-run contract**: unchanged. `tests/test_verb_rerun_safety.py`'s `wait` probe passes `--reason external` only.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1423 passed / 0 failed (`uv run python -m unittest discover -s tests`)
- **Records updated**: the parent epic (roster closure and a log entry); `reproducers-can-exit-zero-while-their-defect-still-fires` (log entry: a reproducer whose harness failure exited 1).

## Closure verification (2026-10-29T04:54:09Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-10-29 — Closure' present
