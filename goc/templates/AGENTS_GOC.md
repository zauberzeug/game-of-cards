## Game of Cards — methodology runtime

This repo uses [Game of Cards](https://github.com/zauberzeug/game-of-cards), a
backlog-as-folder methodology where each task is a directory under `deck/`
with frontmatter, body, and a Definition-of-Done checklist that decides when
it closes. The CLI is `goc`. Run `goc --help` for the full verb list.

**Three operating modes coexist.**

### Session mode — silent runtime under user prompts

When the user asks for persistent work ("rename the button to Export", "add
a CSV export", "fix the auth bug"), run the GoC pipeline silently:

1. Check the deck — does a card already cover this? (`goc --tag <topic>`)
2. If not, file a card: `goc new <kebab-title>` and edit the body.
3. Claim it: `goc status <title> active`.
4. Implement.
5. Close + commit: `goc done <title>`.

**Card operations are not announced to the user** — the user sees the
code, not the bookkeeping. The deck records what they wanted; the
implementation lands. They can look behind the curtain anytime with
`goc` (open queue) or `goc --board` (kanban view).

**No-card exceptions** (zero work, no card): exploration ("explain X",
"why is Y this way?"), one-shot tooling ("git status", "rebase this"),
course-corrections inside an active card.

### Autonomous mode — agents drain the queue

When the user runs `/loop pull-card 30m` or schedules `pull-card`, an
agent pulls one `human_gate: none` card off the queue, claims it, works
it end-to-end, and commits. Multiple parallel sessions work different
cards — the `status: active` field is the soft lock; git's merge handles
rare claim-races.

The pull principle is what makes this safe: work isn't pushed at agents
on a timer; agents pull on their own terms, filtered to gate=none. The
human steers by curating WHAT'S in the queue and at what gate.

### Andon-cord mode — human lowers the gate so the line resumes

When an agent hits a card it cannot decide (a project-specific judgement
call, a missing default, a scope reframing), it raises the gate to
`decision` or `session` and exits. The card sits parked until a human
resolves the *cause* — not the implementation, just the call. This is
Lean's Andon-cord pattern.

The human's path: ask "what's up?" / "where do you need me?" → the
agent surfaces parked cards (oldest-first, with `## Decision required`
body section preview). Decision recorded → gate lowered with
`goc decide <title> --decision "..." --because "..."` → next pull-card
claims and implements.

## Deck CLI

Daily verbs:

| Verb | What it does |
|---|---|
| `goc` | Show the open queue (impact-sorted). |
| `goc --board` | Multi-column kanban view. |
| `goc --status done --since YYYY-MM-DD` | Recently closed cards. |
| `goc new <title>` | Scaffold a new card under `deck/<title>/`. |
| `goc status <title> <state>` | Flip status (open/active/blocked/disproved/superseded). |
| `goc done <title>` | Close + DoD enforcement + commit. |
| `goc decide <title> --decision X --because Y` | Lower gate from decision/session → none. |
| `goc validate` | Validate every card's frontmatter (pre-commit-friendly). |

Run `goc validate` to see schema and enum constraints in error messages.
Project-local tag extensions live in `.game-of-cards/canonical-tags.md`.

## Project-specific extensions

Some repos extend GoC with project-local content (vocabulary, file-path
maps, consultation rubrics that pull-card invokes before raising the
Andon cord). When present, those live in `.game-of-cards/`. Read
`.game-of-cards/README.md` for the conventions used in this repo.

## Runtime-specific extras

When present, [`CLAUDE.md`](CLAUDE.md) contains Claude Code-only extras
such as prompt hooks and native command wrappers. Codex installs may
also provide GoC skill files under `.codex/skills/`; those skills wrap
the same `goc` CLI verbs above and should be treated as optional
runtime affordances, not separate methodology state.
