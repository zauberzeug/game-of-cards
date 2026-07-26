## 2026-07-22 — filed from a downstream drain observation

Filed after the Zoe App drain repeatedly auto-pulled a verify-first card
(`conversations-send-and-receive-file-attachments`) whose DoD needs a
human to trigger a production `chat.send` with an attachment plus a
live-device check — work no unattended agent may do. The card was born at
`human_gate: none`, so the picker kept offering it; ~2–3 passes were spent
before the Zoe App drain's own release-attempt counter
(`_count_release_attempts` / `release_claim_if_stuck` in its `tool/_lib.sh`)
tripped and escalated it to `human_gate: session`.

Two observations drove the filing: (1) that escalation net lives in a
downstream drain wrapper, so every other `goc` consumer gets no backstop;
(2) even with the net, the first passes are wasted — the DoD carried the
human-only signal (`EMPIRICAL:` items) at creation, so detection at
`goc new` / `goc validate` could prevent the waste rather than bound it.

Scope-checked against the closest open card,
`aggregation-epics-head-block-the-autonomous-pull-queue` (open, gate
decision): same symptom (picker offers an unclosable card), different root
cause (pure-aggregator with no work of its own vs. real work only a human
can execute). Kept distinct; cross-linked in the README. Filed
`human_gate: decision` because the fix relocates a behaviour from downstream
wrappers into the engine's gate lifecycle and a human should pick the
mechanism (A/B/C/D) first. Left uncommitted for review.

## 2026-07-22T05:26:01Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

How should the system stop offering a human-only card to unattended
workers? Options (not mutually exclusive):

- **A — Detect at `goc new`.** When a card is filed with a DoD item whose
  method class implies human-only execution (a heuristic over
  `EMPIRICAL:` items mentioning live/production/device actions), warn and
  suggest `--gate session`. Cheapest prevention, but heuristic and easy
  to phrase around; a warning, not a guarantee.
- **B — `goc validate` lint.** A warning-class finding
  (`HUMAN_ONLY_DOD_UNGATED` or similar) for an open `human_gate: none`
  card carrying a human-only `EMPIRICAL:` item. Runs in CI and on every
  refine pass, so it catches cards filed before the rule existed. Still
  advisory; relies on the tag being present and honest.
- **C — Core release-count auto-escalation.** Promote the downstream
  drain's release-attempt counter into `goc` itself: track auto-releases
  per card, and after a configurable budget escalate `human_gate` to
  `session` with a logged reason. Guarantees the loop self-terminates for
  *every* consumer, not just those who hand-rolled a net — but it is a
  reactive net, so it still spends the budget-many passes first. Best
  paired with A or B.
- **D — Do nothing in core; document the convention.** Rely on card
  authors to set `human_gate: session` on verify-first cards, and on each
  drain to build its own net (status quo). Rejected framing, listed for
  completeness: it is exactly the status quo that produced the wasted
  passes and pushed the fix into a downstream wrapper.

Recommendation leans **B + C**: the validate lint prevents most cases at
authoring/refine time across all consumers, and the core auto-escalation
is the backstop for the ones that slip through (or were filed before the
lint). A human should choose before implementation, since C relocates a
behaviour currently owned by downstream wrappers into the engine's gate
lifecycle.


## 2026-07-26T07:07:56Z: decision recorded

B + A' (hooked at `goc publish`, not `goc new`) land in this card; the C escalation backstop splits into its own card and is implemented as a two-rung waiting_on -> human_gate ladder with no attempt counter. — `goc new` writes only a placeholder DoD (card_is_draft, engine.py:2405), so authoring-time detection must hook `goc publish`, where the authored DoD first reaches the queue; A' and B then share one predicate across two call sites at near-zero marginal cost. C splits out because it alone needs new engine authority to mutate human_gate plus its own coupling-invariant test. Both counter designs were rejected -- log.md headings are heterogeneous (colon vs em-dash, engine- vs hand-written), so a count measures deliberation rather than failed pulls, and a frontmatter integer is machine-only telemetry that churns README frontmatter against the parallel-agent commit-safety rules; the existing self-clearing waiting_until overlay already encodes the rung and carries a human-readable reason an integer cannot.. Gate decision → none.

## 2026-07-26: decision expanded, DoD rescoped, C split out

Follow-up to the entry above, recording what the one-line decision does
not carry.

**Option A was not merely refined — as written it was unimplementable.**
It specified detection at `goc new`, but `goc new` stamps `draft: true`
and writes a placeholder DoD; the authored DoD only exists later. A
heuristic there would inspect `SCAFFOLD_DOD_PLACEHOLDER` and find
nothing. The hook moved to `_cmd_publish` (`goc/engine.py:5347`), where
the authored DoD first reaches the queue and where the sibling
`is_placeholder_scaffold` guard already lives. That relocation is also
what keeps A' worth having next to B: it fires while the author still
holds the context to set the gate, whereas B fires in CI/refine when
nobody does. A' and B must share one `dod_is_human_only` predicate
across two call sites, per the define-once rule `card_is_draft` and the
`human_gate` predicate cluster already follow.

**C split out** to
`escalate-repeatedly-auto-released-cards-without-an-attempt-counter`
(filed 2026-07-26, gate `none`). It alone needs new engine authority to
mutate `human_gate` and its own coupling-invariant coverage; bundling it
here would block the cheap prevention behind the expensive backstop. No
value-flow edge between the two — neither blocks the other, and they fix
one symptom through independent mechanisms (heuristic here, observed
behaviour there).

**Counter designs rejected**, both preserved in the README so they are
not re-derived: counting `## ` headings in `log.md` measures
deliberation rather than failed pulls (heading formats are already
heterogeneous across `goc decide` / `goc done` / `goc move` / hand-written
entries) and would make prose load-bearing; a frontmatter integer is
machine-only telemetry that churns the card's hottest file against the
parallel-agent commit-safety rules. The self-clearing `waiting_until`
overlay already encodes the rung and carries a human-readable reason.

DoD rescoped from the generic "implement the chosen mechanism" to five
concrete boxes covering the shared predicate, the two call sites, the
no-false-positive test, and the docs/mirror sync. The PROCESS box is
ticked by this decision.

## 2026-07-26: decision REWOUND — recorded without reading the prerequisite

The two entries above are superseded. The decision was recorded without
reading
[`human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property`](../human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property/),
which was filed the same morning (05:52Z), carries `advances:` this card,
and whose own DoD requires reconciling with this card "whose premise this
card corrects." The `advanced_by` edge landed on disk concurrently with
the session that recorded the decision and was not re-read before
deciding.

Gate restored `none → decision` by hand (no verb raises a gate — the
missing symmetry is itself a DoD item on the prerequisite card). The
`## Decision` block was removed from the README and `## Decision
required` restored. DoD un-ticked and de-scoped back to a mechanism
choice, with a new first box requiring the prerequisite to be decided
first, and the regression box extended to cover the mixed-card case.

Two concrete defects in the rewound decision:

1. **The validate lint was card-level.** The prerequisite states that a
   lint keying on "any `EMPIRICAL:` item mentioning a device or
   production ⇒ gate the card" misfires on every mixed card, and that any
   shipped mechanism must key off *which* items are human-only, not
   *whether any* is. The rewound DoD box said "flags every card carrying
   a human-only DoD item" — exactly the rejected shape.
2. **The escalation ladder punished progress.** It escalated after two
   releases-without-close regardless of whether boxes were ticked. The
   prerequisite requires distinguishing a productive pass from a no-op
   one; the downstream card that motivated all of this has eight DoD
   items with exactly one human-only, so earlier gating would have frozen
   seven workable items.

Not everything was discarded — three findings were promoted into the
README as constraints on the options rather than as a decision: option A
cannot hook `goc new` (it only ever sees the placeholder DoD; the hook
must be `_cmd_publish`), counting `## ` headings in `log.md` is not a
usable attempt metric, and any counter must reset on progress. A new
option E was added: fold into the prerequisite and close as superseded if
per-item gating wins there.

The split-out card
[`escalate-repeatedly-auto-released-cards-without-an-attempt-counter`](../escalate-repeatedly-auto-released-cards-without-an-attempt-counter/)
was returned to `draft: true` rather than deleted — its counter analysis
stands, but its escalation trigger inherits defect 2 and must not be
implemented before the prerequisite is decided.
