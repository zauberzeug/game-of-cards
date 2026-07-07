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

Scrum's **Backlog Refinement** (Schwaber & Sutherland) applied to the
work surface, paired with Kanban's **continuous improvement** (Anderson):
every iteration the BOARD gets better, not just the code on it. A
deck read by humans and swarms of agents accumulates rot the moment
filing slows down — stale parks, defunct cites, missing summaries,
tags whose predicate no longer fires. The same first-principles edge
that catches code drift catches deck drift; this skill is the recurring
tax that keeps the read-pattern guarantee alive.

The consuming repo may extend this hygiene flow via
`.game-of-cards/hooks/refine-deck.md` (already loaded above) — e.g.,
to demand a pattern-discovery pass with specialized reviewers,
override the 90-day decay threshold, surface project-specific
categories beyond the generic ones below, or declare which artifacts
(modules, sub-packages, demos) are in-scope for framework-tier
findings so cluster-finding doesn't span the entire repo
indiscriminately — out-of-scope artifacts surface as
`contribution: low` or skip-with-note, never Tier-1/Tier-2 verdicts
or meta-decision-card cluster members.

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

Categories:

- `tags: [unverified]` parks older than 90 days that nobody has
  reproduced or refuted.
- `status: open` cards whose body cites a file path that has since
  been renamed or deleted (line numbers beyond EOF).
- Cards missing a `summary:` field, leaving triage views blind.
- Tags applied without their predicate firing (per
  the `card-schema` skill "Tag application criteria").
- Coherent epic-shaped bodies of work that lack a canonical
  grouping tag.
- **Orphaned dependencies** — relational rot. Epics with zero
  linked children; meta-fix cards whose body lists a family roster
  but carry zero edges (neither `advances` nor `advanced_by`); open
  cards with legacy `**Depends on:** /
  **Next:** / **Part of:**` markers in body but empty schema
  arrays; unactioned `log.md` migration TODOs (`formerly parent: X`
  / `formerly spawned_from: X`). The schema validator already
  enforces edge SYMMETRY at commit time; this skill catches edge
  ABSENCE, which is invisible to the validator.

Each surfaced issue gets a disposition before commit. Hygiene
findings: apply the mechanical edit directly. Structural findings:
file via the `create-card` skill, disprove via
the `advance-card` skill (with `<title> disproved`), or park `--tag unverified`
per Step 4.5 — never leave surfaced findings undisposed.

## Step 1 — sanity floor

`goc validate 2>&1 || echo "[refine-deck] validate found rot; the skill body below will route you through fixing it"`

If validate fails with half-edge errors, run `goc repair-edges` to
preview the missing reverse-edge writes, then `goc repair-edges
--apply` and re-run `goc validate`. If repair reports a structural
cycle, park that card for human review instead of guessing which edge
is wrong. Fix unknown tags / missing required fields FIRST too.
Hygiene runs on a valid deck. The precondition above is intentionally
soft-gated so a failing validator surfaces its output *into* this
skill rather than blocking the skill load — the recovery guidance
in this body is exactly what the user came here for.

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

`goc --status open --json | head -100`

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

```bash
# Pseudo: for each cited file:line in body, verify file exists and
# line ≤ EOF. Cards with broken cites are surfaced.
```

A defunct citation usually means the cited code was refactored.
Recommendation: re-read the card; either update the citation in
place (mechanical edit, no status change) or — if the refactor
also fixed the defect — close via the `finish-card` skill with a
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

Per the `card-schema` skill's tag application criteria, every applied
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

# 2. Meta-fix cards with zero edges (neither advances nor
#    advanced_by — family roster declared in body but not wired).
#    Count BOTH edge fields: a correctly-wired umbrella carries
#    advanced_by=[siblings] with advances=[], so testing advances
#    alone false-positives every wired family. A surfaced card is
#    either (a) a genuine meta-fix whose family wasn't wired, or
#    (b) a mistagged instance that should not carry the meta-fix
#    tag — distinguish by reading the body for "## Family roster" /
#    "n instances" prose.
goc --tag meta-fix --status open --json | \
  python3 -c "
import json, sys
d = json.load(sys.stdin)
for c in d:
    n = len(c.get('advances') or []) + len(c.get('advanced_by') or [])
    if n == 0:
        print(f'{c[\"title\"]}: meta-fix with zero edges (family unwired or mistagged?)')
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

Example output:

```
heuristic-driven-eta: tags=[unverified] created 2026-01-15 (107d) → the `advance-card` skill → disproved (3 rounds without reproduction)
auth-cookie-expires-too-soon: body cites auth/cookie.ts:84 (file ends at L72) → updated citation to auth/cookie.ts:67
schultz-eligibility-trace-doc-drift: missing summary → wrote ≤3-sentence summary into frontmatter
operating-amplitude-followup-12: tag=plasticity but no plasticity-class predicate fires → stripped tag
research-front-emerging-clusters: 6 cards coalescing around <topic>, no canonical tag → the `create-card` skill <new-tag-pr-card>
```

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

The only escape valve: a candidate that's clearly noise (the
file:line doesn't exist; the predicate that surfaced it has since
fired correctly elsewhere) AND has no underlying substance can be
silently dropped.

This rule applies to **structural** candidates only — the kind
project-local pattern-discovery passes produce. Hygiene findings
(stale parks, defunct cites, missing summaries, predicate-failing
tags, orphaned-edge sub-checks) keep their mechanical-apply path —
they're applied directly in Step 2 and need no Step 4.5 audit.

This rule applies even when the round produces confirmed hygiene
edits. The "zero applied → ≥1 disposition" rule is the
_minimum_; this is the _maximum-amnesia bound_.

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
