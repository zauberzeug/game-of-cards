# deck reference — heritage, worldview, and legacy notes

Companion to `SKILL.md`. Each section below is routed from the core
skill; read the one that matches the situation at hand.

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

## Closure is not frozenness

Terminal status retires the card from the live queue but does not
freeze the directory. When new evidence surfaces later — a bug found
weeks after close, an assumption invalidated by follow-up work, a
successor card that reframes the original — file a new card AND amend
the closed one with a forward pointer (one-line dated entry appended
to `log.md`, optional `> Later evidence:` pointer at the top of the
README body). The deck is the durable record of what was learned, not
just what shipped; each closed card stays as the live entry-point to
the full thread. See `Skill(finish-card)` "After closure" for the
cross-reference format.

## Status, overlay, and gate are orthogonal axes

`status`, the `waiting_on` overlay, and `human_gate` are three
orthogonal axes. An exogenous wait on an agent-observable condition
(upstream release, PR merge, dependency publication, scheduled
re-check) sits as `waiting_on: external` (+ optional `waiting_until`)
on a `status: open` card with `human_gate: none` — a future autonomous
run verifies the condition cleared and `goc wait <title> --clear`s
the overlay without human involvement. Raise `human_gate` to
`decision`/`session` only when human judgement is the unblocker. See
`Skill(card-schema)` for the full orthogonality contract.

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
