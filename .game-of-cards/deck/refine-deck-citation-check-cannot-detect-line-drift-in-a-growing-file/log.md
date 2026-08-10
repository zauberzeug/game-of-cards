
## 2026-08-10 — Filed, and connected to its root cause

Filed from the deck hygiene pass that repaired 389 drifted citations across 114
open cards (commit 69e1e4f2). The repair is what exposed the check: the pass
ran the specified `≤ EOF` test first, got a clean report on all 706 citations,
and only found the rot by anchoring each cite to the text it named at the card's
creating commit.

Connected as a cross-reference to
`static-source-guards-never-prove-they-can-catch-an-offender`, recorded there as
a fifth surface. No `advances` edge, per that card's stated convention for
evidence connections on an open decision.
