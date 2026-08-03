# refine-deck reference — rationale, scripts, and edge cases

Companion to `SKILL.md`. Each section below is routed from the core
skill; read the one that matches the situation at hand.

## Rationale

Scrum's **Backlog Refinement** (Schwaber & Sutherland) applied to the
work surface, paired with Kanban's **continuous improvement** (Anderson):
every iteration the BOARD gets better, not just the code on it. A
deck read by humans and swarms of agents accumulates rot the moment
filing slows down — stale parks, defunct cites, missing summaries,
tags whose predicate no longer fires. The same first-principles edge
that catches code drift catches deck drift; this skill is the recurring
tax that keeps the read-pattern guarantee alive.

The consuming repo may extend this hygiene flow via
`.game-of-cards/hooks/refine-deck.md` (loaded in the core skill) —
e.g., to demand a pattern-discovery pass with specialized reviewers,
override the 90-day decay threshold, surface project-specific
categories beyond the generic ones, or declare which artifacts
(modules, sub-packages, demos) are in-scope for framework-tier
findings so cluster-finding doesn't span the entire repo
indiscriminately — out-of-scope artifacts surface as
`contribution: low` or skip-with-note, never Tier-1/Tier-2 verdicts
or meta-decision-card cluster members.

## Orphaned-dependency sub-check scripts

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
#    alone false-positives every wired family. `meta-fix` is a
#    `judgment` row, so a surfaced card is a prompt to read it, not
#    a verdict. Three dispositions, and only the first edits YAML:
#      (a) an umbrella whose family members are CARDS that were
#          never wired — wire them (goc advance X --by Y);
#      (b) an umbrella whose family members are CODE SITES, not
#          cards — nothing to wire; the roster lives in the body
#          and the card is correctly tagged. Leave it;
#      (c) a card that plainly is not about a family or its root
#          cause — report it for a human to retag deliberately.
#    Absence of a literal `meta-fix` is not evidence of (c): repos
#    name umbrellas by shape, so most umbrellas never contain the
#    string. Do not strip on this sub-check.
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

## Tag sweeps

A predicate that *under*-fires is dangerous in a way an over-firing
one is not, because the curated grouping it removes is unrecoverable
and unflagged. Three rules keep the sweep safe.

**The action on a non-firing row is `report`, never `strip`.** Print
the card, the row, and what could not be confirmed; leave the
frontmatter alone. This is the rule that bounds the other two: get
them wrong and a pass emits a wrong line of output instead of deleting
curated data. Strip a tag only as a deliberate per-card judgment,
recorded as such — never as the mechanical consequence of a predicate
that did not fire.

**Score each tag against its own row, never against a house rule.**
The title / H1 / first ~2500 chars of body in `Skill(card-schema)`'s
tag criteria is the *default* surface; individual rows widen or
replace it, so applying the default window to a row that widened it
scores correct cards as mistagged.

**A `judgment` row is not evaluable, and non-firing is not failure.**
The `check` column splits the table. `state` rows (`bug`, `epic`,
`unverified`) are satisfied out of frontmatter, edges, and files, so
they can be scored outright. `judgment` rows (`story`,
`documentation`, `test`, `api-contract`, `infra`, `meta-fix`) turn on
what the card means; the patterns printed in those rows are
recognition aids, and there is nothing to grep that decides
membership. Leave a judgment row unless the card plainly *contradicts*
it — a `story`-tagged card that is transparently a defect finding,
say, or one carrying `bug` as well (those two rows are disjoint, so
that pair is always a real finding).

`meta-fix` is the cautionary example rather than the evaluable one.
Twice it was written as a literal-plus-edge test and twice a sweep
measured most of the tagged population as mistagged; the cards it
failed were the umbrellas the tag exists to group, because an umbrella
acquires a literal or a wired roster incidentally and often late. See
`Skill(card-schema)`'s `reference.md` § "Why rows split into `state`
and `judgment`" for the three measurements.

## Quality-pass `--llm` flag

The optional `--llm` flag on `goc quality-pass` is a hook for a
Sonnet-batched pass that extends the audit to summary quality +
per-DoD-item issues. Currently a stub; the integration story is
tracked in `deck/auto-validate-card-titles-summaries-and-dods/log.md`.
The regex-only mode is sufficient as the always-on baseline; the
batched LLM pass is a nice-to-have, not load-bearing.

## Example Step 4 output

```
heuristic-driven-eta: tags=[unverified] created 2026-01-15 (107d) → Skill(advance-card) → disproved (3 rounds without reproduction)
auth-cookie-expires-too-soon: body cites auth/cookie.ts:84 (file ends at L72) → updated citation to auth/cookie.ts:67
schultz-eligibility-trace-doc-drift: missing summary → wrote ≤3-sentence summary into frontmatter
operating-amplitude-followup-12: tag=plasticity but no plasticity-class predicate fires → reported (tag kept; disposition is a reader's call)
research-front-emerging-clusters: 6 cards coalescing around <topic>, no canonical tag → Skill(create-card) <new-tag-pr-card>
```

## Step 4.5 scope notes

The park-or-disprove rule applies to **structural** candidates only —
the kind project-local pattern-discovery passes produce. Hygiene
findings (stale parks, defunct cites, missing summaries,
orphaned-edge sub-checks) keep their mechanical-apply path — they're
applied directly in Step 2 and need no Step 4.5 audit. A
predicate-failing tag is the exception in the other direction: it is
reported in Step 2 output and edits nothing, so it needs no
disposition either.

The rule applies even when the round produces confirmed hygiene
edits. The "zero applied → ≥1 disposition" rule is the
_minimum_; this is the _maximum-amnesia bound_.

The only escape valve: a candidate that's clearly noise (the
file:line doesn't exist; the predicate that surfaced it has since
fired correctly elsewhere) AND has no underlying substance can be
silently dropped.
