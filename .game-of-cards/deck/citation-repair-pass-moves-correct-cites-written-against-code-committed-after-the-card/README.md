---
title: citation-repair-pass-moves-correct-cites-written-against-code-committed-after-the-card
summary: "refine-deck's citation recipe anchors a cite at the commit that last wrote its number, assuming the number was computed against that commit's tree. A card written beside a parallel change to the cited file that is committed minutes later carries numbers for the later tree, so the recipe reads unrelated code at the anchor, finds it uniquely in HEAD and proposes moving a correct cite; every per-cite guard passes and every later pass re-proposes it. Seen on one card in the 2026-11-09 pass: two cites misread, one wrongly moved and restored."
status: open
stage: null
contribution: low
created: "2026-11-09T02:13:07Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: reproduce.py exits 0 — the reference's residue table carries the `anchor tree ambiguous` decline, so the documented recipe no longer moves the two instance cites
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/reference.md` § Citation anchor check states the later-tree rule from § Fix, adds the `anchor tree ambiguous` residue row, and its count sentence reads "seven ways"
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/SKILL.md` § Defunct file:line citations carries the rule's one-line form and names the new decline in its list of declines
  - [ ] TDD: `tests/test_refine_deck_citation_anchor.py` gains a case that replays the instance (the documented recipe declines both cites, a recipe without the rule moves them), and its residue-count and decline-naming tests pass
  - [ ] MECHANICAL: plugin mirrors and the OpenClaw port re-synced (`python scripts/sync_plugin_assets.py`, `python3 scripts/port_skills_to_openclaw.py`); `uv run goc validate` and the regression suite pass
---
# Citation repair pass moves correct cites written against code committed after the card

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
computed against". The two differ when the card's author worked beside a
change to the cited file that was not committed yet — the normal state on this
repo's shared `main`, where several agents commit in parallel (AGENTS.md
§ Parallel-Agent Commit Safety). The author sees the change in the working
tree, numbers the cites against it, and commits the card first. The anchor
commit's tree then lacks the lines the author counted, so the recipe reads
unrelated code at the cited number, finds that text uniquely in HEAD, and
proposes moving a cite that is correct.

Every guard the recipe has passes on such a proposal. The anchor line is
substantial, the match is unique, and it is a first-round proposal, so the
fixed-point re-run does not flag it. The anchor stays the filing commit, so
every later pass proposes the same move again. The one check that can stop it
is the "already resolves at HEAD" rule, and only when the card's prose names a
symbol that sits on the cited line and not on the target.

## Empirical evidence

[`openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host`](../openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host/)
was committed in `66678c34` (2026-10-31 05:16:46Z). `ffc0f4bc` (05:23:26Z) then
added six lines to `openclaw-plugin/index.ts` above both handlers the card
cites. The card's numbers fit `ffc0f4bc`'s tree: `:763` is the
`before_prompt_build` registration, `:797` the `agent_end` registration, and
the bare `:764`, `:773`, `:798`, `:808`, `:819`, `:821` the reads and
deliveries its § Location lists.

The 2026-11-09 hygiene pass anchored those cites at `66678c34` and proposed
`:763` → `:769` and `:797` → `:804`. It held `:763`, because the prose's
`before_prompt_build` sits on line 763 at HEAD. It applied `:797`, because
`agent_end` also appears in the comment at line 804 (`3ebd9b7e`); `2195ec34`
restored it. [`reproduce.py`](reproduce.py) replays the documented rule on the
two immutable commits, taking `ffc0f4bc` as HEAD, the tree in which every
cite is correct by construction:

```text
openclaw-plugin/index.ts: anchor commit 66678c34, next commit to the file ffc0f4bc 400s later

`openclaw-plugin/index.ts:763` — the card means : api.on("before_prompt_build", async (ctx: any) => {
   anchor text at 66678c34   : if ((hasExploration || hasTooling) && !hasWork) return;
   documented rule          : relocate to :769 (unique match)

`openclaw-plugin/index.ts:797` — the card means : api.on("agent_end", async (ctx: any) => {
   anchor text at 66678c34   : // TODO(verify-context-shape): agent_end is documented as ob
   documented rule          : relocate to :804 (unique match)

reference.md residue table carries `anchor tree ambiguous`: False

DEFECT PRESENT: the documented recipe moves 2 of 2 correct cites written against a tree committed after the card.
```

Census, same pass: of the 891 in-scope cites in open/active cards, 6 have a
cited file that was committed again within an hour of the anchor commit with
a different line at the cited number. In 2, both on this card, HEAD still
holds the later tree's line at that number. In the other 4, HEAD does not
hold that line, and the anchor commit's line is what each card's prose names.
Those cites were written against the anchor tree and repaired correctly.

## Why it matters

A wrong relocation is the failure the recipe is built to refuse ("a wrong
relocation is worse than a decline"). This one passes every guard, is
reported as a successful repair, and comes back on every later pass. The
deck's own workflow produces the shape: parallel agents on one `main`, and
cards that cite the fix landing beside them. The measured rate is low, 2 of
891 cites. The cost is a correct cite moved without a trace, on cards that sit
at a human gate for months.

Related: [file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/)
(open): symbol-anchored cites would remove this class along with ordinary
drift. [second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/)
and [citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits](../citation-idempotence-re-run-reports-false-repairs-until-the-pass-commits/)
(closed) are the earlier anchor-commit defects this rule sits beside.

## Fix

Add a later-tree rule to reference.md § Citation anchor check, with its
one-line form in SKILL.md step 4. Before relocating a defunct cite, read the
cited file at the next commit that touched it after the anchor commit. If
all three hold, DECLINE the cite as `anchor tree ambiguous`:

1. that commit's committer time is within one hour of the anchor commit's,
   in either direction;
2. it holds a different line at the cited number than the anchor commit;
3. HEAD still holds that later line at the cited number.

Report the decline like every other one. Do not call the cite `current`: the
recipe cannot tell which tree the author used, and a `current` verdict is
silence (the trivial-anchor rule declines for the same reason). Add the row to
the residue table ("The declines split six ways" becomes seven) and name the
decline in SKILL.md's list.

On this deck the three conditions select exactly the two misread cites: the
four correctly anchored cites in the census fail condition 3. Conditions 1 and
2 alone would also decline those four, which costs a reader one lookup each
and moves nothing.
