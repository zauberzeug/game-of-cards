## 2026-05-09: renamed from make-autocommit-mandatory-when-deck-is-version-controlled

## 2026-05-09: decision recorded

Autocommit defaults to ON when deck is tracked (OFF when untracked), but stays user-configurable. If a tracked-deck user sets auto_commit: false, emit a one-time-per-session warning naming the trade-off. — Forcing mandatory contradicts persona #2 (solo developer wants to review before commit, per PERSONAS.md). The hazard for persona #3 (multi-agent coordinator) is solved by a loud warning rather than removing the knob, preserving both personas.. Gate session → none.
