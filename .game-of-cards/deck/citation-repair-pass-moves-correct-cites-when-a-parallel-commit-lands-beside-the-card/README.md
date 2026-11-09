---
title: citation-repair-pass-moves-correct-cites-when-a-parallel-commit-lands-beside-the-card
summary: "refine-deck's citation recipe anchors a cite at the commit that last wrote its number, assuming the number was computed against that commit's tree. On this repo's shared main, a card can be numbered against the tree of a parallel commit to the cited file that lands minutes before or after it, and the recipe then reads unrelated code at the anchor and moves a correct cite past every guard it has. Two cards found: five cites misread, one moved by this pass and restored, three tracked onto the wrong lines by every pass since 2026-08-10."
status: active
stage: null
contribution: medium
created: "2026-11-09T02:13:07Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: reproduce.py exits 0 — the reference's citation section carries the `anchor tree ambiguous` rule, so the documented recipe no longer moves the five instance cites on its own
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/reference.md` § Citation anchor check states the neighbouring-commit rule from § Fix (the trigger, the two readings, the prose read, the decline), adds the `anchor tree ambiguous` residue row, and its count sentence reads "seven ways"
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/SKILL.md` § Defunct file:line citations carries the rule's one-line form and names the new decline in its list of declines
  - [ ] TDD: `tests/test_refine_deck_citation_anchor.py` gains cases replaying both instances (later tree, earlier tree): the documented recipe does not relocate them on the anchor alone, a recipe without the rule does; its residue-count and decline-naming tests pass
  - [ ] MECHANICAL: plugin mirrors and the OpenClaw port re-synced (`python scripts/sync_plugin_assets.py`, `python3 scripts/port_skills_to_openclaw.py`); `uv run goc validate` and the regression suite pass
worker: {who: "claude[bot]", where: main}
---

# Citation repair pass moves correct cites when a parallel commit lands beside the card

## Location

- `goc/templates/skills/refine-deck/reference.md:435-447` — "**Getting the
  anchor.** A cite means what it meant when its number was last AUTHORED, so
  the anchor commit is the one that wrote the number […] Read the cited file at
  that commit — `git show <commit>:<path>` — and take the cited line's text.
  That text is what the card meant; the number is only its address at the
  time."
- `goc/templates/skills/refine-deck/SKILL.md:162` — the same rule in the core
  skill: "Anchor = that line's text at the commit that last WROTE the number".

## What's broken

The rule treats "the commit that wrote the number" as "the tree the number was
computed against". On this repo's shared `main`, where several agents commit
in parallel (AGENTS.md § Parallel-Agent Commit Safety), the two differ in both
directions:

- **Later tree.** The author numbers the cites against a working tree that
  holds a parallel change to the cited file, and commits the card before that
  change lands.
- **Earlier tree.** The author numbers the cites, a parallel commit to the
  cited file lands, and the card is committed on top of it.

Either way the anchor commit's tree holds different code at the cited number
than the tree the author counted. The recipe reads that unrelated line, finds
it uniquely in HEAD, and moves a correct cite. Every guard passes: the anchor
is substantial, the match unique, and the fixed-point re-run sees a
first-round proposal. The proposal then repeats on every later pass, or, once
one pass applies it, the cite's anchor becomes that pass's commit and every
later pass tracks the wrong line faithfully. The "already resolves at HEAD"
check stops it only when the card's prose names a symbol that sits on the
cited line and not on the target.

## Empirical evidence

**Later tree:**
[openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host](../openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host/)
was committed in `66678c34` (2026-10-31 05:16:46Z). `ffc0f4bc`, 400 s later,
added six lines to `openclaw-plugin/index.ts` above both handlers the card
cites, and the card's numbers fit `ffc0f4bc`. The 2026-11-09 pass proposed
`:763` → `:769` and `:797` → `:804`. It held `:763`, because the prose's
`before_prompt_build` sits on line 763 at HEAD. It applied `:797`, because
`agent_end` also appears in the comment at line 804 (`3ebd9b7e`); `2195ec34`
restored it.

**Earlier tree:**
[auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft](../auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft/)
was committed in `dc484d63` (2026-07-05 01:44:57Z). `6d36c3dc`, 37 s earlier,
added six lines to `goc/engine.py` above the cited calls, and the card's
numbers fit `6d36c3dc^`. At the filing commit, each cite is a `print` six
lines above the `_git_auto_commit` call or `commit_targets` the prose names.
The 2026-08-10 pass (`69e1e4f2`) moved the cites from those anchors. Every
anchored pass since, this one included, tracked the `print` lines. The
staleness re-check and `80268935` re-anchored them by the prose.

[`reproduce.py`](reproduce.py) replays the documented rule on the immutable
commits of both instances. In each, the tree the author numbered against
stands in for HEAD, where every cite is correct by construction:

```text
[later tree] openclaw-plugin/index.ts: anchor commit 66678c34, numbered against ffc0f4bc
  `openclaw-plugin/index.ts:763` — the card means : api.on("before_prompt_build", async (ctx: any) => {
     anchor text at 66678c34  : if ((hasExploration || hasTooling) && !hasWork) return;
     documented rule        : relocate to :769 (unique match)
  `openclaw-plugin/index.ts:797` — the card means : api.on("agent_end", async (ctx: any) => {
     anchor text at 66678c34  : // TODO(verify-context-shape): agent_end is documented as 
     documented rule        : relocate to :804 (unique match)

[earlier tree] goc/engine.py: anchor commit dc484d63, numbered against 6d36c3dc^
  `goc/engine.py:5237` — the card means : if _git_auto_commit(commit_targets, f"deck: {title} {prior
     anchor text at dc484d63  : print(f"Next: implement the card; tick DoD items as you go
     documented rule        : relocate to :5231 (unique match)
  `goc/engine.py:5710` — the card means : if _git_auto_commit([DECK_DIR / title, DECK_DIR / advancer
     anchor text at dc484d63  : print(f"ERROR: adding {advancer} → {title} would create a 
     documented rule        : relocate to :5704 (unique match)
  `goc/engine.py:5426` — the card means : commit_targets = [card_dir, *(DECK_DIR / t for t in advanc
     anchor text at dc484d63  : print(f"Next: edit {rel}/README.md to fill the body and Do
     documented rule        : relocate to :5420 (unique match)

reference.md citation section carries `anchor tree ambiguous`: False

DEFECT PRESENT: the documented recipe moves 5 of 5 correct cites numbered against a parallel commit's tree.
```

**How often a neighbouring commit could be to blame** (2026-11-09). This counts
commits to the cited file, other than the anchor itself, that changed the
line at the cited number:

| window | as-filed cites (681 checked) | current anchors this pass |
|---|---|---|
| ±60 s | 4 cites, 1 card | — |
| ±300 s | 13 cites, 7 cards | 5 cites, 5 cards (all already declined) |
| ±600 s | 44 cites, 14 cards | 23 cites, 11 cards (12 repaired, 11 declined) |
| ±3600 s | 181 cites, 54 cards | — |

A window flags candidates, not misreads. Of the 12 repairs in the ±600 s row,
7 on
[advances-graph-readers-each-trust-one-field-and-disagree-on-half-edged-decks](../advances-graph-readers-each-trust-one-field-and-disagree-on-half-edged-decks/)
(`d39b4083`, 313 s earlier) and 2 on
[query-views-each-decide-by-hand-which-filters-apply-and-keep-drifting](../query-views-each-decide-by-hand-which-filters-apply-and-keep-drifting/)
(479 s earlier) were numbered against the anchor tree. Their anchor lines are
exactly what each card's prose names, and the repairs are right. The 2
OpenClaw cites were misread. The window alone cannot tell these apart; the
prose can.

## Why it matters

A wrong relocation is the failure the recipe is built to refuse ("a wrong
relocation is worse than a decline"). This one passes every guard, is reported
as a repair, and is then laundered: the pass's own commit becomes the anchor,
and every later pass confirms the wrong line. Three cites on the auto-commit
card pointed at `print` statements for four months while their prose named
`_git_auto_commit` calls. The cards affected sit at human gates, where a
reader acts on the cite without re-deriving it.

Related: [file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/)
(open): symbol-anchored cites would remove this class along with ordinary
drift. [second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/)
and [citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits](../citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits/)
(closed) are the earlier anchor-commit defects this rule sits beside.

## Fix

Add a neighbouring-commit rule to reference.md § Citation anchor check, with
its one-line form in SKILL.md step 4. Before relocating a defunct cite, list
the commits to the cited file, other than the anchor commit, whose committer
time is within ten minutes of it on either side. If any of them changed the
line at the cited number, the cite has two readings: the anchor commit's line,
and that line in the tree on the commit's other side. Read the sentence the
cite sits in:

1. Relocate by the reading whose line is what the prose names, if exactly one
   is.
2. If HEAD already holds the other reading's line at the cited number, the
   cite is right as it stands. Leave the number alone.
3. If the prose does not decide, DECLINE it as `anchor tree ambiguous` and
   report it like every other decline.

Add the residue-table row ("The declines split six ways" becomes seven) and
name the decline in SKILL.md's list. Ten minutes covers both instances
(+400 s, −37 s). The measured cost is reading about two dozen sentences per
pass, and the recipe is executed by an agent that reads cards anyway.
Prefer a decline over a guess.

What no anchor rule can reach: a misread an earlier pass already applied. Its
anchor is now that pass's commit, numbered correctly against its own tree.
Finding those takes the prose re-read the staleness re-check does. This pass
found both instances that way, not by any anchor test.
