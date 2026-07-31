---
title: yaml-lite-duplicate-mapping-key-shadows-the-first-so-status-flips-stop-landing
summary: "The vendored yaml_lite parser silently keeps the LAST of two same-named keys (block mapping and flow mapping alike), while `mutate_frontmatter_field` rewrites the FIRST and a human reading README.md top-down sees the FIRST. A card that acquires a duplicate key therefore passes `goc validate` clean while `goc status <title> active` prints `open -> active`, auto-commits, and leaves the card `open` to every goc surface — the parallel-agent claim lock never engages. The same function raises ParseError for tab indent, over-indent and missing-space-after-colon precisely so a key is never silently dropped; duplicate-key is the one silent key-drop left."
status: done
stage: null
contribution: high
created: "2026-07-31T05:36:47Z"
closed_at: "2026-07-31T05:45:31Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — a repeated key raises `ParseError` in both the block mapping and the flow mapping arm
  - [x] TDD: a regression test asserts `safe_load` raises on a duplicate block-mapping key AND on a duplicate flow-mapping key, and that a single-occurrence document is unaffected
  - [x] TDD: a regression test asserts the whole deck is duplicate-key free, so a merge that reintroduces the shape fails the suite rather than passing `goc validate`
  - [x] MECHANICAL: `_parse_block_mapping` and `_parse_flow_mapping` reject a repeated key, with the message naming the key and the line/pair so the fix site is obvious
  - [x] MECHANICAL: the module docstring's `Unsupported (raises ParseError)` list names duplicate keys
  - [x] MECHANICAL: the live instance `autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish` is repaired (its stale first `summary:` removed) so `uv run goc validate` stays green
  - [x] PROCESS: `uv run python -m unittest discover -s tests` is green and `python scripts/sync_plugin_assets.py --check` reports the three engine mirrors in sync
worker: {who: "claude[bot]", where: main}
---

# A repeated frontmatter key is silently shadowed, so a claim reports success and lands nothing

## Location

- `goc/_vendor/yaml_lite.py:151` — `_parse_block_mapping`: `result[key] = self._resolve_value(rest, indent)`
- `goc/_vendor/yaml_lite.py:441` — `_parse_flow_mapping`: `result[k] = _parse_scalar(val.strip())`
- `goc/engine.py:487` — `mutate_frontmatter_field`: `fm_text = pattern.sub(..., count=1)`
- Live instance: `.game-of-cards/deck/autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish/README.md` lines 3 and 14 (two `summary:` keys)

## What's broken

Three consumers of a card's frontmatter disagree about which copy of a repeated
key is authoritative, and nothing detects the disagreement.

**The parser takes the last.** `_parse_block_mapping` assigns into a plain dict
with no membership check:

```python
self._pos += 1
result[key] = self._resolve_value(rest, indent)
```

`_parse_flow_mapping` does the same for the inline form (`worker: {who: a,
where: b}`):

```python
result[k] = _parse_scalar(val.strip())
```

**The mutator takes the first.** `mutate_frontmatter_field` is deliberately
line-anchored — its docstring says it "Avoids YAML round-trip (which reorders
keys)" — and substitutes with `count=1`, so it rewrites whichever copy appears
first in document order:

```python
fm_text = pattern.sub(lambda _: f"{field_name}: {new_value}", fm_text, count=1)
```

**A human takes the first**, because README.md is read top-down and GitHub
renders the frontmatter in file order.

The silence is the defect, not the last-wins rule itself. The two branches
directly above the offending line in the *same function* both raise
`ParseError`, and their comments say why in as many words — the over-indent
branch:

> A more-indented line is therefore malformed — an over-indented key (silently
> promoted to a sibling) or a bare plain-scalar continuation (which would
> otherwise truncate every following key). Fail loud, matching the tab guard in
> `_peek` and the ambiguous-indent guard in `_parse_block_scalar`.

and the unrecognized-key branch:

> Silently breaking would drop this line AND every key below it from the
> document — the exact truncation the over-indent guard above and the tab guard
> in `_peek` exist to prevent. Fail loud to match that posture.

A duplicate key drops exactly one key rather than a whole tail, but it drops it
just as silently, and it is the only remaining silent key-drop in
`_parse_block_mapping`. The module docstring's `Unsupported (raises
ParseError)` list does not mention duplicate keys either way, so no stated
contract covers the case.

## Empirical evidence

### Before the fix

`uv run python .game-of-cards/deck/yaml-lite-duplicate-mapping-key-shadows-the-first-so-status-flips-stop-landing/reproduce.py`:

```
DEFECT: safe_load('title: foo\nstatus: open\ntags: [bug]\nstatus: done')
     -> {'title': 'foo', 'status': 'done', 'tags': ['bug']}
DEFECT: safe_load('worker: {who: alice, where: main, who: bob}')
     -> {'worker': {'who': 'bob', 'where': 'main'}}
OK (control): over-indented line raises ParseError

reader split on a card carrying two `status:` keys:
  goc status ... active rewrote the FIRST copy   -> 'status: active'
  the parser keeps the LAST copy                 -> status='open'
  => the verb prints 'open -> active', commits, and the card stays open

FAILED:
  - duplicate block-mapping key did NOT raise; returned {'title': 'foo', 'status': 'done', 'tags': ['bug']} (expected ParseError; the first `status: open` was silently dropped)
  - duplicate flow-mapping key did NOT raise; returned {'worker': {'who': 'bob', 'where': 'main'}} (expected ParseError; `who: alice` was silently dropped)
```

End-to-end in a scratch deck, on a card with two `status: open` keys:

```
### validate
OK  dup-status
exit=0

### goc status dup-status active
dup-status: open → active
Next: implement the card; tick DoD items as you go; then goc done dup-status.
  committed

### frontmatter after the claim
4:status: active
13:status: open

### what the queue reports
   status seen by goc: open
```

The verb announced the transition, auto-committed it, and the card is still
`open` on every surface. `goc done` fails the same way: it sets `closed_at` and
rewrites the first `status:`, and the card stays open.

### After the fix

Same `reproduce.py`, exit 0:

```
OK: safe_load('title: foo\nstatus: open\ntags: [bug]\nstatus: done') raised ParseError
OK: safe_load('worker: {who: alice, where: main, who: bob}') raised ParseError
OK (control): over-indented line raises ParseError

reader-split demonstration unreachable (parse refused): YAML parse error inside frontmatter: line 6: duplicate mapping key 'status'; the earlier value would be silently discarded

All checks passed: a repeated mapping key fails loud.
```

`goc validate` on a scratch deck holding the same card now exits 1 with
`ERROR: dup-status: YAML parse error inside frontmatter: line 12: duplicate
mapping key 'status'; the earlier value would be silently discarded`, so the
corruption turns the deck red instead of passing as `OK`. The repo's own deck is
duplicate-key free (0 of 691 cards) after the repair below.

## Why it matters

The claim flip is the **soft lock** that keeps two parallel sessions off the
same card — `Skill(pull-card)` calls it out explicitly ("The status flip is the
soft lock against parallel sessions"), and `card_is_draft`'s docstring points at
`_cmd_status` as the terminal-transition guard. On a duplicate-key card that
lock silently fails open: the claim is reported and committed, `goc --ready`
still offers the card, and the next autonomous pull claims it again.

**Reachability — this is not hypothetical; it happened in this repo.** Two
sessions independently backfilled the required `summary` on the same card at
different anchors:

- `b2e671e6` (bot, "deck: backfill required summary on autonomous-picker card")
  inserted `summary:` directly after `title:`.
- `d0e138c3` (human, "deck: rewind premature decision on autonomous-picker
  card") inserted a *different* `summary:` after `tags:`, plus the rewind.

The two inserts touch different lines, so git merged both without conflict at
`36ab5479`, and the card has carried two contradictory summaries since. AGENTS.md
§ "Parallel-Agent Commit Safety" documents this concurrency as normal operation
("Multiple agents may work on local `main` at the same time"), and the deck is
edited by the cloud `pull-card` workflow and human sessions alike. Hand-editing
is the second path: AGENTS.md tells authors to edit frontmatter by hand, and an
author appending a field they believe is missing without scanning the whole
block produces the same result.

A repo-wide scan finds exactly one instance today (1 of 690 cards), and it is
the one from that merge:

```
autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish: {'summary': 2}
```

`goc` reports the second summary; a reader opening README.md sees the first,
which describes the *pre-rewind* premise the rewind commit explicitly corrected.
So the card that documents a scheduling bug currently mis-briefs whoever reads
it cold — the exact failure `Skill(create-card)` exists to prevent.

Two further silent effects, both demonstrated above:

- **Re-emit verbs delete a key with no notice.** `goc decide`, `goc wait`,
  `goc advance`, `goc quality-pass --apply` and `goc migrate-list-style` all go
  through `emit_frontmatter`, which writes the parsed dict — so the shadowed
  copy vanishes on the next unrelated mutation.
- **`goc migrate-list-style --dry-run` mis-reports the card** as needing a
  list-style rewrite when what it actually plans is to drop the duplicate.

Family: this is the same fail-loud posture question already settled in this file
by [tab-indented-frontmatter-silently-misparses-instead-of-raising](../tab-indented-frontmatter-silently-misparses-instead-of-raising/),
[yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising](../yaml-lite-overindented-frontmatter-line-silently-misparses-instead-of-raising/)
and [yaml-lite-block-mapping-key-without-space-after-colon-silently-truncates-frontmatter](../yaml-lite-block-mapping-key-without-space-after-colon-silently-truncates-frontmatter/),
all closed by making the parser raise. Those three are distinct guards over
distinct constructs, so this is a fourth sibling rather than a fourth instance
of one root cause — there is no shared code path to consolidate. Adjacent but
different: [validate-ignores-unknown-frontmatter-keys-so-typos-pass-silently](../validate-ignores-unknown-frontmatter-keys-so-typos-pass-silently/)
covers keys outside the schema, not keys that appear twice.

## Fix (landed)

A repeated key is rejected in both mapping arms of `goc/_vendor/yaml_lite.py`,
matching the two fail-loud guards already in `_parse_block_mapping`:

- `_parse_block_mapping` — refuses before assigning when `key` is already in
  `result`, naming the key and the 1-based line number the way the over-indent
  and missing-space guards do.
- `_parse_flow_mapping` — same check, naming the key and the flow text.

The module docstring's `Unsupported (raises ParseError)` list now names the case,
so the contract is stated rather than implied.

No engine change was needed: `parse_frontmatter` already converts `ValueError`
into `FrontmatterError`, so the diagnostics route through the existing paths —
`goc validate` reports the card and exits 1, `load_card_or_exit` exits 2 with the
file path, `load_all_cards` warns per card. `mutate_frontmatter_field` is
untouched, because a card it could target ambiguously no longer parses at all.

The live instance was repaired in the same commit: the stale first `summary:` was
deleted from `autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`.
The surviving copy is the later authored one (from the rewind commit
`d0e138c3`), it is what every goc surface already reported, and it matches the
rewound scope in that card's body — so the repair changed no rendered output.

Regression cover in `tests/test_yaml_lite.py`:
`DuplicateMappingKeyRejectionTest` (both arms reject; nested mappings, sibling
sequence items and single-occurrence documents still parse),
`DuplicateTopLevelKeyScanTest` (proves the deck scan catches a planted
offender before it is trusted on the real deck), and
`DeckRoundTripTest.test_no_card_carries_a_duplicate_frontmatter_key` (names every
offending card and key, so a merge that reintroduces the shape gets a readable
diagnostic instead of a bare line number).

The three plugin engine mirrors (`claude-plugin/goc/`, `codex-plugin/goc/`,
`openclaw-plugin/goc/`) are regenerated by the `sync-plugin-assets` pre-commit
hook; no manual edit there.
