## 2026-11-09T02:00:15Z — Unverified park retried: defect reproduced

Refine-deck pass: this `unverified` park was past its 90-day clock (filed
2026-07-24, empty journal), so its falsification recipe was run. Landed
`reproduce.py` (0/1/2 exit contract; control: the scaffold must draw the
legacy warning). On main at `92f8bb55` it exits 1, exactly the loop the
card describes: `migrate` exit 1 → "run `goc install`", `install` exit 1 →
"run `goc upgrade`", `upgrade` exit 0 "upgrade complete" with no
`.game-of-cards/deck/`, `migrate` exit 1 again. `upgrade` re-stamps the
legacy `deck/.goc-version` in place.

- **Changed**: dropped the `unverified` tag; ticked DoD item 1 (its contract
  is the reproducer landing and demonstrating the loop); § Evidence now
  carries the transcript.
- **Not changed**: status, gate, the fix choice. The cites in § Location were
  not re-anchored here; the pass's citation step handles them.
