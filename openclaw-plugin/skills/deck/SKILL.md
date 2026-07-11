---
name: deck
description: Front door for the deck — the operating substrate for ALL persistent work. AUTO-INVOKE when the user references the deck/methodology/workflow, or at session start as a reminder that persistent work flows through the `create-card` skill → the `advance-card` skill → the `finish-card` skill.
---

## When to invoke

Invoke when the user references the deck, the methodology, or the workflow — or at session start as a reminder that every user request producing persistent work must flow through the `create-card` skill → the `advance-card` skill → the `finish-card` skill. XP-style story cards on a kanban board, designed for AI-agent collaborators.

# The Deck

`deck/` is the project's work-tracking surface. Each subdirectory is one
**card**: a unit of work — bug, story, epic, idea, derivation gap,
doc-drift catch — with frontmatter-driven status on a kanban board.

The deck is the **runtime of the human's intent, not a ceremony they
opt into**: rigor (machine-checkable DoDs, audit-trail commits,
supersession chains) is separated from visibility (zero by default).
The user sees the code, not the bookkeeping, unless they ask.

**Background and rationale live in `reference.md`** — a sibling file
in this skill's directory. Read the named section only when the
situation actually calls for it:

| Situation | `reference.md` section |
|---|---|
| Why XP/Scrum/Kanban discipline is load-bearing for agent swarms | Heritage & philosophy |
| Why card operations stay invisible; full operating-mode prose | Game of Cards as the runtime |
| Why the methodology is named Game of Cards | The worldview |
| New evidence after a card closed | Closure is not frozenness |
| How status / `waiting_on` / `human_gate` compose | Status, overlay, and gate are orthogonal axes |
| Pre-2026-05-01 placeholder DoDs; v1 `find-todo`/`work-todo` names | Migration legacy |

## Three operating modes

- **Session mode.** A human is talking. the agent runs the card pipeline
  silently while answering; card operations are NEVER announced unless
  the user explicitly asks to see the deck.
- **Autonomous mode.** No human is steering. the `pull-card` skill runs
  on a loop or schedule, draining the `human_gate: none` queue;
  the `audit-deck` skill keeps the queue fed on a slower cadence.
- **Andon-cord mode.** A human is unblocking the line: `pull-card`
  parked a card behind a raised gate; the `scan-deck` skill surfaces
  parked cards, the `decide-card` skill records the answer and lowers
  the gate, the next pull resumes the work.

Multiple sessions work cards in parallel. `status: active` is the
soft lock; git's merge handles the rare simultaneous-claim race
(whichever commits first wins).

## What this looks like in practice

**Session mode (silent runtime).** When the user asks for persistent
work — "rename the button to Export", "add a CSV export", "fix the
auth bug" — run the GoC pipeline silently:

1. Check the deck — does a card already cover this? (`goc --tag <topic>`)
2. If not, file a card: `goc new <kebab-title>` and edit the body.
3. Claim it: `goc status <title> active`.
4. Implement.
5. Close: `goc done <title>`, then commit the work and closure.

Card operations are NEVER announced — the user sees the code, not the
bookkeeping. **No-card exceptions** (zero work, no card): exploration
("explain X", "why is Y this way?"), one-shot tooling ("git status",
"rebase this"), course-corrections inside an active card.

**Autonomous mode.** Before recommending or claiming new work, agents
check `goc --status active` and treat listed cards as already-claimed
soft locks. The pull principle is what makes this safe: work isn't
pushed at agents on a timer; agents pull on their own terms, filtered
to gate=none. The human steers by curating WHAT'S in the queue and
at what gate.

**Andon-cord path.** When a human asks "what's up?" / "where do you
need me?", surface parked cards (oldest-first, with `## Decision
required` body section preview). Decision recorded → gate lowered with
`goc decide <title> --decision "..." --because "..."` → next pull-card
claims and implements per the recorded decision.

## Daily CLI verbs

| Verb | What it does |
|---|---|
| `goc` | Show the open queue (value-sorted). |
| `goc --board` | Multi-column kanban view. A `⏳` after an open card's `[contribution]` marker flags any of three signals: `human_gate != none` (parked for a human — **not pullable**), an active impediment overlay (`waiting_on` / future `waiting_until` — **not pullable**), or an advisory derived dependency-block (a non-terminal `advanced_by` prereq — **still pullable**, just flagged as "has an open upstream"). Only the first two hide a card from `pull-card` / `next-card` / `goc --ready`; a dependency-block does not. So `⏳` ⇏ unpullable — check the cause. |
| `goc --status done --since YYYY-MM-DD` | Recently closed cards. |
| `goc new <title>` | Scaffold a new card under `.game-of-cards/deck/<title>/`. |
| `goc status <title> <state>` | Flip status (open/active/disproved/superseded). |
| `goc wait <title> --reason <r> [--until <date>]` | Set the impediment overlay for exogenous waits; `--clear` to drop it. |
| `goc done <title>` | Close + DoD enforcement (no auto-commit). |
| `goc decide <title> --decision X --because Y` | Lower gate from decision/session → none. |
| `goc validate` | Validate every card's frontmatter (pre-commit-friendly). |

Run `goc --help` for the full verb list. Schema and enum constraints
surface in `goc validate` error messages. Project-local tag extensions
live in `.game-of-cards/canonical-tags.md`.

## The deck layout

```
deck/
  SCHEMA.md                 # canonical schema (frontmatter IS the schema)
  README.md                 # navigation + conventions
  deck.py                   # CLI; computes filtered views from frontmatter
  <title>/                   # one dir per card; never moves on state change
    README.md               # frontmatter + dashboard body — latest knowledge + current state
    log.md                  # append-only journal — history, details, decisions, flow
    reproduce.py            # OPTIONAL — declared in DoD when present
    [other validation scripts]
```

One title, one directory, forever. Status changes mutate frontmatter,
not paths.

Two files, two edit disciplines: the README is the **dashboard**
(rewritten in place as understanding evolves so a cold reader sees
only what is true now); `log.md` is the **append-only journal**
(history, details, decisions, and flow preserved verbatim, never
rewritten). See the `card-schema` skill's "What goes where" subsection
for the routing rule.

## Lifecycle

```
   open ──→ active ──→ done (terminal, DoD-100% required)
    │
    ├──→ disproved (terminal; body documents rebuttal)
    └──→ superseded (terminal; typed `superseded_by` → successor,
                     rationale appended to log.md)
```

`open` is the queue. `active` claims the work. `done`, `disproved`,
and `superseded` are all terminal — none deletes the directory; the
forensic record stays.

A card that is **temporarily not workable** does not move to a
separate status; the three-axis model expresses it as either derived
dependency-readiness (an `advances` prereq is still open and shows as
"awaiting" in the queue, advisory only) or the stored impediment
overlay (`waiting_on` + optional `waiting_until`, set via `goc wait`,
hides the card from the ready queue until cleared or the date
elapses). See the `card-schema` skill "Three-axis 'stuck' model" for the
full contract. Closed cards stay amendable, and the three axes are
orthogonal — `reference.md` § Closure is not frozenness and § Status,
overlay, and gate are orthogonal axes.

## The action skills

One skill per job; compose, don't bundle.

- the `scan-deck` skill — browse the deck. Triage default surfaces
  parked cards (gate ≠ none); also filtered queues, kanban board,
  JSON dump, and the "decisions to make" Q&A flow. Read-only by
  default; the Q&A mode calls the `decide-card` skill per answer.
- the `next-card` skill — auto-pick the highest-leverage open
  `gate=none` card to work on next. Read-only; does NOT flip status.
- the `create-card` skill — file a new card with proper frontmatter
  and a DoD scaffold (reproduce.py is authored by hand for bug-class
  cards, not scaffolded by the tool).
- the `advance-card` skill — flip status (open→active, *→open, *→disproved,
  *→superseded) and manage the `waiting_on` impediment overlay
  (`goc wait`). Wraps `goc status` and `goc wait`. Status + overlay
  only — `human_gate` is `decide-card`'s responsibility.
- the `decide-card` skill — the human's Andon-cord lowering action.
  Records `<decision> + <because>` on a parked card and flips gate
  `decision`/`session` → `none`. Status stays `open` so the next
  `pull-card` claims and implements per the recorded decision.
- the `finish-card` skill — close a card: tick DoD, append closure log,
  run `goc done <title>`, then run any project-specific post-close or
  commit handoff defined by the consuming repo's hook.
- the `card-schema` skill — schema reference (read-only): required
  fields, enums, canonical tags with predicates, DoD detection,
  relationship invariants.
- the `refine-deck` skill — hygiene pass: retag stale cards, prune
  unverified parks, surface cards citing defunct file:lines, propose
  new canonical tags.
- the `audit-deck` skill — discovery: hunt for one previously-undocumented
  defect / derivation gap / doc drift / missing test. Files via
  the `create-card` skill.
- the `standup` skill — daily read: active + impeded cards (those
  carrying a `waiting_on` overlay), closures since yesterday, cards
  waiting on a human decision gate.
- the `retrospective` skill — backwards analysis of the last N closed
  cards: cluster by tag, surface recurring failure modes, propose
  generalization candidates.
