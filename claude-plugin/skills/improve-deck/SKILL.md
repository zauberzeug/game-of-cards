---
name: improve-deck
description: Deck hygiene pass — retag stale cards, prune 90-day unverified parks, surface defunct file:line references, surface orphaned dependencies (epics with no children, meta-fix families not wired, log.md migration TODOs), surface engineer-jargon titles for retitling, propose new canonical tags. AUTO-INVOKE when user says "tidy up the deck", "check for stale cards", "hygiene pass", "clean up the queue", "archive old", "audit the deck", or invokes /improve-deck. The board itself gets refactored each iteration (XP refactor mercilessly + Kanban continuous improvement).
---

# Improve the deck

XP's **"refactor mercilessly"** (Beck, 1999) applied to the work
surface, paired with Kanban's **continuous improvement** (Anderson):
every iteration the BOARD gets better, not just the code on it. A
deck read by humans and swarms of agents accumulates rot the moment
filing slows down — stale parks, defunct cites, missing summaries,
tags whose predicate no longer fires. The same first-principles edge
that catches code drift catches deck drift; this skill is the recurring
tax that keeps the read-pattern guarantee alive.

Surface rot and propose corrective edits — never apply them silently.
Categories:

- `tags: [unverified]` parks older than 90 days that nobody has
  reproduced or refuted.
- `status: open` cards whose body cites a file path that has since
  been renamed or deleted (line numbers beyond EOF).
- Cards missing a `summary:` field, leaving triage views blind.
- Tags applied without their predicate firing (per
  `Skill(card-schema)` "Tag application criteria").
- Coherent epic-shaped bodies of work that lack a canonical
  grouping tag.
- **Orphaned dependencies** — relational rot. Epics with zero
  linked children; meta-fix cards whose body lists a family roster
  but `advances: []`; open cards with legacy `**Depends on:** /
  **Next:** / **Part of:**` markers in body but empty schema
  arrays; unactioned `log.md` migration TODOs (`formerly parent: X`
  / `formerly spawned_from: X`). The schema validator already
  enforces edge SYMMETRY at commit time; this skill catches edge
  ABSENCE, which is invisible to the validator.

Each surfaced issue gets a one-line recommendation; the user or
autonomous loop decides whether to flip to `Skill(advance-card)`,
`Skill(create-card)` (for a SCHEMA.md PR), or move on.

## Step 1 — sanity floor

!`.claude/skills/_goc-bootstrap.sh validate`

If validate fails, fix the half-edges / unknown tags / missing
required fields FIRST. Hygiene runs on a valid deck.

## Step 2 — survey by category

### Stale unverified parks

!`.claude/skills/_goc-bootstrap.sh --tag unverified -v`

For each entry: check `created` against today's date. Cards parked
> 90 days that nobody has reproduced or refuted are decay
candidates. Options:

- **Retry the falsifying recipe.** If the body's
  "what-evidence-would-falsify-it" recipe is now feasible (infra
  exists, sweep budget available), run it. On evidence: drop the
  `unverified` tag (promote) or flip to `disproved`.
- **Demote to disproved.** If three independent rounds have failed
  to reproduce, the lead is dead. `Skill(advance-card) <title>
  disproved` with a one-line "Three rounds attempted; no
  reproduction" rebuttal.
- **Keep parked.** Add a one-line note in `log.md` explaining why
  this round didn't have the budget; the 90-day clock resets.

### Stale-open cards (no log activity)

!`.claude/skills/_goc-bootstrap.sh --status open --json | head -100`

Cards with `status: open` whose `log.md` has no entries in 60+
days are at risk of being forgotten. For each: read the body,
decide if the lead is still real, and either:

- Re-prioritize via `Skill(next-card)` (recommend it on the next
  loop iteration).
- Escalate the gate from `none` to `decision` if blocking on a
  framing question.
- Flip to `disproved` if the original evidence has rotted away.

### Defunct file:line citations

For each open card, check its body cites against current code:

```bash
# Pseudo: for each cited file:line in body, verify file exists and
# line ≤ EOF. Cards with broken cites are surfaced.
```

A defunct citation usually means the cited code was refactored.
Recommendation: re-read the card; either update the citation in
place (mechanical edit, no status change) or — if the refactor
also fixed the defect — close via `Skill(finish-card)` with a
note "fixed incidentally by <commit-hash>".

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

Per `Skill(card-schema)`'s tag application criteria, every applied
tag must fire on title / H1 / first ~2500 chars of body. Survey
random 5–10 cards per round; for any tag whose predicate doesn't
fire, strip it (mechanical frontmatter edit).

### Orphaned dependencies

The validator catches asymmetric edges (`A.advances=[B]` but
`B.advanced_by` missing `A`). It does NOT catch edge ABSENCE — a
card with `advances: []` looks fine to the schema even when its
body declares a family roster, an epic membership, or a
predecessor in prose. This is the failure mode that left 122/126
open cards naked after the v1→v2 migration.

Four sub-checks:

```bash
# 1. Epics with no linked children
goc --status open --json | \
  python3 -c "
import json, sys
d = json.load(sys.stdin)
epics = [c for c in d if 'epic' in (c.get('tags') or [])]
for ep in epics:
    n = len(ep.get('advances') or []) + len(ep.get('advanced_by') or [])
    if n == 0:
        print(f'{ep[\"title\"]}: epic with zero linked children')
"

# 2. Meta-fix cards with empty advances (family roster declared
#    in body but not wired). A surfaced card is either (a) a
#    genuine meta-fix whose family wasn't wired, or (b) a
#    mistagged instance that should not carry the meta-fix tag —
#    distinguish by reading the body for "## Family roster" / "n
#    instances" prose.
goc --tag meta-fix --status open --json | \
  python3 -c "
import json, sys
d = json.load(sys.stdin)
for c in d:
    if not (c.get('advances') or []):
        print(f'{c[\"title\"]}: meta-fix with empty advances (family unwired or mistagged?)')
"

# 3. Open cards with legacy markers in body but empty schema arrays
grep -lE '^\*\*(Depends on|Next|Part of):\*\*' deck/*/README.md | \
  while read f; do
    title=$(basename "$(dirname "$f")")
    arrays=$(goc --json --status all 2>/dev/null | \
      python3 -c "
import json, sys
d = json.load(sys.stdin)
for c in d:
    if c['title'] == '$title':
        n = len(c.get('advances') or []) + len(c.get('advanced_by') or [])
        print(n)
        break
")
    if [ "$arrays" = "0" ]; then
      echo "$title: legacy depends-on/next/part-of marker but advances/advanced_by empty"
    fi
  done

# 4. Unactioned migration TODOs in log.md
grep -rE 'Migration v1.v2.*formerly `(parent|spawned_from):' deck/ --include='log.md' | \
  sed -E "s|deck/([^/]+)/log\.md:.*formerly \`(parent\|spawned_from): ([a-z0-9-]+)\`.*|\1 → \3|" | \
  sort -u
```

For each surfaced card: read the body and the migration log
note, judge the direction (epic-of → epic `advanced_by` child;
predecessor → child `advanced_by` predecessor; family member →
instance `advanced_by` meta-fix), and apply via `goc advance X
--by Y`. The advance command is symmetric-by-construction so the
validator stays happy.

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

The optional `--llm` flag is a hook for a Sonnet-batched pass that
extends the audit to summary quality + per-DoD-item issues. Currently
a stub; the integration story is tracked in
`deck/auto-validate-card-titles-summaries-and-dods/log.md`. The
regex-only mode is sufficient as the always-on baseline; the
batched LLM pass is a nice-to-have, not load-bearing.

## Step 3 — propose new canonical tags

When a coherent body of work emerges that isn't covered by an
existing tag (e.g., a sprint of 6 cards all about a specific
research front), propose a new canonical tag for SCHEMA.md.

This is a **propose, don't apply** step — adding a tag is a
SCHEMA.md PR per the schema's "Adding new tags" rule. Output the
proposed tag + its predicate as text; let the human (or a
follow-up `Skill(create-card)` filing) handle the PR.

## Step 4 — surface and recommend

For each surfaced issue, output one line:

```
<title>: <issue> → recommend Skill(<advance-card | create-card>) ...
```

Example output:

```
heuristic-driven-eta: tags=[unverified] created 2026-01-15 (107d) → recommend Skill(advance-card) → disproved (3 rounds without reproduction)
auth-cookie-expires-too-soon: body cites auth/cookie.ts:84 (file ends at L72) → recommend mechanical citation update
schultz-eligibility-trace-doc-drift: missing summary → wrote ≤3-sentence summary into frontmatter
operating-amplitude-followup-12: tag=plasticity but no plasticity-class predicate fires → strip tag
```

## Cross-references

- `Skill(advance-card)` — for status flips (disproved / re-open
  / unblock).
- `Skill(card-schema)` — tag application predicates and the schema
  PR contract for new tags.
- `Skill(create-card)` — when a hygiene issue surfaces a NEW
  defect (e.g., the defunct citation reveals a real bug, not just
  rot), file via create-card.
- Project commit workflow — to land the hygiene edits as a
  `chore(deck): hygiene pass — <date>` commit.
