
## 2026-08-31 — refine-deck: stale park re-checked, kept

96 days parked. Re-read against HEAD: the claim holds. The
`log-md-closure-entry` derived check still builds its pattern from
`date_prefix = _date_part(today)` at attest time (`goc/engine.py:5653`) and
matches `^## <that date>(?:T…Z)? — Closure` (`goc/engine.py:5657`), so a
closure entry written on one UTC day and attested on the next is still
searched for under the wrong header.

No `reproduce.py` built this round. Reproducing through the real attest path
means controlling the clock across a UTC day boundary, and the two honest
ways to do that — injecting `today` (the parameter exists, so the test would
prove the predicate rather than the shipped path) or freezing time around the
subprocess — differ in what they license the card to claim. Picking between
them is a design question the parked decision should answer first.
