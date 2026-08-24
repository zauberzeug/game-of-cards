
## 2026-08-24T05:20:00Z — Gate raised to `decision`; measurement and both prevention steps landed

Pulled at `human_gate: none`. Everything the decision does not depend on is
done; the gate is up for what it does.

**Measured (DoD 2).** `reproduce.py` anchors every `file:line` cite a gated
card carries and asks whether that line survives in HEAD. Of 189 gated
open/active cards, 145 carry a resolvable anchor and **26 carry one that is
absent from HEAD** (31 anchors total). That is the candidate set, not a
confirmed stale count — an absent anchor proves the code moved, only reading
the card proves the defect moved with it. The 44-across-30 figure in the
filing came from a different anchoring rule and is superseded.

**The finding that changes the decision.** `Skill(refine-deck)` anchors at the
commit that last *wrote* the line number, then step 4 relocates the number
onto a line that exists — the repair consumes the evidence. 133 of the 157
cited gated cards (85%) have had a cite rewritten this way, including both
known stale parks. Last-write anchoring at HEAD catches **0 of 2**; anchoring
at the filing commit catches **2 of 2**. So Option B's "the pass already has
this data" argument is false: the data it has is post-repair. B now costs a
second anchoring pass that must run before the repair step, which is most of
A's cost in a weaker home. The README's recommendation was revised from
"B plus C" to "A, or D" on that basis.

**Landed (DoD 4, 5, 7, 8).** `Skill(finish-card)` § "Other cards your fix also
fixed" — the closer greps card bodies before the flip and writes the
`superseded` edge, or, on a gated card the engine correctly refuses to move,
a `## <ts> — Staleness re-check` log entry naming the fixing commit.
`Skill(create-card)` § "Dedup against parked cards" — the same grep at filing
time, since the title grep dedup used cannot see into a parked card's body.
Both known instances got the marker, taking `reproduce.py` from 26 unsurfaced
to 24, which is what makes the marker demonstrably load-bearing rather than
decorative. Mirrors synced and the OpenClaw port re-run, both `--check` clean;
`goc validate` clean; 1030 tests green.

`tests/test_skill_body_size.py` caps for the two skills went 10,000 → 10,500,
documented in that file. `create-card` was at 9,996 of 10,000, so no addition
of any size would have fit; the rationale and the worked instance went to the
`reference.md` siblings as that guard's contract requires, and only the rule
plus the grep stayed in each core.

**Not done, and why.** DoD 1 (`reproduce.py` exits zero) is blocked on DoD 3 —
the script exits 1 with 24 unsurfaced candidates, which is the correct
pre-fix state, and clearing them needs the mechanism the human picks. DoD 6
(should the gate keep blocking `superseded`) is recorded with a recommendation
to keep it, but the DoD asks for an explicit human ruling, not an agent's.
