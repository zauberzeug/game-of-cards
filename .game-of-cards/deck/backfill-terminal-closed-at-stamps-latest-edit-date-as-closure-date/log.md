## 2026-11-09T01:58:50Z — Unverified park retried: defect reproduced, error rate re-measured

Refine-deck pass: this `unverified` park was past its 90-day clock (filed
2026-07-24, empty journal), so its falsification recipe was run. Landed
`reproduce.py` (0/1/2 exit contract): `--apply` writes T2, the latest
README edit, not T1, the closure commit; exit 1 on main at `92f8bb55`.

Error-rate re-measurement (DoD item 2). Closure commit = newest commit after
which the card's terminal `status:` line is present (`git log -G`, then a
blob check); heuristic = `git log -1 --format=%aI` on the README.

| status | cards | heuristic day != closure day |
|---|---|---|
| disproved | 8 | 7 |
| superseded | 6 | 4 |
| total (script's population) | 14 | 11 (79%) |
| done (not targeted, context) | 620 | 266 (43%) |

Same 11/14 the audit hunter reported. The later edits are deck-wide sweeps
that touched closed cards: `83c1408d` (2026-05-29, re-quoting `closed_at`)
is the latest edit of six of the seven misdated `disproved` cards, and
`4ec2606c` (2026-05-31) and `3ad4f9fa` (2026-06-21) account for the rest.
One card, `install-openclaw-harness`, records `closed_at` 2026-05-09 while
its status line first reads `superseded` on 2026-05-05, so the recorded
value is not the flip date either.

- **Changed**: dropped the `unverified` tag; ticked DoD items 1 (reproducer)
  and 2 (re-measurement); added § Empirical evidence.
- **Not changed**: status, gate, the heuristic choice. Fix NOT applied.
