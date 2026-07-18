## Game of Cards — methodology runtime

This repo uses [Game of Cards](https://github.com/zauberzeug/game-of-cards):
tasks are directories under `.game-of-cards/deck/` with frontmatter,
body, and a Definition-of-Done. The CLI is `goc` (`goc --help`).

When the user asks for persistent work, the agent invokes the matching
GoC skill — file → claim → implement → close — silently. The card
records intent; the implementation lands. The user sees `goc` (queue)
or `goc --board` (kanban) only if they ask.

**Skills carry the methodology** (loaded on demand — read the skill
before improvising):

- `deck` — overview, operating modes, Andon cord, daily verbs.
- `card-schema` — frontmatter, DoD, status enums, YAML conventions.
- `create-card` / `advance-card` / `finish-card` — file, claim, close.
- `pull-card` / `next-card` / `scan-deck` — queue and browse.
- `kickoff` — first-time setup in a fresh repo.

Always-loaded rules — one line each; the named skill carries the full
contract:

- **README is a dashboard; log.md is the journal.** When evidence
  changes a claim, rewrite the README section in place — never append
  a correction below the stale claim. `Skill(card-schema)` § "What
  goes where".
- **Closure is not frozenness.** Post-close evidence → file a new
  card and amend the closed one with a forward pointer.
  `Skill(finish-card)` § "After closure".
- **Three-axis stuck model.** Progress `status`, derived
  dependency-readiness (`⏳`, advisory), and the `waiting_on`
  impediment overlay (`goc wait`) are independent axes.
  `Skill(card-schema)` § "Three-axis stuck model".
- **The deck is scheduler AND record.** Relationship edges are
  first-class even on closed cards; supersession is a typed link.
  `Skill(card-schema)` § "Deck as scheduler vs deck as record".

Project-local extensions live under `.game-of-cards/`; see its
`README.md` if present. The `<!-- BEGIN GOC -->` markers above are the
discovery signal that this repo uses GoC.
