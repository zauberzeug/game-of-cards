---
title: a-question-mark-in-a-worker-or-tag-writes-frontmatter-no-yaml-reader-accepts
summary: "The emitter's quote trigger reasons only about YAML block context, but `_yaml_inline` splices its own output into flow collections (`tags: [a, b]`) and `_emit_worker` splices it into a flow mapping (`worker: {who: x, where: y}`). In flow context the plain-scalar acceptance set is strictly narrower, and `?` is the one character block context admits mid-scalar that flow context refuses. So `goc status <card> active` on a machine whose git user.name holds a question mark writes `worker: {who: who?knows, where: main}` — reported OK by `goc validate`, read back correctly by yaml-lite, and rejected outright by PyYAML with a ParserError that takes the whole card's frontmatter with it."
status: open
stage: null
contribution: high
created: "2026-09-20T04:56:56Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
draft: true
definition_of_done: |
  - [ ] TDD: a regression test asserts `_yaml_inline(["a?b"])` and `_emit_worker({"who": "a?b", "where": "main"})` both emit the scalar double-quoted, and that the resulting `tags:` / `worker:` lines round-trip through `goc/_vendor/yaml_lite` unchanged. Fails before the fix.
  - [ ] TDD: the same test asserts block-context emission is UNCHANGED — `_yaml_inline("a?b")` and the flat `_emit_worker({"who": "a?b"})` stay bare — so the fix does not re-quote every `?`-bearing summary in the deck.
  - [ ] TDD: reproduce.py section 2 reports an empty offending-character set (no character is admitted by block context and refused by flow context).
  - [ ] MECHANICAL: the `_YAML_SPACE_BOUND_INDICATORS` comment stops claiming `?query` is an ordinary plain scalar without saying "in block context".
  - [ ] PROCESS: `uv run goc validate` clean and `uv run python -m unittest discover -s tests` green; `python scripts/sync_plugin_assets.py --check` green (the engine is mirrored into three plugin payloads).
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
- `goc/engine.py:229-231` — `_YAML_SPACE_BOUND_INDICATORS`, the exemption that
  is correct for block context and wrong for both sites above.

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
puts `_yaml_inline`'s result. Two callers do not:

```python
    if isinstance(value, list):
        return "[]" if not value else "[" + ", ".join(_yaml_inline(v) for v in value) + "]"
```

```python
        if where:
            return f"{{who: {_yaml_inline(who)}, where: {_yaml_inline(where)}}}"
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

`python3 .game-of-cards/deck/a-question-mark-in-a-worker-or-tag-writes-frontmatter-no-yaml-reader-accepts/reproduce.py`:

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
    probe-card: open → active
  emitted: 'worker: {who: who?knows, where: master}'
  goc validate      : OK  probe-card
  yaml_lite reads   : worker={'who': 'who?knows', 'where': 'master'}
  strict YAML reads : REJECT -- ParserError: while parsing a flow mapping

4. Does the repo's own strict-YAML guard catch it?
  check_card_frontmatter_yaml.flag_frontmatter(...) -> []
```

Note what section 1 rules out: the flat `worker: who?knows` and a `?`-bearing
`summary` are both legal and must stay bare. The defect is confined to the two
flow-collection sites, so the fix must be too.

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

## Fix

Make the flow context explicit at the point where the emitter enters one, so
the quote trigger can widen for it, rather than widening `_yaml_inline`
globally (which would re-quote every `?`-bearing summary in the deck for no
reason).

In `goc/engine.py`, beside the existing indicator sets:

```python
# `c-flow-indicator` plus the flow-context key indicator: inside `[...]` or
# `{...}` a plain scalar additionally cannot contain any of these. `,[]{}` are
# already quoted anywhere by `_YAML_NEEDS_QUOTE`, so `?` — exempted above
# because it is space-bound in BLOCK context — is the only one this adds.
_YAML_FLOW_HAZARDS = frozenset(",[]{}?")
```

Give `_yaml_inline` a keyword-only `flow: bool = False`, pass `flow=True` on
the list-element recursion, add `or (flow and _YAML_FLOW_HAZARDS.intersection(s))`
to the quote trigger, and have `_emit_worker` call
`_yaml_inline(..., flow=True)` in the mapping branch only — the flat branch is
block context and must stay as it is. Then correct the
`_YAML_SPACE_BOUND_INDICATORS` comment to say the exemption is block-context.

No card in this deck currently carries a `?` in a tag or in `worker`, so the
fix rewrites nothing on the next re-emit.
