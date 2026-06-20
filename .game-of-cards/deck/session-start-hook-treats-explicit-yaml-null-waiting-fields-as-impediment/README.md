---
title: session-start-hook-treats-explicit-yaml-null-waiting-fields-as-impediment
summary: "The SessionStart hook reads `waiting_on`/`waiting_until` with `_frontmatter_tail`, which returns the raw token for an explicit YAML null (`null`, `Null`, `NULL`, `~`). Those non-empty strings make `_is_impeded` report an active impediment, so the hook tells the agent it `cannot resume` an active card the engine considers fully resumable. The engine's yaml_lite resolves the same literals to None (`waiting_impedes` → False)."
status: active
stage: null
contribution: medium
created: "2026-06-20T05:03:15Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (hook and engine agree on `waiting_on: null`, `~`, `Null`, `NULL`, and `waiting_until: null`)
  - [ ] TDD: a regression test asserts `_is_impeded` returns the same verdict as `engine.waiting_impedes` for explicit-YAML-null `waiting_on`/`waiting_until`, and the canonical-reason control still impedes
  - [ ] MECHANICAL: `_card_waiting_on` / `_card_waiting_until` resolve YAML null literals to None, mirroring `yaml_lite._NULL_SET`
  - [ ] PROCESS: edit lands in the template (`goc/templates/hooks/deck_session_start.py`); plugin mirrors re-sync via pre-commit
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# SessionStart hook treats explicit YAML-null `waiting_on` / `waiting_until` as an impediment

## Location

`goc/templates/hooks/deck_session_start.py:73-100` (`_card_waiting_on`,
`_card_waiting_until`) feeding `_is_impeded` at lines 130-173.

## What's broken

The two waiting-field readers return `_frontmatter_tail(line) or None`.
`_frontmatter_tail` (lines 22-40) only strips inline comments and
surrounding quotes — it returns the **raw token**. For an explicit YAML
null written into frontmatter (`waiting_on: null`, `~`, `Null`, `NULL`,
or `waiting_until: null`), the tail is a non-empty string like `"null"`,
so the `or None` fallback never fires:

```python
def _card_waiting_on(readme: Path) -> str | None:
    ...
        if line.startswith("waiting_on:"):
            return _frontmatter_tail(line) or None   # "null" passes through
```

`_is_impeded` then treats that string as a live overlay: a `"null"`
reason hits `if reason is not None: ... return True`, and a `"null"`
`waiting_until` is unparseable so the `until_unparseable` backstop also
returns `True`.

The engine — which `_is_impeded` explicitly documents itself as
mirroring ("Mirrors `goc.engine.waiting_impedes`", lines 133-138) —
parses the same frontmatter through `yaml_lite`, where
`_NULL_SET = frozenset(("null", "Null", "NULL", "~"))`
(`goc/_vendor/yaml_lite.py:43`) resolves all four literals to `None`. So
`Card.waiting_on` / `Card.waiting_until` are `None` and
`engine.waiting_impedes` returns `False`.

## Empirical evidence

`uv run python deck/<title>/reproduce.py`:

```
waiting_on: null                   : hook=True  engine=False  <-- DIVERGE
waiting_until: null                : hook=True  engine=False  <-- DIVERGE
waiting_on: ~                      : hook=True  engine=False  <-- DIVERGE
waiting_on: Null                   : hook=True  engine=False  <-- DIVERGE
waiting_on: NULL                   : hook=True  engine=False  <-- DIVERGE
waiting_on: external (control)     : hook=True  engine=True   (agree)
waiting_on: (empty)                : hook=False engine=False  (agree)
```

## Why it matters

The SessionStart hook is the first thing an agent sees on resume. For an
`active` card whose frontmatter carries an explicit-null waiting field,
the engine view is "resumable" but the hook prints
`[GoC] Impeded active card(s) (waiting_on): <card> — agent cannot
resume.` instead of the resumable line — telling the agent to stand
down on work it actually owns.

Reachability: the engine never *emits* `waiting_on: null` (the
frontmatter emitter writes the key only when a reason is set), so the
offending shape arrives via a hand-edited card or an external tool that
serializes the absent overlay as an explicit YAML null — the same
hand-edit / pre-validate reachability bar the rest of this hook family
already accepts (e.g. the closed
`session-start-hook-treats-non-canonical-waiting-on-as-not-impeded`,
which introduced the current `reason is not None` gate that this null
literal now slips through).

## Fix

Normalize the two waiting readers so YAML null literals resolve to
`None`, mirroring `yaml_lite._NULL_SET`. Add a module-level
`_NULL_SET` and a shared helper, and route both readers through it:

```python
_NULL_SET = frozenset(("null", "Null", "NULL", "~"))

def _scalar_or_none(line: str) -> str | None:
    """Tail of a frontmatter scalar, or None for blank / explicit YAML null."""
    tail = _frontmatter_tail(line)
    return tail if tail and tail not in _NULL_SET else None
```

Edit the template (`goc/templates/hooks/deck_session_start.py`); the
pre-commit `sync-plugin-assets` hook regenerates the Claude/Codex
mirrors. (The OpenClaw TS port is tracked separately by
`openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting`.)
