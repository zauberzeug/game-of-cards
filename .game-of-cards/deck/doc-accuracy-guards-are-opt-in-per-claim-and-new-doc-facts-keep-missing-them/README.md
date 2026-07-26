---
title: doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
summary: "tests/test_guidance_accuracy.py now holds six guard classes, each added reactively after a reader caught a doc claim that had already rotted. Nothing sweeps the doc surfaces for UNGUARDED restatements of tree-derived facts, so every next stale claim is found by a human or an audit pass rather than by CI. Sixth instance of the shape; the fix path needs a scope decision."
status: open
stage: null
contribution: medium
created: "2026-07-26T07:47:11Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [meta-fix, documentation, infra]
definition_of_done: |
  - [ ] (replace with real criteria once the decision below is recorded)
---

# Doc-accuracy guarding is opt-in per claim, so each new stale doc fact is found by a human

`tests/test_guidance_accuracy.py` is this repo's answer to doc drift: a test that
pins a prose claim to the code or tree it describes. The mechanism works — but it
is applied **one claim at a time, always after the fact**. Six guard classes now
live in that file, and every one was written in response to an already-rotted
claim someone happened to notice. Nothing looks for the *unguarded* claims.

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

Seven instances across three months, each its own file → claim → fix → guard cycle.
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
different axis, and one no existing card covers.
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
