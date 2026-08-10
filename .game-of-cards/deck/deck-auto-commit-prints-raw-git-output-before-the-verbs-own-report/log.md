## 2026-08-10T05:52:00Z — Closure

- **What changed**: `goc/engine.py` `_git_auto_commit` — all three
  `subprocess.run` calls (`git add`, `git diff --cached --quiet`, `git commit`)
  now pass `capture_output=True, text=True`, and the `CalledProcessError`
  handler replays the captured stderr/stdout under its existing
  `  (auto-commit failed: …)` line so a refusing pre-commit hook still reports
  why.
- **Verification**: reproduce.py inverts 1 → 0 across `status active`, `wait`
  and `advance`; pre-fix the git porcelain occupied stdout lines [0]-[1] with
  the verb's own report pushed to [2], post-fix stdout is 3 goc lines with the
  verb report at [0]. Suite 938 passed / 1 failed (935 → 938, +3 from
  `tests/test_auto_commit_stdout_isolation.py`); the single failure is the
  pre-existing `test_canonical_tag_rows` red tracked by
  `regression-suite-red-on-main-over-the-unverified-tag-row`, present on main
  before this change. `uv run goc validate` exits 0.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is an empty stub); mechanical fix that restores an invariant the repo already
  held everywhere else.
- **Project impact**: n/a
- **Tests**: 938 passed / 1 failed (pre-existing) / 0 xfailed
- **Bundled with**: n/a

Two notes worth carrying forward:

- The source-level guard (`test_engine_git_subprocesses_all_capture_output`)
  earned its place immediately: it flagged the `git diff --cached --quiet`
  call, which this card's own body had asserted was already captured. The
  behavioral tests could not have caught it (`--quiet` prints nothing), and
  neither could a reader — the claim was wrong in the filing and the guard was
  what corrected it. Both the body and the frontmatter summary were rewritten
  in place to say "the only subprocess calls" rather than "the only two".
- Capturing a `git commit` narrows what a hook can do interactively: with
  stdout captured, a hook that prompts can no longer show its prompt. stdin is
  still inherited, so such a hook would block rather than fail fast. Not
  changed here — non-interactive hooks are the only shape goc's auto-commit
  can support anyway, and adding `stdin=DEVNULL` is a separable behavior
  change. Recorded so the next reader does not rediscover it as a surprise.

## Closure verification (2026-08-10T05:45:17Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-10 — Closure' present
