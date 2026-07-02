---
title: empty-title-frontmatter-crashes-queue-and-board-renderers
status: active
stage: null
contribution: medium
created: "2026-07-02T01:56:02Z"
closed_at: null
human_gate: none
summary: "A card with a bare `title:` (parses to `None`) makes `Card.title` return `None`, which crashes `goc` and `goc --board` for the WHOLE deck via `_display_width`. `title` is the one member of the status/contribution/human_gate coercion family that was left uncoerced. Fix: `fm.get(\"title\") or card_dir.name` — validate still reads raw `fm[\"title\"]` so the malformed title is still flagged."
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — a card with a bare `title:` renders in the queue (title falls back to dir name) instead of crashing
  - [ ] TDD: `Card.title` returns the directory name (not `None`) for a card whose frontmatter has a bare/empty `title:`
  - [ ] MECHANICAL: `goc validate` still reports the malformed title from raw `fm["title"]` (coercion protects only the renderers, mirroring the sibling fields' documented posture)
  - [ ] PROCESS: regression test added to tests/ and the full suite passes
worker: {who: "claude[bot]", where: main}
---

# empty-title-frontmatter-crashes-queue-and-board-renderers

## Location

`goc/engine.py:915` — `load_card()`.

## What's broken

`load_card` builds the `Card` title with:

```python
title=fm.get("title", card_dir.name),   # engine.py:915
```

`dict.get(key, default)` only substitutes `default` when the key is
**absent**. A card whose frontmatter has a bare `title:` parses to
`{"title": None, ...}` — the key is *present* with value `None` — so
`card_dir.name` is never used and `Card.title` becomes `None`.

Every sibling status-like field is explicitly defended against exactly
this. `Card.status` (engine.py:765), `Card.contribution` (780), and
`Card.human_gate` (785) each coerce `None → ""` with a comment stating
the reason verbatim:

> A card with `status: null` (or a bare `status:`) parses to a Python
> None with the key present, so a plain `.get("status", "")` returns
> None — which then crashes the table/board renderers that call string
> methods on the value. `goc validate` still flags the bad status from
> the raw `fm["status"]`, so coercing here only protects the renderers.

`title` was left out of that family, so `None` flows into the renderers.

## Empirical evidence

(see `reproduce.py` — output pasted here after the fix run)

## Why it matters

**Reachability path.** `title` is a required field, so a well-formed
`goc new` always writes one — but a bare `title:` is a common hand-edit
(clearing the value, a botched rename, a merge that blanks the line). A
malformed card like that is exactly what `goc validate` exists to catch.
`load_all_cards()` is deliberately written so *one* broken card does not
blank the whole queue (bad cards are meant to still list, then be flagged
by `validate`). But with a `None` title the card loads fine, then
`render_table` → `_display_width(r[0])` (engine.py:3081) iterates the
`None` title → `TypeError: 'NoneType' object is not iterable`. That aborts
the plain `goc` queue and `goc --board` for the **entire deck** before
`validate` can report the malformed title — the opposite of the
one-broken-card-doesn't-blank-the-queue design intent. `render_board`'s
`card_cell` path crashes identically.

## Fix

Mirror the sibling coercions — a one-line change at `engine.py:915`:

```python
title=fm.get("title") or card_dir.name,
```

`fm.get("title")` returns `None` for both an absent key and a bare
`title:`; `or card_dir.name` then falls back to the directory name in
both cases (and for an empty-string title too), matching the existing
default-fallback intent. `validate_card` reads the raw `fm["title"]`
(engine.py:1567, 1569), so the `title != dir name` and title-pattern
errors are **not** masked — coercion protects only the renderers, exactly
as documented for the sibling fields.
