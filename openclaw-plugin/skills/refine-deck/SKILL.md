---
name: refine-deck
description: Deck hygiene pass — retag stale cards, prune 90-day unverified parks, surface defunct references, orphaned dependencies, and jargon titles. AUTO-INVOKE on "tidy up the deck", "hygiene pass", "clean up the queue", or /refine-deck. The board itself gets refactored each iteration.
---

## When to invoke

Invoke when the user says "tidy up the deck", "check for stale cards", "hygiene pass", "clean up the queue", "archive old", "audit the deck", or invokes /refine-deck. Covers retagging stale cards, pruning 90-day unverified parks, surfacing defunct file:line references, surfacing orphaned dependencies (epics with no children, meta-fix families not wired, log.md migration TODOs), surfacing engineer-jargon titles for retitling, and proposing new canonical tags (XP refactor mercilessly + Kanban continuous improvement).

## Context (project-local extension)

Before running the body of this skill, the agent should see current deck state. Run these via the `goc` tool (top-level filters like `--status` / `--tag` / `--worker` map to the tool's `flags` parameter; the subcommand maps to `verb`). For bare-queue listings with no subcommand, shell out via the `exec` tool:

- `cat .game-of-cards/hooks/refine-deck.md 2>/dev/null || true`

# Refine the deck

Every iteration the BOARD gets better, not just the code on it: this
skill is the recurring hygiene tax that keeps the deck's read-pattern
guarantee alive as filing slows down and rot accumulates. The hook
above may extend the flow with project-specific categories or
thresholds (scope rules in `reference.md` § Rationale).

Surface rot and act on it before commit. Two action paths depending
on the finding's nature:

- **Hygiene findings** (mechanical: stale `unverified` parks, defunct
  file:line cites, missing summaries, predicate-failing tags,
  orphaned-edge mechanical wires) — apply the edit directly.
- **Structural findings** (epic-shaped clusters, missing
  canonical-reference families, contribution-recall proposals,
  meta-decision umbrellas, newly-emergent tag candidates surfaced
  by a project hook's pattern-discovery pass) — file via
  the `create-card` skill, disprove via
  the `advance-card` skill (with `<title> disproved`), or park
  `--tag unverified` per Step 4.5. "Surfaced and discussed in chat"
  is not a disposition.

**Long-form material lives in `reference.md`** — a sibling file in
this skill's directory. Read the named section only when the
situation actually applies:

| Situation | `reference.md` section |
|---|---|
| Why this pass exists; hook scope rules | Rationale |
| Running the four orphaned-dependency sub-checks | Orphaned-dependency sub-check scripts |
| `goc quality-pass --llm` | Quality-pass `--llm` flag |
| What the Step 4 report should look like | Example Step 4 output |
| Which findings Step 4.5 covers, escape valve | Step 4.5 scope notes |

## Step 1 — sanity floor

`goc validate 2>&1 || echo "[refine-deck] validate found rot; the skill body below will route you through fixing it"`

If validate fails with half-edge errors, run `goc repair-edges` to
preview the missing reverse-edge writes, then `goc repair-edges
--apply` and re-run `goc validate`. If repair reports a structural
cycle, park that card for human review instead of guessing which edge
is wrong. Fix unknown tags / missing required fields FIRST too.
Hygiene runs on a valid deck. The precondition above is intentionally
soft-gated so a failing validator surfaces its output *into* this
skill rather than blocking the skill load.

## Step 2 — survey by category

### Stale unverified parks

`goc --tag unverified -v`

For each entry: check `created` against today's date. Cards parked
> 90 days that nobody has reproduced or refuted are decay
candidates. Options:

- **Retry the falsifying recipe.** If the body's
  "what-evidence-would-falsify-it" recipe is now feasible (infra
  exists, sweep budget available), run it. On evidence: drop the
  `unverified` tag (promote) or flip to `disproved`.
- **Demote to disproved.** If three independent rounds have failed
  to reproduce, the lead is dead. the `advance-card` skill (with `<title>
  disproved`) with a one-line "Three rounds attempted; no
  reproduction" rebuttal.
- **Keep parked.** Add a one-line note in `log.md` explaining why
  this round didn't have the budget; the 90-day clock resets.

### Stale-open cards (no log activity)

`goc --status open --json 2>&1 | head -100`

Cards with `status: open` whose `log.md` has no entries in 60+
days are at risk of being forgotten. For each: read the body,
decide if the lead is still real, and either:

- Re-prioritize via the `next-card` skill (recommend it on the next
  loop iteration).
- Escalate the gate from `none` to `decision` if blocking on a
  framing question.
- Flip to `disproved` if the original evidence has rotted away.

### Defunct file:line citations

For each open card, check its body cites against current code:
verify each cited file exists and the cited line is ≤ EOF. A defunct
citation usually means the cited code was refactored. Re-read the
card; either update the citation in place (mechanical edit, no
status change) or — if the refactor also fixed the defect — close
via the `finish-card` skill with a note "fixed incidentally by
<commit-hash>".

### Missing summaries

Pre-2026-05-01 cards may have empty or absent `summary:` fields.
Surface these:

```bash
goc --status all --json | \
  jq '.[] | select(.summary == "" or .summary == null) | .title'
```

For each surfaced card: read the body, write a ≤3-sentence
summary into the frontmatter. Mechanical doc edit; no status
change.

### Tags without firing predicates

Per the `card-schema` skill's tag application criteria, every applied
tag must fire on title / H1 / first ~2500 chars of body. Survey
random 5–10 cards per round; for any tag whose predicate doesn't
fire, strip it (mechanical frontmatter edit).

### Orphaned dependencies

Relational rot the validator cannot see: it enforces edge SYMMETRY
at commit time but not edge ABSENCE — epics with zero linked
children; meta-fix cards whose body lists a family roster but carry
zero edges; open cards with legacy `**Depends on:** / **Next:** /
**Part of:**` body markers but empty schema arrays; unactioned
`log.md` migration TODOs (`formerly parent: X` / `formerly
spawned_from: X`). Run the four sub-checks in `reference.md`
§ Orphaned-dependency sub-check scripts, judge each surfaced card's
edge direction, and wire it via `goc advance X --by Y`
(symmetric-by-construction, so the validator stays happy).

### Card metadata quality pass

Title antipatterns + missing-summary scan via:

```bash
goc quality-pass --status all
```

What it surfaces:

- **Title antipatterns** — same regex predicates `goc new` uses to
  reject filings (engineer-jargon: `r88`, `path-2`, `phase-3`,
  `bug-140`, `_md_`/`_py_` infixes, camelCase tokens, math symbols).
  Catches legacy cards filed before the antipattern guard was wired.
  For each surfaced title: rename via `goc move <old> <new>` so
  cross-references rewrite atomically.
- **Missing summaries** — pre-2026-05-01 cards may lack the
  `summary:` frontmatter field that triage views (`goc -v`)
  depend on. For each: read the body, write a ≤3-sentence summary
  into the YAML.

## Step 3 — file new canonical tag candidates

When a coherent body of work emerges that isn't covered by an
existing tag (e.g., a sprint of 6 cards all about a specific
research front), file via the `create-card` skill a card whose DoD is
the SCHEMA.md PR adding the new tag + its predicate. Adding the
tag itself remains a SCHEMA.md PR per the schema's "Adding new
tags" rule; the filing that schedules that PR is imperative. Like
every other structural finding, the candidate either becomes a
card here, gets disproved (the proposed predicate doesn't fire on
a sufficient set), or parks `--tag unverified` per Step 4.5 — not
a chat-only proposal.

## Step 4 — surface and act

For each surfaced issue, output one line documenting the action
taken (hygiene) or the card filed / disprove flip / park
(structural):

```
<title>: <issue> → <action>
```

Sample lines in `reference.md` § Example Step 4 output.

## Step 4.5 — Park-or-disprove unfollowed structural candidates (mandatory)

Project hooks may extend Step 2 with a pattern-discovery pass that
surfaces more structural candidates than this round can verify and
file. Structural candidates that didn't get applied this round
MUST go somewhere durable before commit:

1. **Filed** as a new card via the `create-card` skill.
2. **Disproved** via the `advance-card` skill (with `<title> disproved`) — when
   you re-read the cited code and the candidate is wrong on its
   face.
3. **Unverified** via the `create-card` skill (with `... --tag unverified`) —
   when the candidate has substance but no verification budget
   this round. Body must include: the candidate's hypothesis with
   file:line (verbatim quote), why deferred, falsification recipe,
   the category (Step 2 sub-section) that surfaced it.

Scope, minimum-vs-maximum bound, and the noise escape valve:
`reference.md` § Step 4.5 scope notes.

## Cross-references

- the `advance-card` skill — for status flips (disproved / re-open
  / unblock).
- the `card-schema` skill — tag application predicates and the schema
  PR contract for new tags.
- the `create-card` skill — when a hygiene issue surfaces a NEW
  defect (e.g., the defunct citation reveals a real bug, not just
  rot), file via create-card.
- Project commit workflow — to land the hygiene edits as a
  `chore(deck): hygiene pass — <date>` commit.
