2026-05-27 — pull-card: behavioral repro confirmed (`waiting_impedes` returns False for `waiting_on: external` + elapsed `waiting_until`). Intent remains undecided (bug vs. documented elapsed-resurfaces). No project consultation rubric exists for this API-contract taste call, so raised `human_gate: none → decision` with a `## Decision required` section laying out options A (auto-clear) / B (warn) / C (working-as-intended). Recommendation noted: B.

## 2026-08-31 — refine-deck: stale park retried, promoted

Parked `unverified` for 96 days, but the 2026-05-27 entry above had already
confirmed the behaviour by driving `waiting_impedes` directly. What was
missing was a committed artefact, which is what the `unverified` predicate
actually scores ("no working reproduce.py AND tagged at filing").

`reproduce.py` now drives the real `goc wait` CLI against a scratch deck
rather than the predicate, so the evidence is about the shipped verb. It
reproduces the card's table exactly:

| overlay after the verb runs | impedes | ready |
|---|---|---|
| `waiting_on: external` + elapsed `waiting_until: 2020-01-01` | False | True |
| `waiting_on: external`, no stored date (control) | True | False |
| elapsed date, verb not run (control) | False | True |

Row 2 is the control that makes a future green run meaningful: it proves
`goc wait` sets an effective overlay when no stale date is in the way, so a
fix cannot pass by breaking the verb outright.

`unverified` dropped and the summary's "Needs confirmation" clause rewritten
in place — behaviour is settled, intent is not. The card stays `open` at
`human_gate: decision` on the unchanged A/B/C options; this round adds no
opinion beyond the recommendation already recorded.
