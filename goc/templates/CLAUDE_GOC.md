## Game of Cards is the Runtime

The methodology has a name: **Game of Cards** — the *Game of Thrones* echo is deliberate. Work in a complex codebase + AI-agent swarm is political, unforeseeable, high-stakes, uncontrollable. You don't drive the swarm; events surface, you respond. Full heritage: `Skill(deck)`.

**Game of Cards is the implementation, not a workflow the user opts into.** The deck is the runtime; cards are the persistent state; skills are the API; `goc` is the engine. When the user types "I want a CSV export button", the system silently files the card from their words, advances it, implements, closes, commits — they see the button, not the bookkeeping. Vibe coders never need to learn the deck; the methodology's rigor (DoDs, audit trail, supersession chains) is preserved invisibly. If the user ever wants to look behind the curtain: `Skill(scan-deck)`.

**Two operating modes coexist.**

### Session mode — silent runtime under user prompts

When a human is talking, the `UserPromptSubmit` hook detects work intent and biases Claude to run the GoC pipeline silently. **Card operations are NOT announced** ("I'll file a card now…" — never). The user's words ARE the briefing; the deck records what they wanted; the implementation lands. They see code, not bookkeeping. The pipeline (silent):

1. `Skill(scan-deck)` — does a card already cover this?
2. `Skill(create-card)` — if not, file from the user's words. Title is user-facing, PO-readable.
3. `Skill(advance-card) <title> active` — claim.
4. Implement.
5. `Skill(finish-card) <title>` — close + commit.

**No-card exceptions** (zero work, no card): exploration ("explain X", "why is Y this way?"), one-shot tooling ("git status", "rebase this"), course-corrections inside an active card.

### Autonomous mode — agents drain the queue while you sleep

`Skill(pull-card)` performs ONE complete round of the GoC loop: pull a `human_gate: none` card off the queue → claim → work → close → commit. Designed for `/loop pull-card 30m` (drains in foreground while you work in another session) or `/schedule "weekday 09:00 pull-card"`. Companion routines: `/schedule extend-deck weekly` (keeps the queue fed), `/schedule improve-deck monthly` (hygiene). The user wakes up to commits; the deck moved overnight.

Multiple Claude sessions on the same project work cards in parallel — the `status: active` field is the soft lock; git's merge handles rare claim-races.

### Andon-cord mode — human lowers the gate so the line resumes

When `pull-card` hits a card it cannot decide (a project-specific judgement call, a missing default, a scope reframing), it raises the gate to `decision` or `session` and exits. The card sits parked until a human resolves the *cause* — not the implementation, just the call. This is Lean's Andon-cord pattern: the worker pulls the cord; a supervisor walks over, resolves the root issue, and restarts the line.

The human's path: ask "what's up?" / "where do you need me?" → `Skill(scan-deck)` surfaces parked cards, grouped by gate, oldest-first, with the `## Decision required` body section preview. For streamlined capture: `Skill(scan-deck) decisions to make` walks each decision-gated card, capturing the choice and reasoning per card. Decision recorded → gate lowered → next `pull-card` claims and implements.

## Deck Workflow

`deck/` is the canonical work-tracking surface — a kanban board of XP-style story cards. Use it for ALL persistent items: ideas, findings, bugs, issues, tasks, epics, stories. Don't park them in scratch notes or chat alone.

The 11-skill family (`Skill(deck)` is the front door) decomposes the workflow into single-responsibility verbs:

- **Browse**: `Skill(scan-deck)` for triage default + filtered views + decision Q&A; `Skill(next-card)` for auto-pick of the highest-leverage `gate=none` card.
- **File new**: `Skill(create-card)` scaffolds frontmatter + DoD.
- **Advance**: `Skill(advance-card)` flips status (`open → active → blocked / disproved / superseded`); `Skill(finish-card)` closes with DoD enforcement + commit.
- **Decide (human handoff)**: `Skill(decide-card)` records `<decision> + <because>` and lowers the gate from `decision`/`session` → `none`, re-enabling autonomous claiming.
- **Hygiene**: `Skill(improve-deck)` retags stale cards, prunes parks; `Skill(extend-deck)` hunts new defects, inconsistencies, and doc drift.
- **Reference**: `Skill(card-schema)` for required/optional fields, enums, canonical tags.

The CLI is `goc` (open queue by default; `--board` for multi-column kanban; `--json` for machine-readable; filters: `--tag`, `--impact`, `--status`, `--stage`, `--human-gate`, `--done --since YYYY-MM-DD`). The validator (`goc validate`) runs as a pre-commit hook against `^deck/.*$`. **The deck must not drift from the code** — every commit that touches a card mutates its frontmatter in the SAME commit (`goc done <title>`, `goc status <title>`, `goc move <old> <new>`).

Schema: invoke `Skill(card-schema)`. Workflow philosophy + lifecycle: invoke `Skill(deck)`.
