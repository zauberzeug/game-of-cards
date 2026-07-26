---
title: a-wait-reason-starting-with-zero-makes-an-impeded-card-look-resumable
summary: "Both SessionStart hook ports (the Python template shipped to Claude Code/Codex and the OpenClaw TypeScript port) mirror the engine's yaml-lite integer regex as `^-?\\d+$`, but yaml-lite narrowed it to `^-?(0|[1-9][0-9]*)$` on 2026-06-28 so leading-zero runs stay strings. The mirrors were never updated, so a card with `waiting_on: 007` is impeded by the engine yet announced to the agent as a resumable active card — the exact contract the hooks promise to uphold for hand-edited, pre-validate decks."
status: active
stage: null
contribution: medium
created: "2026-07-26T10:21:56Z"
closed_at: null
human_gate: none
advances:
  - session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
  - openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — every port's integer regex equals
    `yaml_lite._INT_RE.pattern`, and the Python hook's `_is_impeded` agrees with
    `engine.waiting_impedes` on `007` / `00` / `0123`
  - [ ] TDD: a regression test pins all three literals (Python hook template,
    `openclaw-plugin/index.ts`, the committed `dist/index.js` bundle) to
    `yaml_lite._INT_RE.pattern` read from the engine, so a future narrowing of
    the canonical regex fails the build instead of drifting silently
  - [ ] MECHANICAL: `openclaw-plugin/dist/` rebuilt from the edited `index.ts`
    via `npm ci && npm run build`, so the shipped bundle carries the fix
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and
    `uv run goc validate` pass
worker: {who: "claude[bot]", where: main}
---

# A wait reason starting with zero makes an impeded card look resumable

## Location

Three copies of one constant, two of which claim in their own comments to
mirror the third:

- `goc/_vendor/yaml_lite.py:40` — the canonical definition.
- `goc/templates/hooks/deck_session_start.py:30` — the SessionStart hook
  shipped to Claude Code and Codex (and mirrored byte-for-byte into
  `.claude/hooks/`, `claude-plugin/hooks/`, `codex-plugin/hooks/`).
- `openclaw-plugin/index.ts:147` — the TypeScript port, plus its committed
  esbuild output at `openclaw-plugin/dist/index.js:2456`.

## What's broken

`yaml_lite._INT_RE` was deliberately narrowed so leading-zero runs stay
strings:

```python
# goc/_vendor/yaml_lite.py:35-40
# Canonical decimal integer (YAML 1.2 / PyYAML decimal resolver): an optional
# sign, then `0` alone or a non-zero digit followed by more digits. Leading-zero
# runs (`00`, `007`, `008`, `0123`) are NOT integers — they stay strings, so the
# parser preserves the literal a human hand-authored instead of `int()`-stripping
# the zeros (which silently changes `008` to `8`).
_INT_RE = re.compile(r"^-?(0|[1-9][0-9]*)$")
```

Both hook ports still carry the pre-narrowing form while asserting they track
that very constant:

```python
# goc/templates/hooks/deck_session_start.py:23-30
# Mirrors `goc._vendor.yaml_lite._TRUE_SET` / `_FALSE_SET` / `_INT_RE`: tokens
# ...
_INT_RE = re.compile(r"^-?\d+$")
```

```ts
// openclaw-plugin/index.ts:141-147
// Mirrors `goc._vendor.yaml_lite._TRUE_SET` / `_FALSE_SET` / `_INT_RE` (and the
// Python hook's same-named constants): tokens the yaml-lite parser coerces away
// from `str` (to bool / int). ...
const INT_RE = /^-?\d+$/;
```

The mirrors exist to reproduce `Card.waiting_on`'s `isinstance(v, str)` guard:
a token the parser coerces to a non-`str` reads as "no reason". Because they
over-match, `waiting_on: 007` is discarded as an integer and the card reads as
carrying no impediment. The engine keeps it as the string `"007"` and impedes.

The hooks' own docstring is what this contradicts:

> any non-None reason (canonical *or* a typo'd / hand-edited value that has not
> yet been through `goc validate`) impedes unless `waiting_until` is elapsed

`007` is exactly such a hand-edited value, and the hook does not impede it.

## Empirical evidence

`uv run python .game-of-cards/deck/a-wait-reason-starting-with-zero-makes-an-impeded-card-look-resumable/reproduce.py`
(verbatim):

```
engine  yaml_lite._INT_RE = ^-?(0|[1-9][0-9]*)$
python  hook _INT_RE      = ^-?\d+$
openclaw index.ts INT_RE  = ^-?\d+$

[FAIL] goc/templates/hooks/deck_session_start.py: _INT_RE does not mirror yaml_lite._INT_RE
[FAIL] openclaw-plugin/index.ts: INT_RE does not mirror yaml_lite._INT_RE
[FAIL] openclaw-plugin/dist/index.js: shipped bundle carries a stale INT_RE (rebuild with `npm run build`)

waiting_on   engine     python hook  verdict
------------ ---------- ------------ -------
007          True       False        [FAIL] disagree
00           True       False        [FAIL] disagree
0123         True       False        [FAIL] disagree
0            False      False        ok
-0           False      False        ok
42           False      False        ok
-7           False      False        ok
external     True       True         ok

[FAIL] 6 divergence(s) — a leading-zero wait reason is announced as resumable while the engine impedes the card
```

A differential sweep of the full `waiting_on` × `waiting_until` matrix (26 × 7
values, including every canonical reason, both null spellings, quoted and bare
bool/int forms, elapsed/future/malformed dates) found the leading-zero cases to
be the *only* remaining divergence between hook and engine.

## Why it matters

The SessionStart hook is what tells an agent which claimed cards it may pick
back up. Its impeded list prints `— agent cannot resume.` A leading-zero wait
reason drops the card out of that list, so the agent is invited to resume work
the engine considers blocked — while `goc --ready` and `goc --waiting` keep
hiding it. The two surfaces disagree in the unsafe direction.

Reachability is the hand-edited window the hooks were written for, and only
that window: `goc wait --reason` is enum-constrained (`external` / `resource` /
`deferred`), and `goc validate` rejects `waiting_on: 007` outright. The hooks
run before any of that — on a deck a human has just edited by hand, which their
docstrings name as the case they cover. Narrow, but it is the one case the code
claims to handle.

This is the third instance of the same shape on
[session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/),
after
[session-start-hook-treats-coerced-bool-or-int-waiting-on-as-impediment](../session-start-hook-treats-coerced-bool-or-int-waiting-on-as-impediment/)
(closed 2026-06-22, which *introduced* the `^-?\d+$` mirror) and
[session-start-hook-over-coerces-quoted-waiting-scalars-to-absent](../session-start-hook-over-coerces-quoted-waiting-scalars-to-absent/)
(closed 2026-06-22). The drift was created six days later by
[yaml-lite-coerces-leading-zero-scalars-to-int-corrupting-string-values](../yaml-lite-coerces-leading-zero-scalars-to-int-corrupting-string-values/)
(closed 2026-06-28), which narrowed the canonical regex without sweeping the
two copies that cite it. The OpenClaw twin of the same duplication is
[openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/).

## Fix

Make both mirrors match the canonical regex, and pin them with a test so the
next narrowing cannot drift again:

1. `goc/templates/hooks/deck_session_start.py:30` —
   `_INT_RE = re.compile(r"^-?(0|[1-9][0-9]*)$")`. The `sync-plugin-assets`
   pre-commit hook propagates it to the three byte-for-byte mirrors.
2. `openclaw-plugin/index.ts:147` — `const INT_RE = /^-?(0|[1-9][0-9]*)$/;`,
   then `cd openclaw-plugin && npm ci && npm run build` so the committed
   `dist/index.js` carries the fix.
3. A regression test that reads `yaml_lite._INT_RE.pattern` and asserts all
   three literals equal it, plus a hook-vs-engine differential on the
   leading-zero cases. Deriving the expectation from the engine (rather than
   hard-coding the pattern a fourth time) is what makes the guard survive the
   next change to the canonical regex.
