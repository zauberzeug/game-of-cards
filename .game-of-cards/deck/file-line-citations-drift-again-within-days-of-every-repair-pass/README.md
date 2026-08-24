---
title: file-line-citations-drift-again-within-days-of-every-repair-pass
summary: "Cards address code by bare line number, and a bare line number does not survive ordinary growth. Seven days after the 2026-08-10 hygiene pass repaired 329 citations, 227 of them (69%) were wrong again — goc/engine.py grew 6731 to 6979 lines and carried 181 of the failures, so repair is permanent recurring work and between passes a reader cannot tell a good cite from a rotted one. A census of the deck's 729 distinct cites now prices the three fix options: 84.4% point into Python and only 8.9% would need a resolver that does not exist, so symbol-relative addressing is cheaper than this card claimed, but it collapses 22 separately cited lines into one 266-line function; 85% of cites could take a self-anchoring text straight from HEAD today. Parked 2026-08-17 on which form to adopt — the pick rewrites a convention shipped to every consumer."
status: open
stage: null
contribution: medium
created: "2026-08-17T02:36:14Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — the newest bulk repair pass at least three days old has decayed no more than 25%, measured at HEAD.
  - [ ] PROCESS: a citation form is chosen from `## Decision required` and recorded in `log.md`, with the reason (the options differ in who pays: author, tooling, or reader). The choice must say what happens to the 729 cites already in the deck, not only to newly written ones.
  - [ ] MECHANICAL: `Skill(create-card)` Step 5 states the chosen form where it says a bug-class card's Location is `file:line`, so newly filed cards conform.
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/SKILL.md` § "Defunct file:line citations" reads against the chosen form — if cites become self-anchoring, the pass verifies rather than relocates, and says so.
  - [ ] TDD: a check that fails on a card citing code that does not contain the cited anchor, proving it can catch an offender rather than passing on an empty list (see `static-source-guards-never-prove-they-can-catch-an-offender`).
  - [ ] MECHANICAL: all five mirrors regenerate — `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` clean.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
worker: {who: "claude[bot]", where: main}
---

# `file:line` citations drift again within days of every repair pass

## Location

- `goc/templates/skills/create-card/SKILL.md` § Step 5 — "**Location** — `file:line` (bug-class)". This is where the convention is set.
- `goc/templates/skills/refine-deck/SKILL.md` § "Defunct file:line citations" — the recurring repair the convention makes necessary.
- 845 cite occurrences across 154 open cards in this deck are written this
  way — 729 distinct `(path, line)` pairs. See `## The corpus the choice has
  to fit`.

## What's broken

Nothing malfunctions. The convention works exactly as specified and still
fails, because a line number is a position and the thing it names is
content. Any edit above the cite moves the content and leaves the number
behind, pointing — silently, and still inside the file — at whatever slid
into that position.

The rate is the finding. This is not slow rot measured over quarters:

| Repair pass | Age | Citations it wrote that are wrong at HEAD |
|---|---|---|
| `9fa3a242` deck move | 110 days | 60 / 60 (100%) |
| `69e1e4f2` first anchored repair | 13 days | 246 / 329 (75%) |
| `f290f5f7` second anchored repair | 7 days | 195 / 273 (71%) |

**The rate reproduced.** Measured 2026-08-24, `f290f5f7` is 71% decayed at
exactly the age at which `69e1e4f2` measured 69%. Two independent passes,
seven days apart, decaying at the same rate is the finding that the original
single datapoint could not establish: ~70% at one week is the steady-state
behaviour of a bare line number in this repo, not an artefact of one unusual
week. `goc/engine.py` grew 6979 → 7093 lines and `goc/install.py` 1838 →
1866 over the interval — no refactor, no reorganization, just a week of
ordinary work on the two most-cited files in the repo.

So a citation's useful life is shorter than the interval between the passes
that maintain it. Between passes the deck is in its normal state, which is
the state where most cites are wrong. And the reader has no way to tell:
a rotted cite resolves to real code in the right file, so following it
produces confident misreading rather than a visible error.

The repair itself is not cheap, either, and most of it cannot be automated.
The 2026-08-17 pass repaired 320 cites and **declined 236** — 112 whose
anchor line is too short to match uniquely, 81 that match in more than one
place, 42 whose text no longer exists anywhere. The 2026-08-24 pass repaired
286 occurrences across 83 cards and declined a residue of the same shape and
size: 126 trivial anchors, 89 ambiguous, 44 absent, 1 ambiguous path, plus
153 range cites where one endpoint was unsafe and the recipe therefore
rewrites neither. Two passes, near-identical residue — those declines are not
a backlog that shrinks; they are the permanent residue of a scheme that has
to re-derive an address that was never stable.

## Empirical evidence

`reproduce.py` replays each bulk repair pass in the deck's history and asks
how much of its output survives at HEAD. Measuring per pass rather than
"right now" keeps the number meaningful immediately after a repair:

Re-run 2026-08-24, before that day's repair commit landed:

```
Decay of each bulk citation-repair pass, measured at HEAD:

  commit       age         decayed   subject
  f290f5f7f     7d    195/273   ( 71%)  chore(deck): hygiene pass — 2026-08-17
  69e1e4f22    13d    246/329   ( 75%)  chore(deck): hygiene pass — repair 389 drifted file:
  9fa3a2421   110d     60/60    (100%)  deck: move canonical deck from deck/ to .game-of-car

newest pass at least 3 days old: f290f5f7f, 7 days ago — 195/273 of its citations (71%) are
already wrong, budget 25%
  over that span: goc/engine.py 6979 -> 7093 lines; goc/install.py 1838 -> 1866 lines

DEFECT PRESENT: a bare line number does not survive ordinary code growth, so citation repair
is permanent recurring work and a reader cannot trust a cite between hygiene passes.
```

The 7-day column is now measured twice at two different commits (69% then
71%), which is what upgrades this from a rate observed once to a rate.

## Why it matters

A card is meant to be picked up cold. Its Location section is the first
thing a reader follows, and for most of the interval between hygiene passes
it is wrong.
That is a direct hit on the deck's read-pattern guarantee, and it is
invisible to `goc validate`, which never reads citations at all.

It also compounds a second defect. Because repair is routine, second and
third passes over the same cite are the normal case — which is the exact
condition under which the shipped repair recipe corrupts correct
citations. See
[second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/):
that card fixes the recipe, this one questions whether a recipe that has to
run this often is the right answer. Fixing the recipe is necessary either
way and should not wait on this card; solving this one would make the
recipe mostly unnecessary.

Finally it is a standing tax on every hygiene pass. Citation repair was the
largest single item in the 2026-08-17 pass by a wide margin, and it will be
the largest item in the next one, on largely the same cites.

## The corpus the choice has to fit

Every option below was priced against the deck as it stands, not against an
estimate. 190 open/active cards carry **845 cite occurrences**, which dedup
to **729 distinct `(path, line)` pairs across 154 cards**; every one resolves
to a tracked file.

| Cited surface | Cites | Share |
|---|---|---|
| `.py` | 615 | 84.4% |
| `.md` | 49 | 6.7% |
| `.ts` / `.yml` / `.json` / `.yaml` / `.sh` | 65 | 8.9% |

Two thirds of everything points into two files: `goc/engine.py` takes 450
cites and `goc/install.py` 110. That concentration is why a week of ordinary
growth in `engine.py` decays a whole repair pass, and it is also what makes
each option cheap or expensive:

- **Symbol resolution covers almost all of it.** 543 of the 615 Python cites
  (88.3%) land inside a `def` or `class`; the other 72 are module level. Of
  the 49 `.md` cites, 48 sit under a heading, so the `§ Heading` form the
  card bodies already use in prose works there today. Only the 65 cites on
  `.ts`/`.yml`/`.json`/`.yaml`/`.sh` — 8.9%, not the third this card
  previously claimed — would need a resolver that does not exist yet.
- **Symbol resolution is lossy where the cites are densest.** The 615 Python
  cites cover 417 distinct lines that collapse into 156 symbols.
  `engine.py::_build_parser` alone absorbs 22 separately cited lines across a
  266-line body; `install.py::upgrade` absorbs 13 across 169 lines. Those
  cards stop distinguishing the point they were made about.
- **Anchors are mostly free to write today.** At HEAD, 620 of the 729 cites
  (85.0%) sit on a line that is non-trivial and unique within its file, so
  its text can be lifted straight into the card. The 109-cite residue is 39
  lines repeating elsewhere in the file, 39 shorter than 12 characters, and
  31 blank. That residue is smaller than the 236 the current recipe declines,
  because a written anchor never has to be recovered from history — but it
  does not vanish.

The 85% is measured immediately after a repair pass, when cites are at their
most correct; it is an upper bound on how much of a migration is mechanical,
and it shrinks with every day the decision waits.

## Decision required

Fixing this means changing what a citation *is*, and the convention is set in
`goc/templates/skills/create-card/SKILL.md:144` — `- **Location** —
`file:line` (bug-class) or doc/section (doc-class).` — a skill shipped to
every PyPI/npm/ClawHub consumer. So the pick is not local deck hygiene: it
changes the methodology GoC prescribes to repos that have never seen this
deck, and it commits somebody to migrating 729 live cites. The three options
are all coherent and they distribute the cost differently — author, tooling,
or reader — which is a judgement about who this project is willing to charge,
not a fact the code can settle. The measurements above narrow the options but
do not choose between them.

There is a second reason not to pick this one blind. The DoD's first item
asks `reproduce.py` to exit zero, and no citation form can make a *historical*
repair pass survive; the only route to green is redefining what the script
counts as decay, which necessarily follows from the form chosen. Weakening a
defect test is a move that should carry a human's name.

**Option A — self-anchoring cites: keep the number, add the line's text.**
Write the cite as ``goc/engine.py:144`` followed by what that line says, so
the card states what it expects to find.

- *Pros*: the only option that fixes the harm this card names — a reader can
  tell a good cite from a rotted one by reading the card against the file,
  with no tooling and no git archaeology. Repair becomes verified relocation
  instead of inference, which retires the sibling card's whole anchor-recovery
  problem. 85% of existing cites can take their anchor from HEAD mechanically.
  `file:line` stays clickable in terminals and IDEs.
- *Cons*: every author writes more, forever, on every consuming repo. Numbers
  still rot — this makes rot *visible*, not absent, so hygiene passes continue
  at the same frequency with a cheaper per-cite step. 109 cites cannot be
  migrated mechanically.
- *Edit preview*: `goc/templates/skills/create-card/SKILL.md:144` gains the
  anchor form; `goc/templates/skills/refine-deck/SKILL.md:103`
  (`### Defunct file:line citations`) drops steps 2 and 4's history walk for a
  read-and-compare; `reference.md:111` (`## Citation anchor check`) loses its
  Getting-the-anchor section; plus a 729-cite migration pass over the deck.

**Option B — symbol-relative cites.** Address
`goc/engine.py::_build_parser`, or `file.md § Heading`, instead of a line.

- *Pros*: stable across every edit that does not rename or delete the symbol,
  so the treadmill stops rather than getting cheaper. Covers 88.3% of Python
  cites and 48 of 49 `.md` cites with forms the deck already uses in prose.
  Shortest cards — no anchor text to carry.
- *Cons*: loses the granularity exactly where the deck is densest (22 distinct
  cited lines collapse into one 266-line function). Needs a resolver for the
  65 non-Python, non-Markdown cites. Not clickable. A reader still cannot
  verify a cite by eye — they must trust the symbol still means what it did.
- *Edit preview*: same three skill sites as A, plus a symbol resolver in the
  refine-deck recipe and a 729-cite migration.

**Option C — keep bare line numbers, make the treadmill cheap.** Land the
sibling card's recipe fix, then run repair on every deck commit instead of
per hygiene pass.

- *Pros*: no migration, no authoring change, nothing shipped to consumers
  changes. Numbers are never more than one commit stale.
- *Cons*: buys nothing for the 236 cites the recipe declines, and those are
  the permanent residue. A wrong automated relocation now lands unreviewed at
  commit rate rather than at pass rate. The reader still cannot tell a good
  cite from a rotted one — the harm this card is about is unaddressed.
- *Edit preview*: no card-format change; a new hook or CI step running the
  repair recipe, gated on the sibling card landing first.

**Option D — symbol plus anchor, no line number** (surfaced by the census, not
in the original filing). Write ``goc/engine.py::_build_parser`` followed by
the anchor line. Combines B's stability with A's verifiability and deletes the
rotting number outright; costs A's migration plus B's resolver, and gives up
clickability. Listed because the measurements show A and B are complementary
rather than exclusive — worth a sentence before A or B is picked.

**Recommendation (not binding): A.** It is the only option under which a cold
reader can tell whether the cite in front of them is still true, which is the
failure this card was filed about; and the migration is 85% mechanical today
and less so every week.

Whichever is picked, the sibling card's recipe fix stands on its own and
should not wait on this one.
