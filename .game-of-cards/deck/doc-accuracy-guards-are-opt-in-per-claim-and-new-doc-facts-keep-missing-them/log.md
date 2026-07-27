
## 2026-07-26T08:25:00Z — Seventh instance connected (audit-deck round)

An audit pass on the same day this card was filed surfaced instance seven and
connected it here rather than filing a duplicate root:
[ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card](../ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card/)
(open, `contribution: low`, `human_gate: session`). Two of the shapes this card
enumerates, in one eleven-line comment block: a bare count in prose ("All 11
skill templates" — `ls -1d goc/templates/skills/*/ | wc -l` returns 18) and a
forward-looking promise naming `goc-install-command-scaffolds-repo`, a card title
that has never existed.

Body amended in place (dashboard rule): instance table extended, count corrected
six → seven, and a paragraph added on what the new instance changes.

**The substantive addition is a surface-coverage gap, not just a tally.** Option A
enumerates the doc surfaces to sweep — `AGENTS.md`, `goc.md`, `README.md`,
`ABOUT.md`, `CONTRIBUTING.md`, `DECK_LOCATION.md`, `PERSONAS.md`, `site/`, the
plugin READMEs, the skill bodies. Instance seven lives in a
`.github/workflows/*.yml` header comment, which is on none of them. Whichever
option is adopted, the surface definition needs to cover tree-restating prose
wherever it lives — workflow headers, module docstrings, config comments — not
only the `.md` set. No decision is recorded here; that remains the human's pick.

## 2026-07-26T08:22:29Z — Eighth instance connected (pull-card round)

A pull-card session closed
[openclaw-verb-mirror-comment-names-click-in-an-argparse-cli](../openclaw-verb-mirror-comment-names-click-in-an-argparse-cli/)
and connected it here rather than filing a duplicate root. Same cycle as the
other seven: a claim that restated tree state, unguarded, caught only after it
had rotted, fixed with a bespoke guard class
(`CliFrameworkPointerAccuracyTest`) in `tests/test_guidance_accuracy.py`.

Body amended in place (dashboard rule): instance table extended, counts moved
seven → eight instances and six → seven guard classes, and a paragraph added on
what the new instance changes.

**The substantive addition is that per-surface guarding is the wrong unit.** The
eighth instance's stale claim was not a new falsehood — it was *the same
falsehood the second instance already guarded*: that goc's CLI is built with
click. `AgentsArchitectureAccuracyTest` pinned that in `AGENTS.md` and
`goc/cli.py` on 2026-05-27; the identical assertion sat unguarded in
`openclaw-plugin/index.ts` for two more months, and the guard written today
(like every predecessor) again covers exactly one file. This sharpens Option B:
its cheap first cut may be "every fact a guard already pins, pin everywhere it
is asserted" — grep the claim text across all tracked surfaces at guard-writing
time, rather than inferring a general lint shape. It also extends the
surface-class list instance seven started: after `.github/workflows/` headers,
now TypeScript source comments.

No decision is recorded here; that remains the human's pick.

## 2026-07-27 — Deck hygiene: instance roster wired as edges

`Skill(refine-deck)`'s orphaned-dependency sub-check 2 surfaced this card as a
`meta-fix` umbrella carrying zero relationship edges while its body declares an
eight-card instance roster. The `meta-fix` predicate fires (literal in title,
summary and body), so the disposition is "wire the family", not "strip the
tag".

All eight roster entries are now `advanced_by` edges on this card (symmetric
`advances` written on each instance by `goc advance`), matching the wired shape
of the sibling umbrella
[unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes](../unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes/),
which carries six closed instances plus one open one on the same field. Seven
of the eight here are closed; the roster is deck-as-record evidence that the
shape recurs, and closed endpoints are first-class per the deck's
scheduler-vs-record rule.

The one open endpoint,
[ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card](../ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card/),
now shows as a live dependency (⏳ is advisory, not a pull block). No claim in
the body changed and no decision was recorded — the scope question in
`## Decision required` is still the human's pick.

## 2026-07-27T04:47:12Z — Ninth instance connected: prose restating prose

Wired [story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it](../story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it/)
in as `advanced_by` and recorded it in the instance table. Connected rather than
filed as a new root: same root cause (opt-in-per-claim guarding, nothing sweeps
for unguarded restatements), so per `Skill(create-card)` Step 2 it is supporting
evidence on this card, not a second umbrella.

What it adds beyond a tally:

- **A third axis.** The body previously drew the line at *prose restating tree
  state*, explicitly excluding the code-duplicates-code family. This instance is
  prose restating *prose* — `Skill(refine-deck)` re-specifying a rule
  `Skill(card-schema)` owns. Same root cause, but Option A's derive-from-tree
  technique cannot reach it: there is no tree to derive from, only two paragraphs
  whose meanings must agree.
- **Rot introduced by the repair.** The restatement went stale on 2026-07-08,
  when the `meta-fix` predicate card widened the rule at its source and left the
  copy untouched. Nineteen days unguarded. The eighth instance showed a guarded
  claim with an unguarded copy elsewhere; this one shows the fix itself
  manufacturing the divergence — a strictly stronger argument for Option B's
  claim-keyed guarding.
- **The operative copy was the stale one.** refine-deck is the skill that
  *executes* the tag rule on every hygiene pass, so the wrong copy outranked the
  right one in practice: an agent following it would have stripped `story` from
  67 of 102 cards.

No guard was added, and the table row says so. The repair was structural — stop
restating, point at the owner — which is the only general answer available for
this axis. Recording it as an empty guard cell rather than a silent omission so
the eventual scope decision sees that "add a guard" was not on the menu here.
