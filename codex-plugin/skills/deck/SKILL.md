---
name: deck
description: "Front door for the deck — the operating substrate for ALL persistent work. AUTO-INVOKE when the user references the deck/methodology/workflow OR at session start as a reminder that every user request producing persistent work must flow through Skill(create-card) → Skill(advance-card) → Skill(finish-card). XP-style story cards on a kanban board, designed for AI-agent collaborators."
---

## Codex GoC Command

When this skill says `goc ...`, resolve the executable before running the
command:

- In the `game-of-cards` source checkout, use `uv run goc ...`.
- If `goc` is already on `PATH`, use `goc ...`.
- If this skill is loaded from the Game of Cards Codex plugin, use the
  bundled helper at `<plugin-root>/skills/_goc-bootstrap.sh ...`; the plugin
  root is the parent directory that contains both `skills/` and `bin/`.
- If the plugin root is not obvious from the loaded skill path, locate the
  helper with:

```bash
GOC_BOOTSTRAP=$(find "$HOME/.codex/plugins/cache" -path '*/game-of-cards/*/skills/_goc-bootstrap.sh' -type f -perm -111 2>/dev/null | sort | tail -n 1)
test -n "$GOC_BOOTSTRAP" || { echo "GoC Codex plugin bootstrap not found" >&2; exit 127; }
"$GOC_BOOTSTRAP" --help
```

Use that helper path in place of bare `goc` for the rest of the skill. Do not
edit deck files directly just because `goc` is not on `PATH`.


# The Deck

`deck/` is the project's work-tracking surface. Each subdirectory is one
**card**: a unit of work — bug, story, epic, idea, derivation gap,
doc-drift catch — with frontmatter-driven status on a kanban board.

## Heritage & philosophy: agile for the age of agents

The deck inherits three traditions deliberately:

- **XP story cards (Beck, 1999).** One card = one unit of work,
  small enough to fit on an index card, with enough context that any
  team member can pick it up. We keep the size discipline; the medium
  is markdown instead of cardboard.
- **Scrum's Definition of Done (Sutherland & Schwaber).** Every card
  carries a checkbox-list DoD as a closure contract. `goc done
  <title>` refuses to flip the status until every box is `- [x]`. The
  contract is machine-checkable, not a verbal handoff.
- **Kanban (Anderson, Toyota lineage).** Status mutates; position on
  disk does NOT. A card stays at `deck/<title>/` for life — no moving
  to `done/`, no archiving. Cross-references stay valid through every
  state change.

The argument for keeping these now: original agile was a response to
**human handoff costs** — the 1990s problem of getting a feature from
analyst to developer to QA without losing intent. AI agents are the
most aggressive handoff-stress-test ever invented: dozens of
sub-agents, scheduled cron loops, and parallel /loop iterations all
read the same cards and mutate the same frontmatter. What was
"discipline" for human teams becomes **structurally load-bearing**
under that load:

- **Slug-as-URL.** `deck/<title>/` is a stable handle that survives
  status changes, agent rewrites, and supersession chains. Renaming
  breaks every commit message and prior cross-reference.
- **Machine-checkable DoDs.** A swarm cannot pattern-match "did we
  really finish this" the way a stand-up meeting can. The CLI's
  unchecked-box count is the closure gate.
- **Self-contained card bodies.** Hallway context evaporates between
  /loop iterations. Each card must carry its own evidence,
  reproduction recipe, and decision framing — agents cannot rely on
  conversational continuity.

## Game of Cards as the runtime, not a workflow

The deck is the **implementation** of the human's intent, not a
ceremony they opt into. A vibe coder types "I want a CSV export
button" and the system silently: files the card, drafts the body
from their words, advances it, implements, closes, commits. They
see the button. They do not see the card. If they ever ask "what's
in flight?", `Skill(scan-deck)` shows them the bookkeeping. If they
never ask, they never need to know it exists.

This separates the methodology's **rigor** (machine-checkable DoDs,
audit-trail commits, supersession chains, hook-enforced routing)
from its **visibility** (zero by default). Same principle as a
database engine: the user writes SQL; transactions, locks, and
write-ahead logs happen invisibly. Our cards are the rows; deck.py
is the engine; the skills are the query interface.

Three operating modes coexist:

- **Session mode.** A human is talking. The UserPromptSubmit hook
  detects work intent in their prompt; Claude runs the card pipeline
  silently while answering. Card operations are NEVER announced
  unless the user explicitly asks to see the deck.
- **Autonomous mode.** No human is steering. `Skill(pull-card)`
  runs on `/loop pull-card 30m` or `/schedule pull-card
  weekday 09:00`, draining the `human_gate: none` queue.
  `Skill(audit-deck)` runs on a slower cadence to keep the queue
  fed. The deck advances overnight. The human wakes up to commits
  that closed cards they never explicitly claimed.
- **Andon-cord mode.** A human is unblocking the line. When
  `pull-card` hit a question only a human could answer, it raised
  the gate (`none → decision` or `none → session`) and parked the
  card. `Skill(scan-deck)` surfaces parked cards (triage default
  on bare invocation or "what's up?"); `Skill(scan-deck) decisions
  to make` walks each decision-gated card via `AskUserQuestion`
  and calls `Skill(decide-card)` per answer. Gate lowered → next
  `pull-card` claims and implements per the recorded decision.
  Lean's pulled-cord pattern: humans resolve the cause, agents
  restart the line.

Multiple Claude sessions on the same project work cards in parallel.
The `status: active` field is the soft lock; git's merge handles
the rare race when two sessions claim the same card simultaneously
(whichever commits first wins). The user can have N parallel chats
going while M scheduled agents work the deck — they ride the events
as they occur, present or absent as resources allow.

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
| `goc --board` | Multi-column kanban view. A `⏳` after an open card's `[contribution]` marker means "not ready to pull" — either a derived dependency-block (a non-terminal `advanced_by` prereq) or an active impediment overlay (`waiting_on` / future `waiting_until`). No `⏳` ⇒ pullable. |
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

## The worldview: Game of Cards

The methodology has a name: **Game of Cards** — the *Game of Thrones*
echo is deliberate. Work in a complex codebase plus an AI-agent swarm
is **political** (cards have stakeholders, factions, conflicting
opinions), **unforeseeable** (you cannot predict which threads
activate or which cards get superseded), **high-stakes** (a wrongly-
flipped DoD ripples through commit history and supersession chains),
and **uncontrollable** (you don't drive the swarm; events surface,
you respond).

The 1990s agile methodologies optimized for human-team handoffs.
Game of Cards adds the worldview layer: **you ride the events as
they occur**. `Skill(next-card)` exists because work is *taken* when
capacity exists, not *pushed* when work appears (Kanban pull, made
structural). `Skill(audit-deck)` exists because the deck reflects
emergent reality — new cards surface as agents discover gaps the
original plan didn't anticipate. The architecture already encoded
the no-control stance; the name finally gives it words.

Hence the rebrand: not "todos" (an undifferentiated list) but **the
deck** (named cards with stable handles, lifecycle, and contracts).
Not "ticket tracker" but a card surface designed for the read-pattern
of a swarm.

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
rewritten). See `Skill(card-schema)`'s "What goes where" subsection
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
elapses). See `Skill(card-schema)` "Three-axis 'stuck' model" for the
full contract.

**Closure is not frozenness.** Terminal status retires the card from
the live queue but does not freeze the directory. When new evidence
surfaces later — a bug found weeks after close, an assumption
invalidated by follow-up work, a successor card that reframes the
original — file a new card AND amend the closed one with a forward
pointer (one-line dated entry appended to `log.md`, optional `>
Later evidence:` pointer at the top of the README body). The deck is
the durable record of what was learned, not just what shipped; each
closed card stays as the live entry-point to the full thread. See
`Skill(finish-card)` "After closure" for the cross-reference format.

`status`, the `waiting_on` overlay, and `human_gate` are three
orthogonal axes. An exogenous wait on an agent-observable condition
(upstream release, PR merge, dependency publication, scheduled
re-check) sits as `waiting_on: external` (+ optional `waiting_until`)
on a `status: open` card with `human_gate: none` — a future autonomous
run verifies the condition cleared and `goc wait <title> --clear`s
the overlay without human involvement. Raise `human_gate` to
`decision`/`session` only when human judgement is the unblocker. See
`Skill(card-schema)` for the full orthogonality contract.

## The 9 action skills

One skill per job; compose, don't bundle.

- `Skill(scan-deck)` — browse the deck. Triage default surfaces
  parked cards (gate ≠ none); also filtered queues, kanban board,
  JSON dump, and the "decisions to make" Q&A flow. Read-only by
  default; the Q&A mode calls `Skill(decide-card)` per answer.
- `Skill(next-card)` — auto-pick the highest-leverage open
  `gate=none` card to work on next. Read-only; does NOT flip status.
- `Skill(create-card)` — file a new card with proper frontmatter,
  DoD scaffold, and (for bug-class) reproduce.py stub.
- `Skill(advance-card)` — flip status (open→active, *→open, *→disproved,
  *→superseded) and manage the `waiting_on` impediment overlay
  (`goc wait`). Wraps `goc status` and `goc wait`. Status + overlay
  only — `human_gate` is `decide-card`'s responsibility.
- `Skill(decide-card)` — the human's Andon-cord lowering action.
  Records `<decision> + <because>` on a parked card and flips gate
  `decision`/`session` → `none`. Status stays `open` so the next
  `pull-card` claims and implements per the recorded decision.
- `Skill(finish-card)` — close a card: tick DoD, append closure log,
  run `goc done <title>`, then run any project-specific post-close or
  commit handoff defined by the consuming repo's hook.
- `Skill(card-schema)` — schema reference (read-only): required
  fields, enums, canonical tags with predicates, DoD detection,
  relationship invariants.
- `Skill(refine-deck)` — hygiene pass: retag stale cards, prune
  unverified parks, surface cards citing defunct file:lines, propose
  new canonical tags.
- `Skill(audit-deck)` — discovery: hunt for one previously-undocumented
  defect / derivation gap / doc drift / missing test. Files via
  `Skill(create-card)`.
- `Skill(standup)` — daily read: active + impeded cards (those
  carrying a `waiting_on` overlay), closures since yesterday, cards
  waiting on a human decision gate.
- `Skill(retrospective)` — backwards analysis of the last N closed
  cards: cluster by tag, surface recurring failure modes, propose
  generalization candidates.

## Migration legacy

Most pre-2026-05-01 entries (≈135 of 270) carry the placeholder
`definition_of_done: |\n  - [x] (criteria not found in source README;
manual review needed)`. The legacy `bugs/` and `tasks/` trees did not
encode a closure contract per entry — closure was implicit ("the
FIXED.md row appeared"). The migration could not reconstruct what each
prior closure verified, so it inserted a checked placeholder for
already-`done` entries (validation passes; forensic record is the
closing commit's body) and an unchecked placeholder for still-`open`
entries (forces the next `Skill(finish-card)` run to write a real DoD
before `goc done <title>` will accept closure).

The two skills `find-todo` and `work-todo` were the v1 names. Their
responsibilities split:

- v1 `/find-todo` → `Skill(audit-deck)` (discovery + filing).
- v1 `/work-todo` → `Skill(next-card)` + `Skill(advance-card)` +
  `Skill(finish-card)` (selection, status mutation, closure).

Old commits referencing `/find-todo` or `/work-todo` continue to make
sense — the workflows are conserved, just decomposed.
