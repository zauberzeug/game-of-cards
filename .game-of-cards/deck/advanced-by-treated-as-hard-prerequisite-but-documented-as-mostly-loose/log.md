# Log — advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose

## 2026-05-26 — Decision recorded (Option E; gate decision → none)

**Decision:** `advanced-by-closed` is correct as-is (Option E). Keep the
hard FAIL; the blessed resolution is to retract a false edge with
`goc unadvance` (documented on both cards), not `--skip`. The
loose/strict distinction governs start-ordering, not closure, so the
genuine over-read is relocated to derived *readiness* and delegated to
the epic's children.

**Why (the observation that dissolved the framing):** "X advances Y" is
defined as "closing X delivers a piece of Y's value chain." So for
closure, a true edge ⇔ Y not done while X open. There is no coherent
"true edge you may close past": if Y is closeable, the edge was false
(it points at the wrong target — "more tests for C" advances the testing
of C's functionality, not C). This made the closure gate provably
correct and reduced the choice to "how do you resolve a FAIL honestly" →
retract the false edge.

The loose/strict split survives but only for *start ordering*: a loose
edge lets you begin Y before X is done, yet still blocks declaring Y
done with X's piece undelivered. Hence the asymmetry table in the
README and the hand-off of the readiness question to
`derive-dependency-readiness-…` / `add-waiting-overlay-…`.

### Archived deliberation — the options as originally posed (A–D) and the E-vs-B weighing

The card was filed `human_gate: decision` with this options matrix.
Preserved here because `goc decide` does not yet archive replaced README
content (see `goc-decide-loses-deliberation-history-by-not-archiving-replaced-section`).

**Reasoning (as filed):** `advanced_by` was deliberately defined as
mostly-loose with strict/loose carried by prose, yet two engine surfaces
(attest closure gate; derived dependency-readiness) read it as strictly
hard. Picking blindly risks either (a) re-introducing schema complexity
the value-sort redesign removed on purpose, or (b) silently keeping a
closure/readiness blocker that the design says should not exist for ~80%
of edges.

**Option A — encode strict-vs-loose per edge.** Add a per-edge marker
(`strict: true`, or a parallel `requires` list); gates fire only on
strict edges.
- Pros: most precise; genuine prerequisites still hard-block while loose
  contributions don't.
- Cons: re-introduces the exact strict/loose schema distinction
  `rename-blocks-to-advances` deliberately removed; migration cost (every
  existing edge is implicitly loose); more frontmatter, validator rules,
  teaching surface.

**Option B — make `advanced-by-closed` advisory / severity-configurable.**
Downgrade to a non-blocking warning (or config knob); apply the same
advisory stance to readiness; align attest with what `goc done` enforces
(it does not gate on this check).
- Pros: honest to the design (field can't distinguish, so don't pretend
  at gate-time); smallest change; no schema growth/migration; removes
  the autonomous-worker halt and per-child `--skip` toil.
- Cons: loses a genuine guard for the ~20% that *are* strict; "advisory"
  needs a convention so it isn't ignored noise.

**Option C — gate only when the upstream card is itself blocking**
(`human_gate != none` or `status: blocked`).
- Pros: no schema change; narrows the FAIL to cases where ordering
  plausibly matters; keeps a hard block for the parked-parent shape.
- Cons: still a heuristic; couples the check to gate semantics.

**Option D — keep the hard reading (status quo).**
- Pros: zero work; matches the epic's recorded readiness premise;
  strongest ordering guarantee.
- Cons: contradicts the design card's "~80% loose" definition; the
  reported friction.

**Original recommendation: Option B**, on the grounds that the field was
designed not to distinguish strict from loose, so a hard gate reads
information the field doesn't carry.

**Why the decision landed on E instead of B.** B's defended advantage
was "let Y close while a true contributor stays open, and keep the edge
honest." But that state is *incoherent*: if the contributor is a true
edge, Y isn't done; if Y is done, it wasn't a true edge. So B doesn't
preserve truth — it permits a "done" claim with an undelivered, still-
declared value-chain piece. E keeps the gate honest and makes the escape
(retract the false edge) the honest action. The loose-edge friction B
was trying to fix turned out to be a *readiness* concern, not a closure
one, so it didn't need the closure gate weakened at all.
