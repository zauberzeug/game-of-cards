---
title: a-question-mark-in-a-worker-or-tag-writes-frontmatter-no-yaml-reader-accepts
summary: "The emitter's quote trigger reasons only about YAML block context, but three sites splice its output into a flow collection: `_yaml_inline`'s own list branch (`tags: [a, b]`), `_emit_worker` (`worker: {who: x, where: y}`), and `_auto_populate_worker`, which carried a hand copy of the second. In flow context the plain-scalar acceptance set is strictly narrower, and `?` is the one character block context admits mid-scalar that flow context refuses. So `goc status <card> active` on a machine whose git user.name holds a question mark wrote `worker: {who: who?knows, where: main}` - reported OK by `goc validate`, read back exactly by yaml-lite, and rejected outright by PyYAML with a ParserError that took the whole card's frontmatter with it."
status: done
stage: null
contribution: high
created: "2026-09-20T04:56:56Z"
closed_at: "2026-09-20T05:07:44Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: a regression test asserts `_yaml_inline(["a?b"])` and `_emit_worker({"who": "a?b", "where": "main"})` both emit the scalar double-quoted, and that the resulting `tags:` / `worker:` lines round-trip through `goc/_vendor/yaml_lite` unchanged. Fails before the fix.
  - [x] TDD: the same test asserts block-context emission is UNCHANGED — `_yaml_inline("a?b")` and the flat `_emit_worker({"who": "a?b"})` stay bare — so the fix does not re-quote every `?`-bearing summary in the deck.
  - [x] TDD: the claim path is pinned to DELEGATE to `_emit_worker` rather than restate it — `_auto_populate_worker` carried a hand copy of the flow-mapping branch and kept emitting it unquoted after the shared emitter was fixed.
  - [x] TDD: reproduce.py section 2 reports an empty offending-character set (no character is admitted by block context and refused by flow context).
  - [x] MECHANICAL: the `_YAML_SPACE_BOUND_INDICATORS` comment stops claiming `?query` is an ordinary plain scalar without saying "in block context".
  - [x] PROCESS: `uv run goc validate` clean and `uv run python -m unittest discover -s tests` green; `python scripts/sync_plugin_assets.py --check` green (the engine is mirrored into three plugin payloads).
worker: {who: "claude[bot]", where: main}
---

# a `?` in a worker name or tag makes goc write frontmatter no YAML reader accepts

`goc status <card> active` on a machine whose git `user.name` contains a
question mark writes a card whose frontmatter PyYAML refuses to load at all —
while `goc validate` reports `OK` and the vendored parser reads it back
perfectly. The same hazard reaches `tags:`.

## Location

- `goc/engine.py:302` — `_yaml_inline`, whose list branch builds a YAML **flow
  sequence** out of its own recursive output.
- `goc/engine.py:413` — `_emit_worker`, which builds a YAML **flow mapping**
  out of `_yaml_inline` output.
- `goc/engine.py:5858` — `_auto_populate_worker`, the `goc status … active`
  claim path, which carried a **hand copy** of `_emit_worker`'s flat-vs-mapping
  branch rather than calling it.
- `goc/engine.py:229-231` — `_YAML_SPACE_BOUND_INDICATORS`, the exemption that
  is correct for block context and wrong for all three sites above.

## What's broken

The quote trigger's leading-indicator half exempts three characters from
`_YAML_INDICATORS`:

```python
# `-`, `?` and `:` are indicators only when followed by whitespace or standing
# alone: `-v` and `?query` are ordinary plain scalars, while `- v` is a sequence
# entry, `? v` an explicit key, and a bare `-` an empty sequence entry.
_YAML_SPACE_BOUND_INDICATORS = frozenset("-?:")
```

That comment is true **in block context**, which is where every other caller
puts `_yaml_inline`'s result. Three callers do not:

```python
    if isinstance(value, list):
        return "[]" if not value else "[" + ", ".join(_yaml_inline(v) for v in value) + "]"
```

```python
        if where:
            return f"{{who: {_yaml_inline(who)}, where: {_yaml_inline(where)}}}"
```

…and `_auto_populate_worker`, which restated that same branch instead of
calling it — so the claim verb had to be fixed a second time, by hand, after
the shared emitter was already correct:

```python
    who_yaml = _yaml_inline(who)
    if where:
        where_yaml = _yaml_inline(where)
        worker_yaml = f"{{who: {who_yaml}, where: {where_yaml}}}"
```

Inside a flow collection the plain-scalar acceptance set is strictly narrower.
YAML's `c-flow-indicator` characters terminate a plain scalar wherever they
appear, and `?` is a key indicator in flow context regardless of what follows
it — PyYAML's scanner makes this explicit, breaking the plain scan on
`self.flow_level and ch in ',?[]{}'` and refusing `?` as a plain-scalar start
whenever `flow_level` is non-zero. `,`, `[`, `]`, `{` and `}` are already
quoted *anywhere* by `_YAML_NEEDS_QUOTE`:

```python
_YAML_NEEDS_QUOTE = re.compile(r"[:#'\"\\\[\]\{\}\,`@\t]")
```

So `?` is the single character that block context admits mid-scalar and flow
context refuses — and it is exactly the character the space-bound exemption
waves through. A character-class sweep over the printable ASCII range confirms
the set has one member (reproduce.py section 2).

The emitter's own docstring sets the contract this violates:

> The correct oracle is the union of strict-YAML legality and the parser's
> coercions

Strict-YAML legality is evaluated for the wrong context at the two flow sites.

## Empirical evidence

`python3 .game-of-cards/deck/a-question-mark-in-a-worker-or-tag-writes-frontmatter-no-yaml-reader-accepts/reproduce.py`
(PyYAML is the strict-reader oracle and is absent from the project venv, so run
it under a system interpreter; `uv run python` reports the strict checks as
SKIPPED). **Before the fix:**

```
1. Direct emission: the two flow-collection sites
  worker mapping  'worker: {who: who?knows, where: main}'
      -> STRICT REJECT: ParserError: while parsing a flow mapping
  tags sequence   'tags: [bug, needs?review]'
      -> STRICT REJECT: ParserError: while parsing a flow sequence
  worker (flat)   'worker: who?knows'
      -> OK: {'worker': 'who?knows'}
  summary (block)  'summary: who?knows'
      -> OK: {'summary': 'who?knows'}

2. Which characters does block context admit but flow context refuse?
  offending characters: ['?']  (3 shapes)

3. Reachable through a real goc verb (git user.name -> worker.who)
  $ goc status probe-card active   (exit 0)
  emitted: 'worker: {who: who?knows, where: master}'
  goc validate      : OK  probe-card
  yaml_lite reads   : worker={'who': 'who?knows', 'where': 'master'}
  strict YAML reads : REJECT -- ParserError: while parsing a flow mapping

4. Does the repo's own strict-YAML guard catch it?
  check_card_frontmatter_yaml.flag_frontmatter(...) -> []
```

Note what section 1 rules out: the flat `worker: who?knows` and a `?`-bearing
`summary` are both legal and must stay bare. The defect is confined to the flow
sites, so the fix has to be too.

**After the fix** — sections 1 and 3 read `OK` for every reader, and the
character sweep in section 2 reports `offending characters: []  (0 shapes)`:
flow context now admits exactly what block context does. Section 4 is unchanged
by design (see "Nothing catches it" below).

Section 3 is the one that earns its keep: it goes through the real `goc status
… active` verb, and it stayed `REJECT` after `_emit_worker` was fixed, which is
how the third site — `_auto_populate_worker`'s hand copy — surfaced at all.

## Why it matters

**Reachability.** The offending value does not need a hand-edit; three first-party
paths write it:

1. `goc status <title> active` auto-populates `worker` from `git config
   user.name` plus the current branch (`_auto_populate_worker`,
   `goc/engine.py:5858`). Git places no restriction on `?` in an author name.
   The branch half is safe — git refnames forbid `?` — so `who` is the vector.
2. `goc status ... --worker-who` and `goc new --worker` take the value
   straight from the CLI. `_reject_invalid_worker_flag`
   (`goc/engine.py:5123`) rejects only empty and line-break values, so `?`
   passes. The `worker` field is documented as free-form and unregistered —
   "a person slug, a machine name, or a capability tag" — which is precisely
   the space where a `?` shows up.
3. Any project-local canonical tag registered in
   `.game-of-cards/canonical-tags.md` reaches the `tags:` flow sequence.

Once such a value lands, **every** full-frontmatter re-emit verb (`goc wait`,
`goc decide`, `goc advance`, `goc quality-pass`, `goc migrate-list-style`)
rewrites the same broken line, so the card cannot heal by being touched.

**Blast radius is the whole card, not the field.** A flow-collection
`ParserError` aborts the document, so a strict reader loses the title, status
and DoD too — not just the worker. `goc install`'s kickoff briefing promises
each consuming repo, verbatim, that a card is "a plain Markdown file with YAML
frontmatter"; anything downstream that takes that at face value (a `yq`
one-liner, a static-site generator, GitHub's own frontmatter renderer, a CI
lint) fails on the whole card.

**Nothing catches it.** `goc validate` inspects parsed values, not YAML
legality. `yaml_lite` is a deliberate superset and reads it back correctly. And
`scripts/check_card_frontmatter_yaml.py` — the repo-local guard built for
exactly this divergence — skips every value opening with `"`, `'`, `[` or `{`,
which is every line these two sites emit. That blind spot is already filed as
[card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it](../card-summary-with-broken-quoting-passes-both-guards-that-should-catch-it/);
this card is the producer side of it, and is fixable without touching the guard.

**Relation to neighbouring cards.** The closed
[goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse](../goc-writes-card-summaries-a-standard-yaml-reader-cannot-parse/)
derived the leading-indicator rule from YAML 1.2 §5.3 and is what introduced
the space-bound exemption — correctly, for the block context it was reasoning
about. The open
[goc-writes-frontmatter-values-a-standard-yaml-reader-retypes-silently](../goc-writes-frontmatter-values-a-standard-yaml-reader-retypes-silently/)
covers the other half of the same union — *type resolution* rather than
legality — and does not reach this shape. The open
[frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting](../frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting/)
proposes deriving the quote decision from parser behaviour; that factoring would
**not** fix this defect, because `yaml_lite` accepts the value — this is an
emission-context error, not parser drift. Two sibling `_emit_worker` defects
([worker-mapping-with-only-a-branch-emits-invalid-empty-who](../worker-mapping-with-only-a-branch-emits-invalid-empty-who/),
[emit-frontmatter-silently-strips-unknown-worker-sub-keys](../emit-frontmatter-silently-strips-unknown-worker-sub-keys/))
are about the mapping's *shape*, not its quoting.

## Fix (landed)

Make the flow context explicit where the emitter enters one, rather than
widening `_yaml_inline` globally — that would re-quote every `?`-bearing
summary in every deck for no reason.

1. `goc/engine.py` gained `_YAML_FLOW_HAZARDS = frozenset(",[]{}?")` beside the
   existing indicator sets: YAML 1.2 §7.4's `c-flow-indicator` plus the
   flow-context key indicator. It is kept spec-complete rather than minimized
   to `{"?"}` so it reads as *the flow-context rule* and survives any future
   narrowing of `_YAML_NEEDS_QUOTE`.
2. `_yaml_inline` took a keyword-only `flow: bool = False`; the quote trigger
   gained `or (flow and not _YAML_FLOW_HAZARDS.isdisjoint(s))`, and the list
   branch passes `flow=True` on its own recursion — the rendered form *is* a
   flow sequence, whatever context the list itself sits in.
3. `_emit_worker` passes `flow=True` for the two mapping members only. The flat
   branch is an ordinary block value and stays as it was.
4. `_auto_populate_worker` now builds a dict and renders it through
   `_emit_worker` instead of restating the flat-vs-mapping branch. This is the
   part that keeps the defect fixed: the duplicate is *why* the claim verb went
   on emitting an unquoted flow mapping after the shared emitter was corrected.
5. The `_YAML_SPACE_BOUND_INDICATORS` comment now says the exemption is
   block-context and points at `_YAML_FLOW_HAZARDS`.

`tests/test_emitter_flow_context_quoting.py` pins all four halves: the flow
sites quote and still round-trip through `yaml_lite`; block context is
provably untouched; `_YAML_FLOW_HAZARDS` is enumerated independently so
shrinking it in `engine.py` turns the build red; and the claim path is asserted
to *delegate*, not merely to produce the right bytes today. Four of the five
tests fail against the pre-fix engine.

No card in this deck carried a `?` in a tag or in `worker`, so the change
rewrote nothing on re-emit — `goc validate` is clean across all 766 cards and
the full suite is green at 1170 tests.
