# Log

## 2026-06-25 — Filed

Surfaced during an audit pass while the autonomous pull queue was empty
(every open card carries a `session`/`decision` gate or a `waiting_on`
overlay). The `deck_prompt_router` work-verb pattern `\b({WORK_VERBS})\s+\w`
(line 28) fires the GoC reminder on pure-exploration questions that name a
work verb as a noun ("how does the update logic work?"). `reproduce.py`
confirms 5/5 exploration prompts wrongly fire while the 3 canonical work
prompts still fire.

Filed as a sibling of `deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts`
(same precedence root cause, different trigger line). Parked at
`human_gate: decision`: the fix path is a shared judgment call — see
`## Decision required` in README.md. The sibling's narrow-regex / extend-
EXPLORATION fix paths would NOT close this card, so the decision must be
evaluated against both.
