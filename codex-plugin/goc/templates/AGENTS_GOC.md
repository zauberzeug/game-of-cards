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

**Closure is not frozenness.** When new evidence surfaces after a card
closes, file a new card for the new work and amend the closed card
with a forward pointer (dated `log.md` append; optional `> Later
evidence:` line atop the README). See `Skill(finish-card)` "After
closure" for the format.

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
