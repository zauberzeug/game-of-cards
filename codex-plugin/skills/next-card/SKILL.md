---
name: next-card
description: "Pick the highest-leverage open card to work on next. Read-only verdict — does NOT flip status. AUTO-INVOKE when user says \"what's next\", \"pick something\", \"work on the queue\", \"what should I do\", \"next item\", \"drain the deck\", or initiates autonomous-loop work. Filters to `human_gate: none` for loop safety; Kanban pull principle (work is taken, not pushed)."
---

## Preflight

If any `!` block below shows `goc: command not found`, `Permission for this action has been denied`, or `no such file or directory: .game-of-cards/deck/`, **stop and invoke `Skill(kickoff)` first**. Kickoff detects which setup step is missing (CLI not installed, Bash allowance not granted, project state not scaffolded) and walks the user through it. Re-invoke this skill only after kickoff completes.

## Context

!`goc --status active -v 2>&1 | head -20`

!`goc --ready -v${GOC_WORKER:+ --worker "$GOC_WORKER"}`

# Pick the next card

Kanban's **pull principle** (Anderson): work is taken when capacity is
ready, not pushed by a planner. The runner — human or autonomous loop
— pulls one card at a time, top of the value-sorted queue, gated by
the autonomy ladder so a cron run cannot accidentally land a
research-impacting decision unsupervised. The deck is the queue; this
skill is the picker.

Recommend, do not claim. **Status does NOT flip here** — that is
`Skill(advance-card)`'s contract. The pull is a two-step gesture (pick,
then claim) so the human or /loop can abort between them without
half-state on disk.

Before recommending, read the active slice above. Active cards are claimed
soft locks; avoid recommending the same card or adjacent/conflicting work
unless the user explicitly asks to continue that active card.

User argument: $ARGUMENTS — if non-empty (a title or area like
an area tag or path prefix), narrow the queue. If empty, scan the full
ready slice (`--ready` keeps cards with open `advances` prereqs —
they are pullable with an "awaiting: <prereqs> (you may start)"
advisory line, since `advances` is a soft "should precede" not a hard
start-gate; hard waits are expressed via `waiting_on` /
`waiting_until`).

## Selection criteria

`goc` lists open cards sorted by value desc
then created asc. The top entry is the auto-pick candidate, subject
to the autonomy gate below.

### Contribution ladder

`high` outranks `medium` outranks `low`. Tags refine:

- **`contribution: high`** — wrong algorithm vs. cited literature, silent
  state corruption, broken public API, default config that
  contradicts the science. Doc claims that contradict an authoritative
  source — `tags: [documentation]` + `contribution: high` is the high-impact
  doc-quality slot. Treat these as load-bearing.
- **`contribution: medium`** — tolerance creep, vacuous assertions, tests
  that pass for the wrong reason, missing guard rails.
- **`contribution: low`** — README pinned-metric stale, docstring documents
  removed flag, stale references.

### Effort / independence / reversibility

- **Effort** — files touched, area of the project (library code
  vs application code, test coverage required). Library default
  changes carry higher cost.
- **Independence** — fixes whose effect can be verified without first
  fixing another card ship before the dependent ones. Read the
  body's "Why it matters" notes and any `advanced_by:` chain.
- **Reversibility** — prefer fixes with low blast radius. Local demo
  edits before library changes.

## Autonomy gate (the human_gate field)

Every card carries `human_gate: none | decision | session`:

- **`none`** — autonomous-loop-safe; cron may auto-pick.
- **`decision`** — needs ONE human go/no-go before work proceeds. The
  body MUST already carry the framing in a `## Decision required`
  section (per `Skill(card-schema)`). The human resolves
  asynchronously.
- **`session`** — needs interactive working session.
  Research-impacting framework derivations, open architectural
  choices.

**Pickability rule** (uniform across cron, /loop, explicit-by-title):

- `none` → recommend.
- `decision` → DO NOT recommend. End the session cleanly with a
  one-line summary pointing at the parked card and (if available)
  its body's `## Decision required` recommendation line. **Do not
  pause an idle agent.** No commits, no half-step writes — control
  returns to the human at their convenience.
- `session` → refuse to auto-pick under autonomous mode; ask for
  explicit confirmation under interactive mode that "yes, this is the
  working session for this topic." On no/silence, end like
  `decision`.

**Autonomous-mode rule** (`/loop`, cron, or any non-interactive
invocation): walk down `--ready` and recommend the top.
If every ready candidate is `decision` or `session`, the run
halts with a one-line summary listing the parked cards. Better to
ship nothing than to land a research move without a review
checkpoint.

**Explicit invocation by title**: read the named card via
`goc show <title>` and check the gate. Apply
the rules above on the specific card.

## Reclassify after reading

The `human_gate` is a hypothesis from the filing round; the body
often reveals the real shape. Before recommending work, re-check
whether the fix would:

- Close (or reopen) a gap in `docs/framework/*.md`.
- Pick one of two literature-backed mechanism candidates.
- Set a sign / direction convention.
- Introduce a new named primitive.
- Flip a default whose rationale is documented against a paper or
  axiom.
- Update an empirical / publication-tier claim.

If any apply, the gate should be at least `decision` (likely
`session`). **Recommend escalation via `Skill(advance-card)` to fix
the gate**, not working it autonomously. The right move is a 2-line
edit to the frontmatter + (if upgrading to `decision`) writing the
`## Decision required` section in the body — then the run ends and
the human comes back.

## Output

A single recommendation with:

- **Slug + one-line subject** of the recommended card.
- **2-line rationale** — contribution, why it's the highest-leverage open
  pick, any advanced_by edges that matter.
- **Next-step pointer**: typically "Run `Skill(advance-card) <title>
  active` to claim, then work it." If gated `decision` or `session`,
  point at the parked framing and end.

The output is a recommendation, not a plan. The user (or `/loop`)
picks whether to actually run `Skill(advance-card)` next.
