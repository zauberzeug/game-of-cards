---
title: closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter
summary: "The closure verbs (`goc done`, `goc done --bundle`, `goc status X disproved|superseded`) write `closed_at` unquoted via `mutate_frontmatter_field`. `emit_frontmatter` re-emits the same value quoted because `_YAML_NEEDS_QUOTE` matches the colons in the timestamp. 251 cards in this repo carry the bare form; the next `goc decide` / `goc migrate-list-style` rewrites every one of them on a closed_at-only edit."
status: active
stage: null
contribution: medium
created: "2026-05-29T10:16:55Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero before the fix (drift demonstrated) and continues to exit zero after, but with both writer paths emitting the same line (drift line == False after fix).
  - [ ] TDD: a regression test asserts `mutate_frontmatter_field(text, "closed_at", _utc_now_iso())` yields a line byte-identical to what `emit_frontmatter` would produce for the same value.
  - [ ] MECHANICAL: the closure-verb paths (`_cmd_done`, `_cmd_done_bundle`, the `disproved` / `superseded` write in `do_status`) and any other call site of `mutate_frontmatter_field` for a colon-bearing value either route the value through `_yaml_inline` first or document the intentional bare form.
  - [ ] PROCESS: a single migration pass normalizes the 251 bare-quoted `closed_at` lines in this repo so the dogfood deck stops trapping the next emitter rewrite in a 251-card diff. (Bundle the migration with the fix commit or as a follow-up commit explicitly tagged `[sync auto]`.)
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green; `uv run goc migrate-list-style --dry-run` reports zero `closed_at`-only rewrites on the dogfood deck.
worker: {who: "claude[bot]", where: main}
---

# `closed_at` format drifts between closure verbs and the frontmatter emitter

## Location

- Closure writer: [`goc/engine.py:3252-3255`](../../../goc/engine.py) (`_cmd_done`),
  [`goc/engine.py:3327-3341`](../../../goc/engine.py) (`_cmd_done_bundle`), plus
  the `disproved` / `superseded` path in `do_status` (search for
  `mutate_frontmatter_field(text, "closed_at"` for all sites).
- Emitter quoter: [`goc/engine.py:176`](../../../goc/engine.py)
  (`_YAML_NEEDS_QUOTE = re.compile(r"[:#'\"\\\[\]\{\}\,`@]")`) and
  [`goc/engine.py:228-238`](../../../goc/engine.py) (`_yaml_inline` returns
  the quoted form when `_YAML_NEEDS_QUOTE.search(s)` matches).

## What's broken

`_cmd_done` (and every other closure verb) writes `closed_at` via:

```python
now = _utc_now_iso()                # e.g. "2026-05-29T09:58:40Z"
text = mutate_frontmatter_field(text, "status", "done")
text = mutate_frontmatter_field(text, "closed_at", now)
```

`mutate_frontmatter_field` is a line-anchored regex substitution
(`engine.py:320-348`); it inserts the raw value string verbatim, no
YAML quoting. Result on disk:

```yaml
closed_at: 2026-05-29T09:58:40Z
```

`emit_frontmatter` reaches the same field through `_yaml_inline`, which
applies `_YAML_NEEDS_QUOTE`:

```python
_YAML_NEEDS_QUOTE = re.compile(r"[:#'\"\\\[\]\{\}\,`@]")
...
if _YAML_NEEDS_QUOTE.search(s) or ...:
    return f'"{escaped}"'
```

The colons in `2026-05-29T09:58:40Z` match — so the emitter would
write:

```yaml
closed_at: "2026-05-29T09:58:40Z"
```

Both forms parse cleanly through the vendored parser (the parser only
splits on the first `: ` in the key portion, so it keeps the bare
datetime as-is). The drift is silent at parse time but materialized at
emit time: every whole-frontmatter rewrite path (`goc decide`,
`goc migrate-list-style`, any future emitter pass) flips the bare line
to its quoted form even when the rewrite was supposed to touch a
different field.

## Empirical evidence

`uv run python .game-of-cards/deck/closed-at-format-drifts-between-closure-verbs-and-frontmatter-emitter/reproduce.py`:

```
Path A (closure verbs)              : closed_at: 2026-05-29T12:00:00Z
Path B (emit_frontmatter rewrite)   : closed_at: "2026-05-29T12:00:00Z"
drift                               : True

live deck — closed_at bare        : 251
live deck — closed_at quoted      : 5
→ emit_frontmatter rewrites every bare line to its quoted form on next pass.
```

`uv run goc migrate-list-style --dry-run` corroborates: 128 cards would
be rewritten, with `closed_at` shape being the dominant contributor.

## Why it matters

The mutate-vs-emit divergence has two concrete consequences:

1. **Closure drift hides under unrelated edits.** A user running
   `goc decide <title>` on a closed card to add a `## Decision`
   section sees their diff include a `closed_at` quoting flip on
   every closed card the rewrite touches — noise that hides the
   real change in code review.
2. **Migration commits become 251-card diffs for nothing.** Any
   future emitter-routed migration (the natural way to ship a new
   normalization rule) inflates by 251 cosmetic lines because the
   closure verbs and the emitter disagree on the canonical form for
   `closed_at` specifically.

Reachability is direct: every `goc done` / `goc done --bundle` /
`goc status disproved|superseded` writes the bare form; every
`emit_frontmatter`-routed verb rewrites it. The two writer paths are
both shipping code; the inconsistency is in the contract between
them.

## Fix proposal

Route `mutate_frontmatter_field`'s value through `_yaml_inline` at
each closure site that supplies a colon-bearing value:

```python
text = mutate_frontmatter_field(text, "closed_at", _yaml_inline(now))
```

Alternative: have `mutate_frontmatter_field` itself route its
`new_value` through `_yaml_inline` when the value looks like a bare
scalar (i.e. doesn't already start with a quote / block-indicator
character). The call-site fix is the safer minimum; the
`mutate_frontmatter_field` overhaul is a larger contract change that
might affect existing call sites which intentionally pass already-
serialized YAML (`status`, `human_gate`, block-list bodies).

The migration leg of the DoD normalizes the 251 bare-quoted lines in
the dogfood deck via a one-shot rewrite; afterwards the closure verbs
and the emitter agree on canonical form and `migrate-list-style`
reports zero rewrites on closed_at-only edits.

## Cross-references

- [`mutate-frontmatter-field-corrupts-backslashes-via-regex-replacement-template`](../mutate-frontmatter-field-corrupts-backslashes-via-regex-replacement-template/)
  — closed, sibling defect on the same `mutate_frontmatter_field`
  surface (value-substitution treats the replacement as a regex
  template).
- [`frontmatter-emitter-does-not-quote-empty-string-scalar-that-parses-as-null`](../frontmatter-emitter-does-not-quote-empty-string-scalar-that-parses-as-null/)
  — closed, sibling defect in the same `_yaml_inline` /
  `_YAML_NEEDS_QUOTE` neighborhood.
