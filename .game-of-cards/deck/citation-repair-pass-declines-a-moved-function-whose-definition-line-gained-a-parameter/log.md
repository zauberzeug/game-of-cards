## 2026-09-14 — closed

A definition is named, not addressed — and the pass that proves it ran on
this deck.

### The recipe

`goc/templates/skills/refine-deck/reference.md` § Citation anchor check
gained **A definition is identified by its name, not by its parameter
list**, between the decide-step commentary and the residue table. When
the anchor is a `def`/`class` line and its exact text is absent from
HEAD, the pass retries on a unique `def <name>(` / `class <name>(`
match. Only the identity claim moves; the refusal to guess does not, and
the paragraph carries the two constraints the card asked for as its own
sub-bullets. Two or more definitions of that name is an ambiguous match
and DECLINES — nearest-match is no more available here than to the exact
rule. And the name rule feeds the endpoint mapper only: a range whose
start it relocates past an end that stayed put is the wreck the pair
guard already refuses, and it stays refused there.

Both residue rows the rule touches were narrowed. `anchor text absent`
no longer reads "the cited code was refactored away" as the only
disposition — it now says the name test ran too, and that a rename or a
split reads identically, so a reader stops treating the decline as
evidence the defect is gone. That advice was the actively harmful half of
this defect: a decline costs a lookup, but a decline that recommends
closure costs the card. `ambiguous match` gains the name rule's own
decline.

`SKILL.md` step 4 carries all three parts in condensed form, and the
paragraph under the recipe that read "anchor text that exists nowhere
usually means the cited code was refactored away" now qualifies itself
with "and no unique definition of its name either". The edit landed once
in `goc/templates/skills/refine-deck/`; the pre-commit sync and the
OpenClaw porter propagated it to the five mirrors.

`tests/test_skill_body_size.py` raised the `refine-deck` cap 13_600 ->
14_200 with the rationale, following that file's convention. Eighth
raise, and its argument has one twist the fourth-through-seventh do not:
the decline this rule replaces is honest OUTPUT, so a pass carrying only
a pointer reads a well-formed refusal and has no symptom that would send
it looking for a missing rule behind it.

### The guard

`tests/test_refine_deck_citation_anchor.py` gained:

- `documented_definition_rule(prose)`, demanding all three parts on both
  surfaces, with step 4 as the recipe shipped it as the negative control.
  That control matters here: the sentence reads as complete, because its
  refusal to guess IS complete. What it gets wrong is what the anchor
  identifies.
- `SignatureDriftRelocateTest`, whose fixture is the shape the deck
  produced — a card cites a function by its `def` line, the file grows
  AND the function gains `*, probe: bool = False`. The exact rule
  declines while the function sits uniquely named four lines below the
  cite; the shipped rule finds it. Its third case appends a second
  definition of the same name and asserts the decline.
- `SignatureDriftRangeTest`, which proves constraint 1 end-to-end rather
  than by reading the words: the name rule maps the start to line 10
  while the end anchor still sits at its own line 8, and the pair the
  mapper hands over is inverted. With the pair check on, the range
  declines; with it off, the fixture shows the backwards pair being
  emitted, so the decline is demonstrably the pair check's and not an
  endpoint that never mapped.

Confirmed red-then-green: reverting `SKILL.md` step 4 turns 4 of these
red; restoring it turns them green. 1142 tests pass, up from 1131.

### reproduce.py

Rewritten from a census into a census plus a classifier, the shape this
family settled on. It reads the two shipped surfaces, classifies each,
and runs the walk with the name rule enabled or disabled from that
verdict rather than from the pre-fix rule — so the exit code tracks what
the recipe SAYS, not what the deck happens to hold today.

Its finding is scoped to the class this card is about: an `anchor text
absent` decline whose anchor a unique-name match locates. Declines from
the sibling rules are deliberately not findings. Counting them would
make the guard demand the recipe break its siblings, since the pair check
is SUPPOSED to swallow a name-relocated start whose end stayed put — and
the filed DoD item said "no decline", which is that mistake in one word.
The box was amended at closure to say absent-anchor decline.

The replay also grew the recipe's belt-and-braces rule (a cite that
already resolves at HEAD is not a repair candidate), mechanized as
narrowly as the prose states it: HEAD's cited line is a definition whose
name the card's own text carries. Without it the script proposed moving
a cite off `def _git_auto_commit(...)` — the line the card names in
prose — onto the docstring below it, because the anchor commit had the
docstring at that number. That proposal was correct by the anchor rule
and wrong for the reader, which is exactly the case the belt-and-braces
rule exists for. Modelling it reclassified 7 cites to `current` and
removed the false repair.

### The pass

Run on this deck, in the session that landed the rule:

|  | before | after rule | after applying |
|---|---|---|---|
| current | 431 | 438 | 443 |
| repairs proposed | 1 | 5 | 0 |
| `anchor text absent` | 39 | 32 | 32 |
| recoverable by name | 8 | 0 | 0 |

Five cites were repaired — `card_is_ready` (three cards), and
`_append_marker_block` and `_append_precommit_hook` (one each), all
three functions having changed their signature under cards that name
them. The three remaining in-class cites are ranges their siblings'
rules decline: one on the pair check, two on an end endpoint that is
itself trivial or absent. That is constraint 1 working, not a gap.

The closing re-run the recipe now prescribes proposes ZERO further
repairs, so the pass is a fixed point.

### The DoD's fourth item was amended at closure

As filed it deferred the measurement to "the next `Skill(refine-deck)`
pass" and predicted 12 repairs. The pass ran here instead, which is what
`EMPIRICAL` asks for — the experiment ran and the verdict is documented —
and the number is 5 rather than 12 for two reasons worth keeping: four of
the twelve entries are two tokens counted at two occurrences each, which
the occurrence rule that closed hours earlier declines before the walk;
and three are range cites the pair check and the trivial-anchor rule
decline. The filing measured endpoints under a recipe one commit older
than the one that shipped.

### Left open

The 32 remaining absent-anchor declines are the honest residue: code that
really did move or vanish, and non-Python definition forms the rule does
not reach. The card's non-goals stand — whitespace-normalized and
similarity-ratio matching would have reached 16 further cites this round
and rest on a tuned threshold rather than on an identity claim. The
convention-level question, whether a bare line number should address code
at all, stays parked on
`file-line-citations-drift-again-within-days-of-every-repair-pass`.

## 2026-09-14T05:25:42Z — Closure

- **What changed**: `goc/templates/skills/refine-deck/reference.md`
  § Citation anchor check + `SKILL.md` step 4 — a `def`/`class` anchor
  whose exact text is gone is now relocated on a unique `def <name>(` /
  `class <name>(` match, declining when HEAD holds that name twice and
  leaving step 1's pair check to decide what a range emits; the residue
  table's `anchor text absent` row stops reading a decline as evidence
  the code was refactored away.
- **Verification**: `reproduce.py` — 903 in-scope cites over the
  open/active deck; under the shipped recipe 0 absent-anchor declines are
  recoverable by name (was 8 over 7 cards), repairs proposed 1 -> 5,
  absent-anchor declines 39 -> 32, exit 0. The five repairs were applied
  to the deck and the closing re-run proposes 0 further repairs.
  Reverting `SKILL.md` step 4 turns 4 of the new tests red and
  `reproduce.py`'s classifier to `exact-full-line-equality`; restoring
  it turns them green. Mirror guards clean:
  `scripts/sync_plugin_assets.py --check` and
  `scripts/port_skills_to_openclaw.py --check`. `uv run goc validate`
  exit 0.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 1142 passed / 0 failed / 0 xfailed (52 in
  `tests/test_refine_deck_citation_anchor.py`, up from 41).
- **Bundled with**: n/a

## Closure verification (2026-09-14T05:25:42Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-09-14 — Closure' present
