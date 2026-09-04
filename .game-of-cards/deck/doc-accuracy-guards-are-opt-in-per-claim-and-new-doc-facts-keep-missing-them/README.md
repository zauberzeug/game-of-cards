---
title: doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
summary: "tests/test_guidance_accuracy.py now holds nine guard classes, plus two more in their own files, each added reactively after a reader caught a doc claim that had already rotted. Nothing sweeps the doc surfaces for UNGUARDED restatements of tree-derived facts, so every next stale claim is found by a human or an audit pass rather than by CI. Fourteenth instance of the shape; the fix path needs a scope decision that must say which surfaces count — the ninth added prose restating *prose*, where a derive-from-tree guard is structurally impossible, the eleventh added machine-readable manifests, where it is not just possible but cheap, and the twelfth added the public website plus a claim whose ground truth is an external registry rather than this tree. The thirteenth widens nothing and is the sharpest for it: three false clauses in an *already-guarded* AGENTS.md sentence, all three written by an earlier instance's own repair, so neither a per-surface sweep nor per-claim pinning would have caught them. The fourteenth adds the first surface whose rot is executed rather than read — a skill body specifying a procedure an agent follows literally, which moved 165 correct citations onto unrelated code before it was caught — and it is guardable only by running the instruction against a fixture, which is neither option as written."
status: open
stage: null
contribution: medium
created: "2026-07-26T07:47:11Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - generated-agents-guidance-overstates-done-commit
  - agents-md-architecture-section-cites-removed-click-and-omits-verbs
  - deck-skill-board-legend-misstates-pullability-of-dependency-flagged-cards
  - sort-default-docstring-cites-wrong-engine-line-for-value-walk-dangling-edge-drop
  - create-card-and-deck-skills-claim-goc-new-scaffolds-a-reproduce-py-stub
  - cli-reference-plugin-sections-describe-a-payload-goc-no-longer-ships
  - ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card
  - openclaw-verb-mirror-comment-names-click-in-an-argparse-cli
  - story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it
  - card-schema-reference-links-to-a-deck-card-no-consumer-repo-has
  - openclaw-plugin-manifest-config-options-do-not-behave-as-documented
  - llms-txt-still-presents-the-clawhub-install-as-unpublished
  - five-of-six-content-stubs-promise-inlining-no-shipped-skill-performs
  - meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card
  - agents-md-cli-bullet-describes-parser-wiring-the-entry-point-never-does
  - second-citation-repair-pass-moves-correct-cites-onto-unrelated-code
  - cli-reference-steers-authors-onto-deprecated-blocked-status-not-the-wait-overlay
tags: [meta-fix, documentation, infra]
definition_of_done: |
  - [ ] (replace with real criteria once the decision below is recorded)
---

# Doc-accuracy guarding is opt-in per claim, so each new stale doc fact is found by a human

`tests/test_guidance_accuracy.py` is this repo's answer to doc drift: a test that
pins a prose claim to the code or tree it describes. The mechanism works — but it
is applied **one claim at a time, always after the fact**. Nine guard classes now
live in that file (two further guards got their own files), and every one was written in
response to an already-rotted claim someone happened to notice. Nothing looks for
the *unguarded* claims.

## The instance list

| Guard class | Filed by | Closed |
|---|---|---|
| `GuidanceAccuracyTest` | [generated-agents-guidance-overstates-done-commit](../generated-agents-guidance-overstates-done-commit/) | 2026-05-05 |
| `AgentsArchitectureAccuracyTest` | [agents-md-architecture-section-cites-removed-click-and-omits-verbs](../agents-md-architecture-section-cites-removed-click-and-omits-verbs/) | 2026-05-27 |
| `DeckBoardLegendAccuracyTest` | [deck-skill-board-legend-misstates-pullability-of-dependency-flagged-cards](../deck-skill-board-legend-misstates-pullability-of-dependency-flagged-cards/) | 2026-06-18 |
| `DocstringCitationAccuracyTest` | [sort-default-docstring-cites-wrong-engine-line-for-value-walk-dangling-edge-drop](../sort-default-docstring-cites-wrong-engine-line-for-value-walk-dangling-edge-drop/) | 2026-06-24 |
| `CreateCardScaffoldClaimAccuracyTest` | [create-card-and-deck-skills-claim-goc-new-scaffolds-a-reproduce-py-stub](../create-card-and-deck-skills-claim-goc-new-scaffolds-a-reproduce-py-stub/) | 2026-06-25 |
| `GocMdPluginReferenceAccuracyTest` | [cli-reference-plugin-sections-describe-a-payload-goc-no-longer-ships](../cli-reference-plugin-sections-describe-a-payload-goc-no-longer-ships/) | 2026-07-26 |
| *(none yet — open)* | [ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card](../ci-workflow-header-miscounts-skill-templates-and-cites-a-nonexistent-card/) | — |
| `CliFrameworkPointerAccuracyTest` | [openclaw-verb-mirror-comment-names-click-in-an-argparse-cli](../openclaw-verb-mirror-comment-names-click-in-an-argparse-cli/) | 2026-07-26 |
| *(none — not guardable by the technique; see below)* | [story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it](../story-tag-predicate-fails-on-two-thirds-of-the-cards-carrying-it/) | 2026-07-27 |
| `test_no_shipped_skill_body_links_into_a_deck` (own file, `tests/test_skill_template_deck_links.py`) | [card-schema-reference-links-to-a-deck-card-no-consumer-repo-has](../card-schema-reference-links-to-a-deck-card-no-consumer-repo-has/) | 2026-07-29 |
| *(none yet — open)* | [openclaw-plugin-manifest-config-options-do-not-behave-as-documented](../openclaw-plugin-manifest-config-options-do-not-behave-as-documented/) | — |
| `LlmsTxtInstallChannelTest` (own file, `tests/test_llms_txt_install_channels.py`) | [llms-txt-still-presents-the-clawhub-install-as-unpublished](../llms-txt-still-presents-the-clawhub-install-as-unpublished/) | 2026-08-01 |
| *(no new class — four tests added to the existing `AgentsArchitectureAccuracyTest`)* | [agents-md-cli-bullet-describes-parser-wiring-the-entry-point-never-does](../agents-md-cli-bullet-describes-parser-wiring-the-entry-point-never-does/) | 2026-08-15 |
| `DocumentedAnchorRuleTest` + `SecondRepairPassTest` (own file, `tests/test_refine_deck_citation_anchor.py`) | [second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/) | 2026-08-17 |

Fourteen instances across four months, each its own file → claim → fix → guard cycle.
`Skill(audit-deck)`'s sibling-sweep rule sets the threshold at four: "If the sweep
would produce a 4th instance of an already-catalogued family, file the
architectural meta-fix instead." This card is that filing.

The seventh arrived the same day this card was filed, before any option below was
adopted — and it carries a finding that changes Option A's scope. Its two stale
claims ("All 11 skill templates" when there are 18; a shipped capability framed
as pending behind a card title that never existed) live in a **`.github/workflows/`
header comment**, a surface class absent from Option A's sweep list. Doc-shaped
prose is not confined to `.md` files: workflow headers, `Makefile`s and module
docstrings all restate tree state, and a sweep or lint scoped to the documentation
set would have missed this one.

The eighth widens the surface class once more — a **TypeScript source comment**
(`openclaw-plugin/index.ts`) — and adds the sharpest evidence yet that per-surface
guarding is the wrong unit. Its stale claim was *the same false claim* the second
instance already guarded: that goc's CLI is built with click. `AgentsArchitectureAccuracyTest`
pinned that down in `AGENTS.md` on 2026-05-27 and in `goc/cli.py`; the identical
assertion sat unguarded in the OpenClaw plugin entry for two more months. A guard
keyed to *the claim* rather than *the file* would have caught it the day the first
one was written. That is a datum for Option B: the cheap version of a shape-level
lint may be "every fact a guard already pins, pin everywhere it is asserted" —
grep the claim text across all tracked surfaces, not just the one where it was
caught.

The ninth is the first where the restated fact is **not tree state at all**, and
it is the one that bounds Option A. `Skill(refine-deck)` § "Tags without firing
predicates" restated the tag-application rule owned by `Skill(card-schema)`
("every applied tag must fire on title / H1 / first ~2500 chars of body"). On
2026-07-08 [meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag](../meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag/)
widened that rule at its source — the window became a *default* a row may
override — and the restatement was never touched. It sat wrong for nineteen days
until an audit pass caught it, and because refine-deck is the skill that
*executes* the rule on every hygiene sweep, the stale copy was the operative one:
an agent following it would have stripped `story` from 67 cards regardless of
what card-schema said.

Two things follow for the scope decision.

First, this instance is the strongest case yet for Option B, and it is stronger
than the eighth: there, one assertion was guarded and a copy elsewhere rotted;
here, **the act of fixing the first assertion is what created the stale second
one**. A claim-keyed guard is the only shape that catches that class, because the
rot is introduced by the repair.

Second, Option A cannot reach it. The good guards work by *deriving* the expected
value from the tree — count the directories, read the parser. Prose restating
prose has no tree to derive from; checking it means comparing the *meaning* of two
paragraphs, and no lint does that. So the fix for this surface class is
structural rather than test-shaped: **don't restate a rule another document owns —
point at it.** The repair took that route (refine-deck now says "a tag must
satisfy its own row's predicate" and defers, instead of re-specifying the
surface), and no guard was added, which is why its row in the table above is
empty. Any option adopted here should say explicitly whether prose-restating-prose
is in scope, because "add a guard" is not an available answer for it.

The eleventh widens the surface class a fourth time, to a **machine-readable
manifest**. [openclaw-plugin-manifest-config-options-do-not-behave-as-documented](../openclaw-plugin-manifest-config-options-do-not-behave-as-documented/)
found both keys in `openclaw-plugin/openclaw.plugin.json`'s `configSchema`
misdescribing the code: `deck_path` declares a settable override that no consumer
reads, and `pattern_generalization_check` declares `"default": true` against a
runtime gate, a source comment, and a README that all say off-by-default. This is
the same rot as a stale prose claim, but the surface is a JSON declaration rather
than a sentence — so a sweep scoped to prose (`.md`, comments, docstrings, workflow
headers) misses it entirely, and the scope decision should name manifests
explicitly.

It is also the cheapest instance yet for Option A, and that is the useful datum:
both claims are derivable. "Every key in a `configSchema` is referenced by at
least one consumer" and "every declared `default` equals the runtime gate's
default" are both tree-derived predicates of exactly the self-maintaining kind
described below — no restated constant, nothing to go stale. Where the ninth
instance bounded Option A from above (prose restating prose is unreachable), this
one shows the technique reaching *further* than the surfaces catalogued so far:
declarations in structured config are guardable, and nobody has looked there.

The twelfth widens the surface class a fifth time, to the **public website**, and
is the first instance whose ground truth lives outside this tree.
[llms-txt-still-presents-the-clawhub-install-as-unpublished](../llms-txt-still-presents-the-clawhub-install-as-unpublished/)
found `site/llms.txt` — the file LLMs ingest to learn how to recommend GoC — still
saying the OpenClaw install works "Once the plugin is published" and pointing
readers at a from-source build "Until publish lands", ten releases after ClawHub
began serving the package. It is the second confirmed member of the
**forward-looking promise** shape this card's taxonomy already names, and the
first where the promise had an externally observable fulfilment date it outlived
by eleven weeks.

Two datums for the scope decision.

First, it bounds Option A from a direction the ninth did not. Prose restating
prose is unreachable because there is no tree to derive from; here there *is* a
fact, but it is not in the tree — "is this package published?" is answerable only
by an external registry, so a derive-from-tree guard structurally cannot pin it,
and a guard that could would make CI depend on a third-party API.

Second, the repair shows the way around that, and it generalizes: guard the
**agreement among restatements** instead of the fact. Four in-repo surfaces
(`README.md`, `ABOUT.md`, `goc.md`, `site/index.html`) already asserted the
install was live; `tests/test_llms_txt_install_channels.py` pins llms.txt against
them, which is fully tree-derived and would have failed the day they diverged.
Where Option B says "pin every fact a guard already pins, everywhere it is
asserted", this adds: **when a fact has no in-tree source at all, the fact that N
surfaces restate it is itself the derivable invariant.** That reaches a class
neither option currently covers, and it costs one consistency test per claim
family rather than one guard per claim.

The thirteenth widens nothing — and that is what makes it the sharpest instance
in the table. Its surface (`AGENTS.md`'s `## Code architecture`) and its guard
class (`AgentsArchitectureAccuracyTest`) are the *second* instance's, already
catalogued here since 2026-05-27.
[agents-md-cli-bullet-describes-parser-wiring-the-entry-point-never-does](../agents-md-cli-bullet-describes-parser-wiring-the-entry-point-never-does/)
found all three clauses of the `goc/cli.py` bullet false at once: the parser
build, the `install`/`upgrade` registration and the `--version` ownership were
each attributed to a file that does none of them. Every one of those clauses was
written *by the second instance's own repair*, in the same sentence it was
fixing, and the guard it added that day — `test_cli_bullet_does_not_mention_click`
— went green on the rewritten text without ever looking at what the rewrite now
asserted.

This is the ninth instance's lesson ("the act of fixing the first assertion is
what created the stale second one") recurring inside a *guarded* surface, and it
narrows the unit of coverage by one more level. The eighth showed a guard keyed
to a file misses the same claim asserted elsewhere; this shows a guard keyed to a
*claim* misses the other claims in the sentence it guards. Neither Option A's
sweep (the surface has a guard) nor Option B's claim-keyed pinning (the three new
claims were novel, pinned nowhere) would have caught it.

The datum for the scope decision is therefore about *when* to sweep, not where:
the highest-yield moment to look for unguarded restatements is the commit that
edits a documentation sentence, because a repair rewrites more prose than it was
aimed at. Whatever option is adopted, a guarded surface should not be treated as
a covered one — the repair took the local route (four derived tests replacing the
one `click` regex, three of them checked against the stale text to prove they
fire), but the general shape is a diff-scoped check: **when a commit touches a
guarded doc surface, every factual clause in the changed lines needs a guard, not
just the one that motivated the edit.**

The fourteenth adds a surface class the taxonomy above has no row for: prose
that is **executed rather than read**. `Skill(refine-deck)`'s citation-repair
recipe told a hygiene pass to anchor each cite at the card's creating commit;
[second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/)
measured that instruction moving 165 correct cites of 850 onto unrelated code
on the second pass. Every other instance in the table is a claim a reader may
be misled by; this one is an instruction an agent runs, so its rot mutates the
tree instead of merely describing it wrongly. The blast radius argues for
ranking, not for a new option: instruction-shaped prose ships in all five
plugin payloads and is followed literally.

Three datums for the scope decision. First, it recurs the thirteenth's lesson
one level deeper — the false claim ("anchoring at the creating commit is what
makes the check independent of any earlier repair pass") was itself written by
the *previous* instance's repair of that same recipe
([refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file](../refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file/),
closed 2026-08-10), so a repaired surface is no more covered than a guarded
one. Second, it is guardable, but by neither option as written: the rule is not
derivable from the tree (Option A) and not a restatement to pin against a twin
(Option B) — the guard parses the rule out of the skill body and *runs* it
against a synthetic fixture, which is a third technique the decision should
name. Third, its rot needed two hygiene passes to become visible at all, which
puts a lower bound on how long an instruction-shaped defect can sit green: the
sweep interval of whatever process executes it.

## What's structurally wrong

The guard technique is sound and, at its best, self-maintaining: the good guards
**derive** the expected value from the tree rather than restating it.
`test_all_engine_verbs_listed_in_architecture_section` reads the verb set off the
live argparse parser; `test_claude_skill_count_matches_payload` counts
`claude-plugin/skills/` directories. A guard written that way cannot go stale — it
fails the build the moment tree and prose disagree.

But coverage is **opt-in per claim**. A doc surface can restate any number of
tree-derived facts and carry zero guards, and nothing reports that. The failure
mode is not "a guard broke"; it is "no guard was ever written, and the claim
quietly stopped being true." The most recent instance is the clearest
illustration: `goc.md`'s plugin sections carried **seven** simultaneously-false
claims, the oldest untrue since 2026-05-07, on a file linked from `README.md`,
`ABOUT.md`, `CONTRIBUTING.md` and the website. CI was green the whole time.

The claim shapes that rot are enumerable, which is what makes this tractable:

- **Bare counts in prose** — "11 GoC skills", "13 GoC skills", "Three lifecycle
  hooks", "16 deck skills". Each is a cardinality the tree already knows.
- **Enumerations of a set the tree defines** — hook event lists, verb lists,
  skill lists, template→destination tables.
- **Architecture assertions** — "are symlinks", "shells to the `goc` CLI",
  "requires X first". Each is checkable against a file mode, a wrapper script, or
  a manifest.
- **Forward-looking promises** — "A future release will fix … to use
  `${CLAUDE_SKILL_DIR}`". These have no expiry and no owner; that string appeared
  nowhere in the tree, and the promise outlived the actual fix by months.
- **`file.py:NNN` citations** in prose and docstrings — already the subject of
  `DocstringCitationAccuracyTest`, which fixed one instance by banning the shape.

## Why it matters

Doc drift here is not cosmetic, for two reasons specific to GoC:

1. **The docs are the agent's instructions.** `AGENTS.md` and the skill bodies are
   read cold by autonomous agents every session. A stale claim is not a misleading
   paragraph a human skims past — it is a wrong premise an agent acts on. The
   symlink claim in the last instance told contributors that editing
   `claude-plugin/skills/` edits the template; acting on it loses the edit
   silently at the next `sync-plugin-assets` run.
2. **The repo dogfoods itself, so the surface is doubled.** Every claim about the
   payload layout has a consumer copy and a template copy, and `goc.md` describes
   both. The surfaces needing guards outnumber the ones anybody remembers to check.

Same shape as
[draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it](../draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it/)
and
[query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it](../query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it/)
— an opt-in guard mechanism where the opt-in step is what keeps getting skipped.
Whatever mechanism those two land on may generalize here; they should be decided
together, or at least in a consistent direction.

Adjacent but distinct: the "X reimplements Y and keeps drifting" family
(e.g. [yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/))
is *code* duplicating *code*. This card is *prose* restating *tree state* — a
different axis, and one no existing card covers. The ninth instance adds a third
axis to this card's scope: *prose* restating *prose*, where the owning document
is itself guidance rather than code. Same root cause (no guard binds the copy to
its source), but the only two answers that work on it are "point instead of
restate" and a claim-keyed grep — not a derive-from-tree test.
[derive-openclaw-manifest-skills-array-from-ported-skill-dirs](../derive-openclaw-manifest-skills-array-from-ported-skill-dirs/)
is the single-surface version of the same instinct (a manifest hardcoding a list
the tree knows); it should probably fold into whatever this card decides.

## Decision required

The diagnosis is not in question — six instances document it. What needs a human
pick is **how much machinery to build**. The options trade real coverage against
real maintenance cost, and are not mutually exclusive; the decision is which to
adopt and in what order.

**Option A — sweep once, guard what's found, accept reactive from then on.**
One pass over `AGENTS.md`, `goc.md`, `README.md`, `ABOUT.md`, `CONTRIBUTING.md`,
`DECK_LOCATION.md`, `PERSONAS.md`, `site/`, the three plugin `README.md`s and the
skill bodies; add derive-from-tree guards for every count, enumeration and
architecture assertion found. Bounded and immediately valuable, but the class
stays opt-in — instance seven arrives eventually.

**Option B — a shape-level lint: no bare cardinalities in prose docs.**
A test that flags `\*\*\d+ (GoC )?skills\*\*`-style patterns in tracked docs
unless the number is covered by a derive-from-tree assertion. Catches the whole
class rather than known members. Risk: defining "covered" is fiddly, and false
positives on legitimate prose numbers ("Python 3.10+", "the 0.0.x line") need an
opt-out that itself becomes a maintenance surface.

**Option C — generate the volatile bullets instead of guarding them.**
Templating: `goc.md` gets placeholders that the Pages build (or a pre-commit step)
fills from the tree, the way `scripts/release_rewrite_versions.py` already
rewrites version literals. Removes the drift class outright rather than detecting
it. Cost: `goc.md` stops being a plain readable file in the repo, which cuts
against it being the human-facing CLI reference — and the release-rewrite
precedent shows how much anchoring care surgical rewrites need.

**Option D — a promise-expiry guard only, and document the rest as convention.**
Narrow: ban forward-looking "a future release will…" claims unless they cite a
card slug, so the promise has an owner and shows up in the deck. Cheapest, and it
targets the worst subclass (an unowned promise never expires), but leaves counts
and architecture assertions reactive.

Factors a human should weigh: whether `goc.md` staying a plain file is worth more
than eliminating the drift class (rules Option C in or out); whether this should
move in step with the two sibling `opt-in-per-X` cards; and whether Option B's
guard-maintenance cost is acceptable for a repo whose docs change on most
releases.

Once recorded, replace the DoD with criteria matching the chosen option.
