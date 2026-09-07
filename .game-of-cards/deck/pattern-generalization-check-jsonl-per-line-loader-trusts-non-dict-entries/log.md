
## 2026-08-31 — refine-deck: stale park retried, promoted

Parked `unverified` for 93 days. The body's falsification recipe was feasible
as written, so this round ran it instead of resetting the clock.

`reproduce.py` is now committed alongside the card. It confirms the
hypothesis: `_had_code_mutation` walks the transcript in reverse, so the last
non-dict line is hit first and `AttributeError: 'str' object has no attribute
'get'` escapes the Stop hook. (The card predicted `'list' object …`; the
exception type is the same, the shape that reaches `.get` first differs
because the walk is reversed. Summary corrected in place.)

The script also carries a control line — a well-formed `role: assistant`
`tool_use` block naming `Edit` — which returns True. Without it, a green run
after a fix could not distinguish "non-dict lines are skipped" from "the
loader stopped reading anything".

`unverified` dropped: its predicate is a state row — "no working reproduce.py
AND tagged at filing" — and a working reproduce.py now exists. The card stays
`open` at `human_gate: decision`; what is undecided is the remedy (skip the
line silently, as `json.JSONDecodeError` already is, versus something louder),
not whether the defect is real.
