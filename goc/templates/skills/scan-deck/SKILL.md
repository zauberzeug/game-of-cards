---
description: Browse the deck — supportive triage view, filtered queues, kanban board, JSON dump, decision Q&A. Read-only by default. AUTO-INVOKE when user says "what's up?", "where do you need me?", "what's open", "show me the deck", "list cards", "kanban view", or "decisions to make". ALSO auto-invoke before Skill(create-card) to dedup against existing titles. Kanban first practice (make work visible).
argument-hint: omit for triage view; "decisions to make" for interactive Q&A; title/tag/filter expression for everything else
---

# Scan the deck

Kanban's first practice (Anderson): **make work visible**. You cannot
manage what you cannot see, and a swarm of /loop iterations cannot
prioritize against state it has to reconstruct from chat. This skill
renders the board for whoever's looking — human-supportive triage,
filtered queues, kanban columns, JSON dumps, and a structured
decision Q&A that closes the Andon-cord loop in one round.

Read-only **except** in the explicit "decisions to make" mode, which
calls `Skill(decide-card)` per parked card to lower gates.

User argument: $ARGUMENTS

## Mode A — bare invocation / "what's up?" / "where do you need me?"

The supportive default. Surface what's *blocking* progress (parked
cards) before what's *queued* (open work), because the human's
highest-leverage action is unblocking the line, not browsing it.

```bash
goc triage
```

This emits parked cards (gate ≠ none) grouped by gate, oldest-first,
with the `## Decision required` body section preview and an aged-days
badge. Then show a one-line summary of the open queue:

```bash
goc -v | head -10
echo "..."
goc | wc -l
```

**Why `-v` by default**: the `-v` flag adds a per-card summary line
that surfaces the qualitative context the `contribution` tier alone
can't capture (pong-active vs pong-DORMANT, recent regression vs old
doc-rot, blocking-other-work vs standalone). The agent picking from
the queue makes better importance judgments with summaries visible —
without them, "medium contribution" is opaque.

End with the discovery hint: **for streamlined decision capture,
suggest `Skill(scan-deck) decisions to make`**, which walks every
decision-gated card via AskUserQuestion in one round and records
each answer via `Skill(decide-card)`.

## Mode B — "decisions to make" (interactive Q&A)

Triggered by `Skill(scan-deck) decisions to make` (or matching
phrasings: "let me decide", "walk me through decisions",
"AskUserQuestion mode"). The fastest path to draining the human's
gate queue.

### Step 1 — fetch parked decisions

```bash
goc triage --json
```

Filter to `gate == "decision"` items. (Session-gated cards stay
parked — they need a real-time conversation, not a structured Q&A.
Note them at the end as out-of-scope for this round.)

### Step 2 — build options that bundle WHAT with WHY

For each decision card, parse the `decision_required` body section
and pre-author 2–3 options where **each option's `label` is a full
`<decision> — because <reason>` clause**. The `description` field
expands the trade-off context that lives below the label in the UI.

Why bundled: the reason for a choice IS what makes it the choice.
Asking WHY as a follow-up forces the user to re-reason a decision
they already made, and creates artificial branching when reasons
overlap across options. Bundling makes `decide-card`'s mandatory
`--because` discipline frictionless — one selection captures both.

Example:

```
label:       "Rewrite §3.4 to defer to §10.4 — because §10.4 is
              empirically anchored and matches shipping config"
description: "Sprint 2.44 coherence²-collapse theorem; pong +
              line_follower ship amp_diff; smallest disruption
              to API structure"
```

If the card lacks a `decision_required` body section with
enumerable options, infer from the card summary or fall back to a
single "Other (free text)" prompt where the user types one
sentence in the same form: `<my decision> — because <my reason>`.

Always include an "Other (free text)" option for cases where none
of the parsed options fit. Same split rule applies to free text —
if the user forgets the ` — because ` separator, prompt once for
clarification.

### Step 3 — paginate by four

AskUserQuestion caps at 4 questions per call, so present **batches
of 4 cards** by default. The cap is a tool constraint; treat it as
the UX policy too — 4 decisions is enough for one round of
attention, and walking 56 in a single sitting is implausible.

Between batches, ask via AskUserQuestion: *"Continue with the next
4 decisions, or pause here?"* The human can pause anytime; the
skill reports whatever was recorded plus a count of what's still
parked.

### Step 4 — call `Skill(decide-card)` per selection

For each chosen option, split the label on the **first** ` — because `
token to recover the WHAT and WHY clauses, then:

```bash
goc decide <title> \
    --decision "<text before ' — because '>" \
    --because "<text after ' — because '>"
```

(Or invoke `Skill(decide-card)` if the human prefers the skill
indirection.)

### Step 5 — summarize

Report one line: `recorded N decisions; M session-gated cards still
parked (out of scope, schedule a session); K decision-gated cards
remain (paused mid-walk — re-invoke to continue)`.

## Mode C — filters (everything else)

Existing flags compose with AND semantics on tags, intersect on
other fields. Use these when the human knows what they're looking
for.

```bash
goc -v                          # open queue + summaries (RECOMMENDED DEFAULT)
goc -v --tag bug --contribution high  # filter + summaries
goc -v --human-gate none        # autonomous-safe queue + summaries
goc -v --status all             # everything + summaries
goc --done --since 2026-04-01   # throughput query (terse OK)
goc                              # terse table (titles + contribution only — use sparingly)
goc -vv                          # adds STAGE/CREATED + DoD checklist + cross-refs
goc --json                       # machine-readable
goc --board                      # multi-column kanban
goc show <title>                  # full card body
```

**Default to `-v`**: summaries surface the qualitative context that
the `contribution` tier alone can't capture (pong-active vs pong-DORMANT,
recent regression vs old doc-rot, blocking-other-work vs standalone).
Use bare `deck.py` only when scanning for titles/counts (the terse
table is faster to read at a glance but loses importance signal).

If the user passed a title, also run `deck.py show <title>` so the
full body lands in the conversation.

## Why the triage view is the default

Without it, the human's first answer to "what's up?" is "126 open
cards, sorted by contribution" — a wall of work that hides the fact that
**most of those 126 cards are NOT waiting on the human at all**.
They're waiting on `pull-card`, on a scheduled run, on someone
claiming them. Buried among them: ~80 cards that ARE waiting on the
human and have been for days. Pull-card cannot drain them. Without a
triage default, those cards rot, and the autonomous half of the
deck stalls behind cords nobody lowered.

This is exactly the failure mode Lean's Andon was invented to
prevent: a stopped line with no visible signal. The triage view is
the signal — the parked cards are the lit cords, and they go on top.

## Cross-references

- `Skill(decide-card)` — the human's one-action handoff for parked
  cards; the natural follow-up to mode A and the engine of mode B.
- `Skill(pull-card)` — the autonomous worker that raises the gate
  when stuck. The other end of the Andon loop.
- `Skill(next-card)` — auto-pick the highest-leverage card to *work*
  on (`gate=none` only). Use after triage when you want to take
  something off the queue yourself, not just look.
- `Skill(extend-deck)` — discovery hunt. Use when the queue feels
  thin or you suspect undocumented defects.
- `Skill(create-card)` — file a new card. Use when you spotted
  something during scan that isn't in the queue yet.
- `Skill(card-schema)` — schema reference. Use when filter results
  show fields you don't recognize.
