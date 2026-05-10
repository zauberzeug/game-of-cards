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
