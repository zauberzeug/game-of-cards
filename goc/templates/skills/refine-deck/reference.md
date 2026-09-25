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

## Citation anchor check

**Why the bounds test does not work.** `line ≤ EOF` asks whether a
number is inside a file; citation rot asks whether the number still
names the code the card meant. The two coincide only when a file
SHRINKS past the cite, and source files grow. Measured on this
project's own deck: replaying every cite its open cards carried at
filing time, 482 of 528 had drifted onto unrelated code and the bounds
test flagged 0 of them. Its silence was indistinguishable from a clean
deck for the life of the deck, which is why the rule below anchors on
content rather than on range.

**Scope: what the cite claims, not where it sits.** A cite asserts either
where code lives NOW or what a command printed THEN, and only the first
is repairable. The second — pasted `grep -n` output in
`path:line:content` form, a `reproduce.py` transcript, a quoted error
message — is dated evidence, and rewriting its number fabricates a
result the command never produced, which costs the card the thing it
was filed to carry. Fenced code blocks hold both shapes, so "is it
inside a fence?" is the wrong question. The repairable fenced form is a
COMMENT LABEL — a `#` or `//` marker before the cite on its line, as in
`# goc/engine.py:N` above a quoted snippet or `... # engine.py:N`
beside one — and it is as much an assertion about HEAD as any prose
cite, so it is repaired by the same recipe. Apply the marker test,
repair the labels, and leave the records; report the records' count
under a heading of their own, apart from the declines in the table
below, because a decline is a repair the pass COULD not make while an
out-of-scope cite is one it MUST not. Undecidable → treat it as a
record: a stale label costs a reader one lookup, a rewritten transcript
costs the card its evidence.

Measured on this deck's open cards at the 2026-08-31 pass: 49 fenced
cites were comment labels and 17 were pasted output, spread over 31
cards. That pass read the silence the other way — every fenced cite is
evidence, skip it — and left 28 defunct labels unrepaired, all 28 of
which were labels for which it had already computed a valid unique
relocation. The opposite invention is equally reachable and worse: a
pass reading the silence as "relocate everything" rewrites the 17
records and leaves no trace that it did. Both readings are wrong on one
of the two shapes, which is why the split is stated here rather than
re-derived per pass.

**Resolving the cite.** Cards write paths as they read in prose, so
accept the bare basename (`engine.py:N` for `goc/engine.py:N`) and
prefer a match outside vendored/mirror trees when several exist.

**A range is one cite, not two.** `file.py:120-140` asserts a BLOCK, and
the endpoints are only how the block is addressed — so a repair that
leaves them no longer bounding a block has destroyed the cite rather
than moved it, and is strictly worse than the drifted cite it replaced.
A drifted `file.py:120` still points somewhere a reader can orient from.
Map each endpoint by the recipe below, then check the PAIR before
writing it: emit the rewrite only when it is ordered (`start <= end`)
and the new span still fits a block. An unordered pair, or a span no
block could have (this deck's guard refuses more than 500 lines), is a
DECLINE — reported like every other decline, never written.

Endpoints usually move together, because code inserted above a block
shifts both of its edges by the same amount, and that is exactly what
makes the failure silent when it stops. A pass that relocates one
endpoint and leaves the other — its anchor text happened to still sit
at its own line, so the endpoint read as `current` — emits a pair whose
two numbers each anchor cleanly in isolation. The NEXT pass therefore
verdicts the wreck `current` too, and no decline is ever reported for
it. Measured on this deck: three anchored passes left twelve such cites
across eight open cards, seven of them `human_gate: decision`, none of
them reported by any pass.

**Do not re-map a range that ARRIVES incoherent.** `start > end`, or a
span no block could have, is damage an earlier pass wrote, not drift.
Its endpoints anchor to whatever they were last mistakenly moved onto,
so running the recipe over them relocates that unrelated text and
launders one corrupt cite into a differently corrupt one — the pass
reports a repair and the cite still names nothing. Report it under the
same decline reason and leave the numbers alone; only the card's own
prose says which block it meant.

**Getting the anchor.** A cite means what it meant when its number was
last AUTHORED, so the anchor commit is the one that wrote the number —
the filing commit for a cite no pass has touched, the repair commit for
one an earlier pass rewrote. Find it by walking the card's own history:
list `git log --follow --format=%H -- <deck>/<card>/README.md` oldest to
newest (check the legacy `deck/` path too), read the README at each
commit, and take the newest commit at which the cite token turns from
absent to present. Presence is SET MEMBERSHIP, not a substring search:
extract that version's cite tokens with the same pattern the pass uses
to find cites in the card, and ask whether this token is one of them.
Read the cited file at that commit — `git show <commit>:<path>` — and
take the cited line's text. That text is what the card meant; the number
is only its address at the time.

**Why the presence test has to be token-exact.** A plain text search
reads `path:N` as present inside `path:N-M`, so a single-line cite that
shares its number with a range the same card carries never turns from
absent to present at the commit that actually wrote it — it reads as
present from whenever the range arrived, and inherits the range's older
anchor. Calling the token "exact" is not enough and is why this held for
a month: the word modified the token, while the test around it was still
`in`. Measured on this deck 2026-09-14, two cites anchored this way,
both onto text one line above the function their card names, and both
were proposed for a rewrite onto that wrong line.

**One token at two occurrences — DECLINE.** The walk identifies a cite
by its TOKEN, and a token is not unique inside a card. Where the same
in-scope token sits at two or more occurrences, those occurrences share
one history and no walk can anchor them apart, even in principle:
token-exactness does not help, because the token genuinely WAS present
at the earlier commit, at the other occurrence. So count the occurrences
before walking, and decline the token outright when there is more than
one — a residue row, never a rewrite. The passes manufacture this shape
themselves: neighbouring cites drift by the same amount, so a pass
repairs them together and lands one on a number another already held.
Measured on this deck 2026-09-14: 63 open cards hold an in-scope token
at two or more occurrences, benign only while both occurrences still
mean the same line.

**A cite that already resolves at HEAD is not a repair candidate.**
Cheap, and worth running first: if HEAD holds at the cited line the
symbol the card's own prose names, the number is correct and no anchor
can say otherwise. That would have stopped all three false repairs this
rule was written for. It is belt-and-braces rather than the fix — it
silences the symptom for cites that happen to be right and does nothing
for one that is genuinely defunct and anchored on a neighbour's history.

**Why not the creating commit.** It is the same commit for a cite no
pass has ever rewritten, so the walk subsumes that older rule rather
than replacing it — but a repair pass rewrites the number, which is its
whole job, and from then on the creating commit resolves whatever
unrelated code sat at that offset when the card was filed. The recipe
below then finds that text elsewhere in HEAD and moves the cite onto
it, passing the uniqueness guard because the wrong anchor is genuinely
unique. Measured on this project's deck one week after its first repair
pass: of 850 open-card cites, the creating-commit anchor would have
moved 165 that were correct. Repair passes recur, so second passes are
the normal case; an anchor that is right only on a virgin deck is right
only once.

**Deciding.** Test the anchor line BEFORE comparing it. A blank, a bare
brace, or anything under roughly 12 characters matches everywhere, so
re-finding it at the cited offset is no more evidence that the cite is
current than it is evidence of where the cite should move: the verdict
is a DECLINE, reported, never `current`. Only a non-trivial anchor is
compared — anchor text ≠ the text at that line in HEAD → defunct. Then
look for the anchor text in HEAD and rewrite the number only when the
match is UNIQUE; the line is already known substantial, because the
refusal above ran first. That guard is what makes the repair safe to
apply unattended — on the pass that produced this rule it repaired 388
cites across 113 cards and declined 279 rather than guess.

**One predicate, both directions.** The non-triviality test shipped on
the relocate step alone, and the asymmetry is the whole defect: a line
too weak to move a cite by one line was strong enough to certify it for
another pass. Nothing surfaced that, because a `current` verdict is
silence — no decline line, no residue row — and a blank anchor cannot
decay, so it freezes an author's original typo into a permanent
`current`. Measured on this deck 2026-09-14: 46 of 413 `current`
verdicts (11%), over 28 open cards, rested on such a line. One had
passed three consecutive anchored passes while missing the function its
card named by 910 lines, having never named it correctly at all.

**A definition is identified by its name, not by its parameter list.**
Exact full-line equality makes the anchor LINE the unit of identity. That
is right for a statement inside a body, where the line is all the card
ever meant, and wrong for a `def` or `class` line, where the card means
the DEFINITION and the line is only how it announced itself on the day
the cite was written. Append a keyword-only parameter, widen a return
annotation, reflow the argument list across two lines — the function is
still there, still uniquely named, still one grep away, and the exact
test reports `anchor text absent` and declines. It declines again on the
next pass, and on every pass after, because nothing about the situation
changes. So when the anchor is a definition line and its exact text is
absent from HEAD, retry on a unique `def <name>(` / `class <name>(`
match. Only the identity claim moves, from "this line" to "this
definition"; the refusal to guess does not, and two constraints hold it
there:

- **Two or more definitions of that name is an ambiguous match —
  DECLINE.** An overload in a mirror tree, a method and a module-level
  function sharing a name: the card's prose disambiguates, the matcher
  cannot. Nearest-match is no more available to this rule than to the
  exact one.
- **The pair check still decides.** The name rule feeds the endpoint
  mapper and nothing else. A range whose start relocates by name while
  its end sits unmoved is the same wreck the pair guard above refuses,
  and it is refused there.

Measured on this deck 2026-09-14: 12 declines over 9 open cards were
def/class anchors a unique-name match locates, and ONE refactor produced
most of them — five install-time writers gained `*, probe: bool = False`
in a single commit, so every card citing any of them lost its anchor at
once. Signature drift arrives in families, so this class does not
trickle in, it lands in batches, which is what makes a per-pass judgement
call the wrong place for it.

The relaxation stops at the definition line. Whitespace normalization and
similarity ratios would have reached 16 further cites that same round and
rest on a tuned threshold rather than on an identity claim; a wrong
relocation is worse than a decline, and a threshold cannot say which it
produced. Non-Python definition forms — TypeScript `function` and
`const … =>`, shell functions — stay out until a measurement asks for
them.

**The residue is output, not silence.** The declines split six ways
and each is reported for a human read:

| Decline | What it usually means |
|---|---|
| ambiguous occurrence (>1 in the card) | the same cite token sits at two or more in-scope occurrences of one card, so the history walk cannot tell which occurrence it is anchoring; only the card's prose says what each one meant |
| trivial anchor, verdict undecidable | the anchor line is a blank, a bare brace, or under ~12 characters, so matching it at the cited offset is no evidence the cite is current and finding it elsewhere is no evidence of where it went; a reader must re-derive the address from the card's prose |
| ambiguous match (>1 hit in HEAD) | boilerplate, a repeated idiom, or a definition name HEAD holds more than once — an overload in a mirror tree, a method beside a module-level function; the card's surrounding text disambiguates, the matcher cannot |
| anchor text absent | neither the anchor text nor — for a definition line — a unique `def`/`class` of that name is anywhere in HEAD; the code may have been refactored away, but it may equally have been renamed or split, so re-read the card before reading the decline as evidence the defect is gone, and close it per the core skill only if a refactor did fix it |
| incoherent range pair | the two endpoints no longer bound a block — one half-moved by this pass, or a range that arrived already broken; a reader must re-derive the block from the card's prose |
| retired occurrence (re-run before the commit) | a second-round proposal on a cite this pass itself wrote, made while the rewrite was still uncommitted: the walk cannot see the rewrite, so it anchored on the last commit that carried the number — a different cite's, before an earlier pass moved it. The cite is not defunct and the proposal is not a repair; apply nothing that round proposed, commit, and re-run |

A pass that printed only the cites it could auto-repair would report a
shrinking problem while the unmappable majority rotted unseen — the
same fail-open shape as the bounds test it replaced. Expect the first
pass after a widened decline to report MORE residue than the one before
it, and read that as accounting caught up rather than as a regression:
moving the trivial-anchor test ahead of the comparison reclassified 46
cites on this deck from a silent `current` into the table above, none of
which the pass before it had been entitled to certify.

**Close the step by committing, then re-running it.** Commit the
rewrites, then run the decision phase again over the cards just written
and assert it proposes ZERO further repairs. A correctly repaired deck
is a fixed point, so any second-round proposal is the pass repairing
its own output — and the per-cite rules cannot catch that, because each
such proposal is individually well-formed: a real anchor, a unique
match, a confident rewrite onto the wrong line. The colliding-anchor
class above was found by exactly this re-run and by nothing else; a
pass that had followed the recipe as written would have reported three
successful repairs and left no trace of the three correct cites it
moved. Treat a non-empty second round as a defect in the recipe to be
filed, not as more work to apply.

**The commit comes first because the walk reads history.** Its input is
`git log`, so a rewrite still uncommitted in the working tree is
invisible to it. For a cite the pass has just written, the newest
absent-to-present turn is then one from BEFORE this pass — on a
renumbering pass, routinely a RETIRED occurrence: the number the card
carried for a different cite until an earlier pass moved that cite
elsewhere. The walk anchors the fresh cite on the retired occurrence's
text, finds that text uniquely in HEAD, and proposes moving a correct
cite onto it. Neither occurrence guard above sees it — presence is set
membership already, and the token occurs once in the card — because
the colliding occurrence is in the card's PAST, where no count of
current occurrences reaches. Measured on this deck 2026-09-21: one pass
re-ran over its identical 269 repairs twice, and proposed 3 further
repairs before its commit, all three false, and 0 after it. So the
re-run is only valid once the rewrites are committed, which a local
commit satisfies; pushing can wait for the verdict. A pass that cannot
commit yet — another agent holds the shared index — commits the
rewrites in a throwaway worktree and re-runs there, or holds the step
open until its own commit lands. It never re-runs over the working
tree, and it applies nothing such a run proposes (the retired-occurrence
row above). Reading the working-tree README as the walk's newest
version would make the re-run valid at any point, but it would anchor
cites on edits nobody has committed and redefine the walk every other
rule here is built on, where the ordering costs one sentence.

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
per-DoD-item issues. Currently a stub. The regex-only mode is
sufficient as the always-on baseline; the batched LLM pass is a
nice-to-have, not load-bearing.

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
