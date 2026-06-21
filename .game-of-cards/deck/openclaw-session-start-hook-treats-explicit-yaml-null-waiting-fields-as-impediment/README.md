---
title: openclaw-session-start-hook-treats-explicit-yaml-null-waiting-fields-as-impediment
summary: "The OpenClaw `index.ts` session-start reader does not resolve explicit YAML null literals (`null` / `Null` / `NULL` / `~`) on the `waiting_on` / `waiting_until` fields, so `waiting_on: null` on an active card survives as the truthy string `\"null\"` and `isImpeded` reports the card as impeded — announcing a fully-resumable card as `agent cannot resume.`. The Python hook resolves these literals to absent via `_NULL_SET`; the TS port never got that translation. New instance of the openclaw-hook-predicate drift family."
status: active
stage: null
contribution: medium
created: "2026-06-21T10:11:56Z"
closed_at: null
human_gate: none
advances:
  - openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: a null-literal cell is added to `tests/test_openclaw_session_start_hook.py` (extracts the TS reader path / `isImpeded` and asserts `waiting_on: null` / `~` / `Null` / `NULL` on an active card reads as NOT impeded), red before the fix.
  - [ ] TDD: `reproduce.py` exits zero (Python hook and OpenClaw TS agree `impeded=False` for every explicit-null literal).
  - [ ] MECHANICAL: `openclaw-plugin/index.ts` resolves explicit YAML null literals to "absent" for the `waiting_on` / `waiting_until` frontmatter reads, mirroring `goc._vendor.yaml_lite._NULL_SET` and the Python hook's `_scalar_or_none`.
  - [ ] PROCESS: the meta-fix umbrella `openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting` lists this card under `advanced_by` (edge wired both ways) and its body's drift-cell enumeration is updated to include the explicit-null cell.
worker: {who: "claude[bot]", where: main}
---

# OpenClaw session-start hook treats explicit YAML null waiting fields as impediment

## Location

`openclaw-plugin/index.ts:253-256` (the `findActiveCards` frontmatter reader)
and the downstream `isImpeded` at `index.ts:194-218`.

## What's broken

The OpenClaw session-start hook reads `waiting_on` / `waiting_until` from each
card's frontmatter with no YAML-null resolution:

```typescript
} else if (line.startsWith("waiting_on:")) {
  waitingOn = stripQuotes(frontmatterTail(line));
} else if (line.startsWith("waiting_until:")) {
  waitingUntil = stripQuotes(frontmatterTail(line));
}
```

`stripQuotes` only strips surrounding quotes (`value.replace(/^["']|["']$/g, "")`);
it does not resolve the explicit YAML null literals `null` / `Null` / `NULL` / `~`
to "absent". So `waiting_on: null` yields the **non-empty** string `"null"`, and
`isImpeded("null", "", now)` takes the `if (waitingOn !== "")` branch and returns
`true`. The active card is then announced at session start as impeded —
`Impeded active card(s) (waiting_on): … — agent cannot resume.` — even though it
carries no impediment.

The Python hook gets this right. `goc/templates/hooks/deck_session_start.py`
mirrors `yaml_lite._NULL_SET` explicitly:

```python
# Mirrors `goc._vendor.yaml_lite._NULL_SET`: explicit YAML null literals that
# resolve to None, so `waiting_on: null` / `~` reads as absent, not a reason.
_NULL_SET = frozenset(("null", "Null", "NULL", "~"))

def _scalar_or_none(line: str) -> str | None:
    tail = _frontmatter_tail(line)
    return tail if tail and tail not in _NULL_SET else None
```

The TS port never received the equivalent translation — this is exactly the
"reimplements engine logic and keeps drifting" shape the family meta-fix tracks.

## Empirical evidence

`reproduce.py` extracts the real TS reader path (`stripQuotes` ∘ `frontmatterTail`)
and `isImpeded` from `index.ts`, runs them under Node, and compares each null
literal to the Python hook's `_is_impeded`:

```
Active card with `waiting_on: <literal>` — is it announced as impeded?

 literal |  Python hook |  OpenClaw TS | verdict
------------------------------------------------------
    null |        False |         True | DIVERGES (bug)
    Null |        False |         True | DIVERGES (bug)
    NULL |        False |         True | DIVERGES (bug)
       ~ |        False |         True | DIVERGES (bug)

DEFECT CONFIRMED: 4/4 explicit-null literals impede on the OpenClaw host but not under the Python hook.
Expected after fix: Python and OpenClaw TS agree (impeded=False) for every explicit-null literal.
```

`waiting_until: null` is wrong the same way: `parseWaitingUntil("null")` returns
`null` → `untilUnparseable = true` → the `until_unparseable` backstop returns
`true`, treating an absent field as a malformed one.

## Why it matters

These read-time hooks run **before** `goc validate` — they are the last line of
defense on hand-edited / pre-validate decks, which is precisely why the Python
hook bothers to resolve null literals at all. The engine never *emits*
`waiting_on: null` (`goc wait --clear` does `fm.pop("waiting_on", None)` at
`engine.py:4999`, removing the key), so the reachability path is a **hand-edited
card**: a human blanking the field by writing `waiting_on: null` or `~` instead
of deleting the line — a natural edit, and the same shape the closed Python
sibling [session-start-hook-treats-explicit-yaml-null-waiting-fields-as-impediment](../session-start-hook-treats-explicit-yaml-null-waiting-fields-as-impediment/)
already fixed on the Python side. On that card's fix, the OpenClaw TS port was
explicitly deferred to the family meta-fix
[openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/),
but no concrete instance card was ever filed for the cell — this card closes
that gap. The symptom: the OpenClaw host falsely tells the agent a resumable
card "cannot resume," diverging from every other host (Claude, Codex, pipx) for
the same deck.

## Fix

Mirror `_NULL_SET` resolution in the TS frontmatter reader. Add the literal set
and route the two waiting reads through a null-resolving helper, e.g.:

```typescript
const NULL_LITERALS = new Set(["null", "Null", "NULL", "~"]);

function scalarOrEmpty(line: string): string {
  const tail = stripQuotes(frontmatterTail(line));
  return NULL_LITERALS.has(tail) ? "" : tail;
}
```

then use `scalarOrEmpty(line)` for both `waiting_on:` and `waiting_until:` at
`index.ts:253-256`. This keeps `isImpeded`'s `!== ""` contract intact (an
explicit-null field reads as absent, exactly like a missing line).

`index.ts` is a hand-ported file (not auto-synced), so the edit is applied
directly and reviewed by hand, matching how the prior `index.ts` drift fixes
landed. **Do NOT apply the fix in this filing pass** — it is filed as a documented
instance of the drift family; the worker that pulls it lands the fix + the
regression cell.
