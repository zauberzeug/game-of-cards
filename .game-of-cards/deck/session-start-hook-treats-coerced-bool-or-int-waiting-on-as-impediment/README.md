---
title: session-start-hook-treats-coerced-bool-or-int-waiting-on-as-impediment
status: done
stage: null
contribution: medium
created: "2026-06-22T08:38:45Z"
closed_at: "2026-06-22T08:46:16Z"
human_gate: none
advances:
  - session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
summary: "The session-start hook re-implementations of `waiting_impedes` (Python `goc/templates/hooks/deck_session_start.py:_is_impeded` and TS `openclaw-plugin/index.ts:isImpeded`) keep the raw `waiting_on` token string, so a value the yaml-lite parser coerces to bool/int (`false`, `true`, `yes`, `no`, `42`) is reported impeded by both hooks while the engine — which drops non-string `waiting_on` via `isinstance(v, str)` — resolves it to None and treats the card as resumable. This is the opposite matrix cell of the just-closed `session-start-hook-treats-non-canonical-waiting-on-as-not-impeded`: that fix widened the hooks to \"any non-empty reason impedes\", which now over-fires on parser-coerced non-string tokens."
definition_of_done: |
  - [x] TDD: a regression test constructs active cards with `waiting_on: false` (and `true` / `yes` / `no` / `42`) and no `waiting_until`, asserting `engine.waiting_impedes` is False while the unfixed `deck_session_start._is_impeded` is True — fails before fix, passes after.
  - [x] TDD: fix in `goc/templates/hooks/deck_session_start.py` mirrors the engine's `isinstance(v, str)` resolution for `waiting_on` only — a token in `_TRUE_SET ∪ _FALSE_SET` or matching `_INT_RE` resolves to None (not impeded). The `waiting_until` reader is NOT narrowed the same way (the engine's `waiting_until` property has no `isinstance` guard).
  - [x] TDD: same widening ported into `openclaw-plugin/index.ts` `isImpeded` so the TS hook agrees with the engine on coerced bool/int `waiting_on`.
  - [x] TDD: no behavior change for canonical reasons (external / resource / deferred), other non-canonical *string* reasons (the sibling card's cell — e.g. `externl` still impedes), bare-`waiting_until` deferrals, elapsed-`until` resurfacing, the `until_unparseable` backstop, or the all-empty cell.
  - [x] EMPIRICAL: `reproduce.py` exits 0 (engine and hook agree across all coerced values).
  - [x] PROCESS: pre-commit `sync-plugin-assets` regenerates the Claude-Code / Codex plugin mirrors of `deck_session_start.py`; CI parity stays green.
worker: {who: "claude[bot]", where: main}
---

# Session-start hook treats coerced bool/int `waiting_on` as an impediment

## Location

- `goc/templates/hooks/deck_session_start.py:46-55` — `_scalar_or_none`
  (the resolver behind `_card_waiting_on`), and `:145-188` — `_is_impeded`.
- `openclaw-plugin/index.ts:209-228` — `isImpeded` (`if (waitingOn !== "")`),
  fed by `scalarOrEmpty`.
- Engine reference (the contract these helpers MUST mirror):
  `goc/engine.py:691-695` — `Card.waiting_on`; `goc/engine.py:2183+` —
  `waiting_impedes`.

## What's broken

The engine resolves `waiting_on` through an `isinstance` guard
(`goc/engine.py:691-695`):

```python
@property
def waiting_on(self) -> str | None:
    """Stored impediment reason: external, resource, deferred — or None."""
    v = self.frontmatter.get("waiting_on")
    return v if isinstance(v, str) and v else None
```

The yaml-lite parser coerces bare scalars: `false`/`true`/`yes`/`no` become
Python `bool`, and an all-digit token becomes `int`
(`goc/_vendor/yaml_lite.py:35,44-45`, `_INT_RE` / `_TRUE_SET` / `_FALSE_SET`).
So `waiting_on: false` lands in the frontmatter as the bool `False`;
`isinstance(False, str)` is False, the property returns `None`, and
`waiting_impedes` reports the card **resumable**.

The hook re-implementation keeps the raw token. `_scalar_or_none` filters only
`_NULL_SET`:

```python
def _scalar_or_none(line: str) -> str | None:
    tail = _frontmatter_tail(line)
    return tail if tail and tail not in _NULL_SET else None
```

so `waiting_on: false` yields the non-empty string `"false"`. The just-closed
sibling `session-start-hook-treats-non-canonical-waiting-on-as-not-impeded`
widened `_is_impeded` from enum-membership to "any non-None reason impedes"
(`reason is not None` at `:181`). That widening is correct for *string*
reasons but now over-fires on the parser-coerced non-string tokens the engine
deliberately drops. The TS port has the identical shape — `if (waitingOn !==
"")` at `openclaw-plugin/index.ts:227`.

This is the **opposite matrix cell** of the sibling: the sibling fixed values
the hook treated as *not* impeded but the engine treated as impeded; this card
covers values the hook treats as impeded but the engine treats as *not*
impeded.

## Empirical evidence (resolved)

`uv run python .game-of-cards/deck/session-start-hook-treats-coerced-bool-or-int-waiting-on-as-impediment/reproduce.py` now exits 0:

```
waiting_on:  'false' | engine.waiting_impedes=False | hook._is_impeded=False | card.waiting_on=None
waiting_on:   'true' | engine.waiting_impedes=False | hook._is_impeded=False | card.waiting_on=None
waiting_on:    'yes' | engine.waiting_impedes=False | hook._is_impeded=False | card.waiting_on=None
waiting_on:     'no' | engine.waiting_impedes=False | hook._is_impeded=False | card.waiting_on=None
waiting_on:     '42' | engine.waiting_impedes=False | hook._is_impeded=False | card.waiting_on=None

No divergence: engine and hook agree across coerced values. Fixed.
```

Pre-fix, every row reported `hook._is_impeded=True` against `engine.waiting_impedes=False`.

## Why it matters

The SessionStart hook is the agent's first signal at session start. When it
mis-classifies an active, non-impeded card as impeded, it prints
`[GoC] Impeded active card(s) (waiting_on): <card> — agent cannot resume.`
and the agent stands down from a card the engine considers resumable — the
exact false "cannot resume" advisory the sibling fix was meant to eliminate,
just in the other direction.

Reachability: `waiting_on: no` is a plausible hand-edit ("no wait" written as
a YAML bool) and `goc validate` does not reject it (the engine reads it as
None, equivalent to absent). `goc wait` always writes canonical strings, so
the trigger is a hand-authored or hand-edited card — the same authoring path
the sibling cells cover.

## Fix (applied)

`_card_waiting_on` in `goc/templates/hooks/deck_session_start.py` now mirrors
the engine's `isinstance(v, str)` resolution, scoped to `waiting_on` only:
after `_scalar_or_none` resolves the tail, a token in `_TRUE_SET ∪ _FALSE_SET`
(parser-coerced to bool) or matching `_INT_RE` (coerced to int) resolves to
`None`. The three coercion constants were mirrored from
`goc._vendor.yaml_lite` into the hook. `_card_waiting_until` is deliberately
left unchanged — the engine's `waiting_until` property has no `isinstance`
guard, so its unparseable-backstop contract still depends on the raw token.

The TS port adds `BOOL_LITERALS` / `INT_RE` and a dedicated `waitingOnScalar`
reader in `openclaw-plugin/index.ts` that resolves a coerced bool/int token to
`""` before the `waitingOn !== ""` test; the `waiting_until` read keeps
`scalarOrEmpty`. The pre-commit `sync-plugin-assets` hook regenerated the
Claude-Code and Codex plugin mirrors of `deck_session_start.py`.

`reproduce.py` now exits 0: engine and hook agree (`_is_impeded=False`) across
all five coerced values.
