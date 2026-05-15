---
title: clarify-readme-as-dashboard-and-log-md-as-history
summary: "The card-schema, create-card, advance-card, and finish-card skill bodies describe `README.md` as the card's narrative / design-doc body — the same word (narrative) used for `log.md`, which conflates the two. The user's framing is sharper: `README.md` is a **dashboard** that always shows the *latest knowledge and current state* of the card, rewritten in place as understanding evolves so a cold reader sees only what is true now; `log.md` is the **append-only journal** for history, details, decisions, and flow, preserved verbatim and never rewritten. Make this distinction explicit in the skill templates so future humans and AI agents stop accumulating prose in README and stop dropping state-changes only into log."
status: active
stage: null
contribution: medium
created: "2026-05-15T05:46:25Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation, meta-fix]
definition_of_done: |
  - [ ] `card-schema/SKILL.md` Layout section explicitly frames `README.md` as a **dashboard** (latest knowledge + current state, rewritten as understanding evolves) and `log.md` as the **append-only journal** (history, details, decisions, flow). The single word "narrative" is no longer reused for both.
  - [ ] `card-schema/SKILL.md` carries a short "What goes where" rule of thumb so a cold reader can route a new piece of information without re-deriving the contract.
  - [ ] `create-card/SKILL.md` Step 5 ("write the body") names the README sections as a dashboard snapshot (problem framing, current understanding, fix proposal, DoD) and instructs the writer to **rewrite** these sections as understanding evolves rather than appending below them.
  - [ ] `advance-card/SKILL.md` and `finish-card/SKILL.md` make explicit which file receives what on each transition: state-of-the-world updates rewrite the README dashboard; transition narrative, decisions, and timestamps append to `log.md`.
  - [ ] `deck/SKILL.md` (front-door overview) Layout block mirrors the dashboard / journal framing so the distinction lands on the first read, not only inside `card-schema`.
  - [ ] All four (or five) edits mirrored byte-for-byte into `.claude/skills/...` and `claude-plugin/skills/...` and `openclaw-plugin/skills/...` via `pre-commit run sync-plugin-assets` (or its CI equivalent); `python scripts/sync_plugin_assets.py --check` passes.
  - [ ] `uv run goc validate` passes.
  - [ ] `tests/test_version_surfaces.py` (or whichever test covers skill-body parity) stays green.
worker: {who: "claude[bot]", where: main}
---

# clarify-readme-as-dashboard-and-log-md-as-history

## What the user said

> we shuould make more clear that the README.md of a card must be a
> dashboard describing latest knowledge and state. for history, details,
> decisions, flow we have the log.md.

The methodology already has the two files. The contract is implicit
in how every existing card is *actually* used, but the skill bodies
describe both files in language that blurs the line — and new readers
(human or agent) re-derive the distinction badly or not at all.

## The current wording (what to fix)

In `goc/templates/skills/card-schema/SKILL.md`, the Layout block reads:

```
deck/
  <title>/                   # one dir per card; never moves on state change
    README.md               # frontmatter + markdown body
    log.md                  # append-only round/phase narrative
```

A few lines later (line 42):

> The README is the **narrative**; sibling files are concrete
> artifacts the README references.

`log.md` is also called a "narrative" on line 33 and again across
`create-card`, `advance-card`, `finish-card`, and `deck`. The shared
word collapses the distinction. The cards we ship dogfood the right
shape — `decide-card-body-format-readme-vs-html-vs-flexible` keeps a
crisp dashboard with a `## Decision` section that captures the
resolved verdict in place, while `log.md` accrues the closure entry
— but no skill body teaches the writer to do that on purpose.

`goc/templates/skills/finish-card/SKILL.md` already gets it half-right
for log.md: "`deck/<title>/log.md` is the **append-only round/phase
narrative**; never rewrite existing entries." There is no equivalent
positive instruction for README. The closest is `create-card`
Step 5's list of body sections (Title, Summary, Location, What's
broken, Empirical evidence, Why it matters, Fix, DoD), which describes
*what to write the first time* but never says "rewrite these sections
in place as the picture sharpens."

## The framing to install

| File | Role | Edit discipline | Reader semantics |
|---|---|---|---|
| `README.md` | **Dashboard** of the card's latest knowledge and current state | Rewritten in place; outdated content is replaced, not amended below | A cold reader sees only what is true now |
| `log.md` | **Append-only journal** of history, details, decisions, and flow | Strictly appended; existing entries are never rewritten | A forensic reader can reconstruct how we got here |

Rule of thumb: **"If a future reader would be misled by reading this
in isolation, the dashboard needs the update; if the value is in the
sequence (when, by whom, why we changed our mind), the journal needs
the entry."** Most operations want both: rewrite the README to
reflect the new state, append a `log.md` entry that records the
transition.

## Why this matters

Three concrete failure modes the current wording does not prevent:

1. **README accumulation.** A worker drops a "Latest finding (date)"
   block at the bottom of the README. Three iterations later the
   reader scrolls through four contradicting "Latest" sections and
   has to date-sort by eye to find the current truth. The README
   stopped being a dashboard and became a stale ledger.

2. **log.md silence on state mutations.** A worker rewrites the
   README's `## Fix` section in place — correctly — but never
   appends a `log.md` entry recording *why* the fix proposal changed.
   `goc attest`'s closure verification reads `log.md` for the audit
   trail and finds a gap; future retrospectives lose the
   "we tried X first, then pivoted because Y" thread. Two existing
   cards (`state-flip-verbs-skip-log-md-entry`,
   `card-rename-leaves-old-title-in-body-and-skips-log-entry`)
   already document this failure mode for specific verbs; the
   meta-cause is that no skill body tells the *human* author that
   state mutations belong in the journal too.

3. **Decision-gate cards bleed prose.** A `human_gate: decision`
   card's README is supposed to be a tight options matrix with a
   `## Decision` section the human fills in. Without an explicit
   dashboard framing, the README accumulates pros / cons / counter-
   pros / "actually, on reflection ..." paragraphs that turn the
   card into a chat thread. The right pattern is: keep the matrix
   current, append each consideration round to `log.md`, resolve
   into the dashboard's `## Decision` section.

## Files to touch

Source-of-truth edits (then sync-plugin-assets mirrors them):

- `goc/templates/skills/card-schema/SKILL.md` — Layout block + a new
  "What goes where (README dashboard vs `log.md` journal)" subsection
  near the top so subsequent references can say "see Layout."
- `goc/templates/skills/create-card/SKILL.md` — Step 5 (write the
  body): add an explicit "the README is the dashboard — rewrite these
  sections as you learn, never append a new 'Latest finding' block"
  sentence; cross-link `log.md` for append-only events.
- `goc/templates/skills/advance-card/SKILL.md` — each status
  transition row: name which file receives the new state vs which
  file receives the transition entry.
- `goc/templates/skills/finish-card/SKILL.md` — Step 3 (DoD ticks)
  and Step 4 (closure log) already exemplify the split; make it
  explicit ("Step 3 updates the dashboard; Step 4 appends to the
  journal").
- `goc/templates/skills/deck/SKILL.md` — Layout block mirrors
  `card-schema` so the front-door read carries the same framing.

## Out of scope

- No engine change. `goc validate`, `goc show`, `parse_frontmatter`
  do not need to enforce the dashboard discipline mechanically —
  this is a *writing* contract, not a parser one. (A future card
  could add a soft linter for `## Latest finding (DATE)` patterns
  in README, but that is a separate idea.)
- No frontmatter change.
- No template rename. The files keep their names; only the
  prose around them changes.
- No retroactive rewrite of existing cards. New cards land in the
  sharpened style; old cards stay as historical artifacts.

## Related cards

- `card-skills-document-html-as-sibling-artifact-pattern` (closed,
  2026-05-09) — established the "card directory is a bundle"
  framing this card extends with role semantics.
- `state-flip-verbs-skip-log-md-entry` — specific failure mode
  this clarification addresses at the methodology level.
- `card-rename-leaves-old-title-in-body-and-skips-log-entry` —
  same family.
- `extend-utc-datetime-stamps-to-log-md-entries` — touches the
  same log.md authoring contract.
