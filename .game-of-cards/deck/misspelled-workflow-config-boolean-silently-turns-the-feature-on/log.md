## 2026-08-26 — filed, then narrowed by a sibling-reader precedent

Filed from an `audit-deck` pass with a two-layer `reproduce.py` (unit table
over `_coerce_config_bool`, plus end-to-end CLI runs with a correctly-spelled
`off` as control). Both symptoms reproduce.

A post-filing generalization sweep — asking whether the defect names a
pattern with broader applicability — found the answer inside the same module
rather than outside it. `get_skills_source` (`goc/engine.py:5342`) reads a
different key from the same `.game-of-cards/config.yaml`, faces the same
unrecognized-value question, and resolves it with a documented
fall-back-to-the-declared-default ("Invalid values fall back to 'auto'
silently — the config is meant to be forward-compatible").

So this is not a greenfield policy question, as the first draft of the body
framed it. It is one config reader contradicting its sibling. The README's
decision section was rewritten in place: refuse-and-exit and
widen-the-vocabulary are now recorded as rejected with the precedent cited,
and the only open question is silent-vs-warn-once. The DoD moved with it.

No generalization card filed. Two contradicting readers is an inconsistency
this card now carries, not yet the four-instance family that the audit
convention says should become an architectural meta-fix. Recheck if a third
config reader grows its own unrecognized-value policy.
