## 2026-05-29 — Reporting choice in `validate_supersedes_targets`

The card body's "## Fix" sketch proposed `if not isinstance(refs,
list): continue` at all three sites — exactly mirroring the
`detect_advance_cycles` / `_would_create_advance_cycle` siblings. The
two cycle-detection walkers can `continue` cleanly because their job
is graph traversal; a non-list shape just means no outgoing edges.

`validate_supersedes_targets` is different: it is the dedicated
integrity validator for the supersession typed pointer, and its
contract is to *report* violations. Silently skipping a bare-string
`supersedes:` would let the dangling pointer pass `goc validate` —
the same defect class the card is fixing, just from the other
direction. So at that site the guard emits an error that includes
the bad value (`got str value='nonexistent'`) instead of `continue`-ing.
`reproduce.py` pins this: its PASS criterion is that the validator
flags `'nonexistent'`.

The other two walkers (`detect_supersedes_cycles`,
`_would_create_supersedes_cycle`) use the plain `continue` shape from
the card body — they are graph walkers, not validators, and the
schema-level shape check at `validate_card` line 1234-1237 already
catches the bad input on the `goc validate` path via
`LIST_REL_FIELDS`.
