# Log

## 2026-05-26 — Decision: exclude terminal descendants from scheduler value

**Decision:** descendants whose status is terminal (`done`, `disproved`,
`superseded`) do NOT contribute to a card's `compute_values` scheduling
score. `value_for` skips them in the `advances` walk.

**Rationale:** the deck-as-scheduler-vs-record contract in `AGENTS.md`
states the scheduler axis walks `advances` edges across *live* cards,
while the record axis is the one that includes closed cards (so a cold
reader can reconstruct history). A completed descendant can no longer be
unblocked, so amplifying a live card's priority on the strength of work
that is already done contradicts the scheduler semantics. The
`compute_values` docstring previously framed chain depth as an
unrestricted "curation signal"; that prose was the source of the
ambiguity and is now corrected to state the live-only rule explicitly.
The api-contract document is the higher-authority source; the
implementation docstring is brought in line with it.

The previously-flagged example — an `open low` card scoring
`1.0 + 0.7·9.0 = 7.3` purely from a `done high` descendant, outranking a
genuinely-open `medium` (3.0) — no longer occurs: the open card now
scores its bare rank (1.0).

**Implementation:** `goc/engine.py` `value_for` skips a resolved
descendant when `by_title[dest].status in TERMINAL_STATUSES`. Live
descendants still contribute unchanged. `reproduce.py` asserts all three
cases (open→done, open→superseded, open→open). `unverified` tag dropped.

## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/engine.py` `value_for` (in `compute_values`) — skip descendants whose status is terminal so completed work no longer amplifies a live card's scheduler value; docstring states the live-only rule.
- **Verification**: reproduce.py exits 0 — open→done A scores 1.0 (was 7.3); open→open A still scores 7.3.
- **Audit**: PASS — invokes the deck-as-scheduler-vs-record contract (AGENTS.md): scheduler axis walks `advances` across live cards only.
- **Project impact**: n/a
- **Tests**: no pytest suite; reproduce.py 3/3 cases pass; `goc validate` clean; plugin mirrors synced.
- **Bundled with**: none

## Closure verification (2026-05-26T21:18:48Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
