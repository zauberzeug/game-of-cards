## 2026-11-09T02:14:07Z — Filed by the refine-deck hygiene pass

Found while closing the pass's citation step. The pass applied 319 anchored
repairs, and its belt-and-braces check (does the prose name a symbol at the
current number but not the new one?) flagged one: `index.ts:763` on the
OpenClaw hooks card, which was held. Reading why showed that its sibling
`:797` had passed the check for the wrong reason and was already applied. Both
cites were written against `ffc0f4bc`, committed six minutes after the card.
`2195ec34` restored `:797` and logged the hold on that card.

Dedup: nine cards carry the citation recipe's history. Eight closed recipe
defects cover the bounds test, the creating-commit anchor, fences, ranges,
trivial anchors, token collisions, definition lines that gained a parameter,
and the commit-before-re-run order. The
open `file-line-citations-drift-again-within-days-of-every-repair-pass` asks
whether to leave bare line numbers altogether. None covers a number computed
against a tree other than its anchor commit's.

Filed at `human_gate: none` with a concrete rule, because the census
separates the shape cleanly on this deck: 2 true cases, 0 false ones. The
recipe's existing stance (decline rather than guess) settles what to do with
a hit.

## 2026-11-09T02:16:03Z: renamed from citation-repair-pass-moves-correct-cites-written-against-code-committed-after-the-card

## 2026-11-09T02:22:09Z — Second instance, opposite direction; retitled and re-scoped

Batch E of the same pass's staleness re-check reported that the
`engine.py` cites on
`auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft`
sat six lines above the code their prose names. They were numbered against
`6d36c3dc^`. That commit landed 37 s before the card's filing commit
`dc484d63`, so this is the earlier-tree mirror of the OpenClaw case. Every
anchored pass since 2026-08-10 tracked the wrong lines; `80268935`
re-anchored them by the prose.

- **Retitled** from `…-written-against-code-committed-after-the-card` to
  `…-when-a-parallel-commit-lands-beside-the-card` (`goc move`), since the
  shape runs both ways.
- **Fix re-scoped.** The first draft declined on "next commit within an hour
  and HEAD still holds its line". That condition misses the earlier-tree case,
  and a window alone is too blunt. At current anchors, ±10 min flags 23 cites;
  only 2 were misread, 9 checked correct, and the rest were declined anyway. So
  the window now triggers a prose read, and the decline applies only when the
  prose does not decide.
- `reproduce.py` now replays both instances (5 of 5 correct cites moved).
- Contribution raised to `medium`, in line with the token-collision and
  trivial-anchor recipe defects: the misread is laundered into a confident
  anchor and survives every later pass.

## 2026-11-09T05:03:39Z — Closure

- **What changed**: `goc/templates/skills/refine-deck/reference.md`
  § Citation anchor check — new paragraph "A neighbouring commit can own the
  number." (window, two readings, prose read, `anchor tree ambiguous`
  decline, measurement, the two shapes out of reach), a seventh residue row,
  and "The declines split seven ways". `goc/templates/skills/refine-deck/SKILL.md`
  — step 4 opens with the rule's one-line form; the list of declines names
  `anchor tree ambiguous`. `tests/test_refine_deck_citation_anchor.py` —
  `documented_neighbour_rule` classifier and 14 tests in four classes
  (`DocumentedNeighbourRuleTest` 6, `LaterTreeNeighbourTest` 3,
  `EarlierTreeNeighbourTest` 2, `NeighbourRuleScopeTest` 3) on git fixtures
  with pinned commit times. `tests/test_skill_body_size.py` — refine-deck cap
  15,700 → 16,000 (eleventh raise, rationale beside the cap); the skill had
  102 bytes of headroom and now measures 15,975. Mirrors re-synced and the
  OpenClaw port re-run.
- **Design change from the filed § Fix**: its step 2 ("HEAD already holds the
  other reading's line → leave the number alone") is applied only once the
  prose has picked the neighbour's reading. Run on its own, it would certify
  as `current`, in silence, a cite counted on the anchor tree that the
  neighbour's change rotted, since HEAD keeps the neighbour's line at that
  number until something moves it. So prose that does not decide always
  declines. Both instances still come out right: the later-tree cite whose
  prose names the neighbour's line is left alone, the earlier-tree cite is
  relocated by the line its prose names.
- **Verification**: `reproduce.py` exits 0 (was 1: 5 of 5 correct cites
  moved). Against the pre-fix `SKILL.md` and `reference.md` (read from HEAD,
  swapped into the test module), 5 of the 18 tests in the new classes plus
  `ResidueAccountingTest` fail — the core skill's classification, the residue
  row, and the three documented-recipe replays — while the fixture proofs and
  scope controls pass, so the fixtures exercise the defect and the specs
  catch its return. (The sibling-agreement test passes on the old prose too:
  both surfaces classify as reading no second tree.) In the replays the rule keeps the later-tree `on_prompt`
  cite at 7 (the anchor alone moves it to the guard at 8), declines the
  `on_agent_end` cite whose symbol sits on both readings (anchor alone: 12),
  and relocates the earlier-tree cite to the call at 9 (anchor alone: the
  `print` at 8).
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1489 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`); `uv run goc validate` 0 errors;
  `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check`
  both OK.
- **Bundled with**: none. No other open or active card describes this
  defect. The OpenClaw instance card's log carried a hold contingent on it
  ("until the recipe can tell which tree a cite was written against"), so it
  gets a forward-pointer entry.

## Closure verification (2026-11-09T05:04:33Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-11-09T05:03:39Z — Closure' present
