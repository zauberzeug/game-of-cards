## 2026-05-27 — disproved as a reachable defect

Grepped for callers of `detect_advance_cycles` / `detect_supersedes_cycles`:
the only two are at `engine.py:2558` and `engine.py:2561`, both inside the
`validate` command, which runs `validate_card` (per-field self-reference
check at `engine.py:1163`) on every card first (`engine.py:2541`). A self-edge
fails that check before the cycle detectors run.

The recipe's promotion condition #1 (an unmasked direct caller) is false and
condition #2 (per-field check refactored away) has not happened, so the blind
spot is unreachable as a user-observable escape. The MECHANICAL DoD item —
drop `unverified` via a reproduce.py through an unmasked path — is
unsatisfiable because no such path exists. "Fixing" the guard would only emit
a redundant second error for self-edges `validate` already rejects.

Closed `disproved` per the card's stated falsification recipe. Re-file if the
per-field self-reference check is ever removed or narrowed.
