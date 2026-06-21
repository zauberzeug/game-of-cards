## Game of Cards — methodology runtime

This repo uses [Game of Cards](https://github.com/zauberzeug/game-of-cards):
tasks are directories under `.game-of-cards/deck/` with frontmatter,
body, and a Definition-of-Done. The CLI is `goc` (`goc --help`).

When the user asks for persistent work, the agent invokes the matching
GoC skill — file → claim → implement → close — silently. The card
records intent; the implementation lands. The user sees `goc` (queue)
or `goc --board` (kanban) only if they ask.

**Skills carry the methodology** (loaded on demand):

- `deck` — overview, operating modes, Andon cord, daily verbs.
- `card-schema` — frontmatter, DoD, status enums, YAML conventions.
- `create-card` / `advance-card` / `finish-card` — file, claim, close.
- `pull-card` / `next-card` / `scan-deck` — queue and browse.
- `kickoff` — first-time setup in a fresh repo.

Project-local extensions live under `.game-of-cards/`; see its
`README.md` if present. The `<!-- BEGIN GOC -->` markers above are the
discovery signal that this repo uses GoC.

**The README is a dashboard, not a changelog.** A card's `README.md`
shows only what is true *now*; `log.md` is the append-only journal of
how it got there. When new evidence corrects, refutes, or re-scopes a
finding the README already asserts, **rewrite the section that stated
it in place** — do not append a "Correction" / "Update" / "Latest
finding" block below it and leave the now-false claim standing. A card
that asserts both the old verdict and the new one contradicts itself,
and the stale top-framing is exactly what the next agent reads first.
In the same pass, reconcile the `summary:` frontmatter and any `> ⚠`
verdict banner, and record the *why* plus the demoted claim in
`log.md`. `goc decide` reminds you of this for re-scopes and `goc
validate` flags `DECISION_CONTRADICTS_VERDICT`, but the discipline
applies to every hand edit, not just the decide path — the lone
exception is a closed card's post-close amendment (next). See
`Skill(card-schema)` "What goes where" for the full contract.

**Closure is not frozenness.** When new evidence surfaces after a card
closes, file a new card for the new work and amend the closed card
with a forward pointer (dated `log.md` append; optional `> Later
evidence:` line atop the README). See `Skill(finish-card)` "After
closure" for the format.

**Three-axis "stuck" model.** A card that isn't moving fails for one
of three independent reasons, each with its own resolution mechanism:
(1) **progress status** — `open → active → done/disproved/superseded`
(no `blocked` peer; the status field doesn't model waits); (2) **derived
dependency-readiness** — a non-terminal `advanced_by` prereq is
computed at read time, self-clears when the prereq closes, and shows
as `⏳` on the board (advisory display only — does not hide a card
from `pull-card` / `next-card`); (3) **stored impediment overlay** —
`waiting_on` ∈ {`external`, `resource`, `deferred`} plus optional
`waiting_until` (ISO date), set via `goc wait <title> --reason <r>
[--until <date>]` and cleared with `--clear`. A future `waiting_until`
hides the card from queues; an elapsed one is surfaced by `goc
validate` as an SLE escalation. The overlay composes alongside
`human_gate` (decision/session waits) — a card may be `status: active`
AND carry `waiting_on`. See `Skill(card-schema)` "Three-axis stuck
model" for the full predicate.

**The deck is both a scheduler and a record.** The scheduler axis
walks `advances` edges across live cards to compose priority; the
record axis walks edges that include closed cards so a cold reader
can reconstruct the history of a decision. Closed-card relationship
edges are first-class: `goc validate` enforces referential integrity
for both axes regardless of either endpoint's status, and supersession
records a typed `superseded_by` / `supersedes` link (set atomically
by `goc status <old> superseded --by <new>`) so a reader landing on
a `superseded` card can be routed forward without parsing prose. See
`Skill(card-schema)` "Deck as scheduler vs deck as record" for the
full invariants.
