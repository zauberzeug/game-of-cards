---
title: session-start-hook-over-coerces-quoted-waiting-scalars-to-absent
summary: "The SessionStart hook strips outer quotes before its null/bool/int coercion check, so a quoted `waiting_on: \"true\"`/`\"42\"`/`\"null\"` (and `waiting_until: \"null\"`) — which the engine keeps as a live string reason and treats as impeded — is wrongly resolved to absent and the card is announced as resumable. Opposite-direction regression of the just-closed bool/int coercion fix, whose tests only cover unquoted forms."
status: active
stage: null
contribution: medium
created: "2026-06-22T09:20:54Z"
closed_at: null
human_gate: none
advances:
  - session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
advanced_by: []
tags: [bug, infra, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `deck/<title>/reproduce.py` exits zero — the hook agrees with `engine.waiting_impedes` for quoted `waiting_on: "true"`/`"false"`/`"42"`/`"null"` and `waiting_until: "null"` (all currently DIVERGE).
  - [ ] TDD: a regression test in `tests/test_session_start_hook.py` asserts a quoted `waiting_on: "true"` and a quoted `waiting_until: "null"` card is reported impeded by the hook (matching the engine), and that unquoted `waiting_on: true`/`42`/`null` still resolve to absent.
  - [ ] MECHANICAL: `_card_waiting_on` and `_scalar_or_none` in `goc/templates/hooks/deck_session_start.py` apply null/bool/int coercion only to *unquoted* tokens; the OpenClaw TS port (`waitingOnScalar` / `scalarOrEmpty` in `openclaw-plugin/index.ts`) mirrors the change.
  - [ ] PROCESS: re-sync plugin mirrors (`python scripts/sync_plugin_assets.py`) and re-port OpenClaw skills if needed; `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass.
worker: {who: "claude[bot]", where: main}
---

# Session-start hook over-coerces quoted `waiting_on` / `waiting_until` scalars to absent

## Location

`goc/templates/hooks/deck_session_start.py` — `_frontmatter_tail`
(line 33), `_scalar_or_none` (line 54), `_card_waiting_on`
(lines 96–124). Mirror with the identical bug: `openclaw-plugin/index.ts`
— `frontmatterTail` / `scalarOrEmpty` (lines 170–179) and
`waitingOnScalar` (lines 181–192).

## What's broken

The SessionStart hook re-implements `engine.waiting_impedes` so it can
run dependency-free. To match the engine's `Card.waiting_on`
(`return v if isinstance(v, str) and v else None`, `engine.py:692-695`),
the just-closed card
[`session-start-hook-treats-coerced-bool-or-int-waiting-on-as-impediment`](../session-start-hook-treats-coerced-bool-or-int-waiting-on-as-impediment/)
added a coercion guard so a token the yaml-lite parser would turn into a
bool/int reads as absent here too:

```python
# _card_waiting_on, lines 114-123
if line.startswith("waiting_on:"):
    reason = _scalar_or_none(line)          # <-- already quote-stripped
    if reason is not None and (
        reason in _TRUE_SET
        or reason in _FALSE_SET
        or _INT_RE.match(reason)
    ):
        return None
    return reason
```

But `_scalar_or_none` → `_frontmatter_tail` strips outer quotes
(`.strip().strip('"').strip("'")`, line 51) **before** the coercion
check runs. The yaml-lite parser only coerces *unquoted* tokens: an
unquoted `true` becomes `bool` (dropped by the engine's `isinstance`
guard), but a **quoted** `"true"` is parsed by `_parse_double_quoted`
(`_vendor/yaml_lite.py:304-305`) and stays the live string `"true"` —
which the engine keeps as a reason and treats as impeded.

By coercing on the quote-stripped value, the hook resolves a quoted
`waiting_on: "true"` (and `"false"`, `"42"`, `"null"`) to None and
reports the card resumable, while the engine reports it impeded. The
same strip-before-coerce flaw in `_scalar_or_none`'s `_NULL_SET` branch
mis-handles a quoted `waiting_until: "null"`: the engine keeps the raw
`"null"` token → `_waiting_until_instant` finds it unparseable → its
backstop impedes; the hook strips to `null`, resolves to absent, and
reports resumable.

## Empirical evidence

`reproduce.py` output on a clean checkout (defect present):

```
waiting_on: "true"   | engine impedes=True  reason='true'   | hook impedes=False | DIVERGE
waiting_on: "false"  | engine impedes=True  reason='false'  | hook impedes=False | DIVERGE
waiting_on: "42"     | engine impedes=True  reason='42'     | hook impedes=False | DIVERGE
waiting_on: 'yes'    | engine impedes=True  reason='yes'    | hook impedes=False | DIVERGE
waiting_on: "null"   | engine impedes=True  reason='null'   | hook impedes=False | DIVERGE
waiting_until: "null"| engine impedes=True  until='null'    | hook impedes=False | DIVERGE
```

## Why it matters

This is the opposite-direction regression created by closing the
bool/int coercion card: that fix and its test only exercise the
**unquoted** forms, so the quoted forms slipped through. The
reachability path: the frontmatter emitter
(`engine._yaml_inline`, `engine.py:229-239`) does not currently quote
these enum tokens, so the divergence is reached today only by a
hand-edited or one-shot-authored card. But the hook exists precisely to
read pre-validate / hand-edited decks (its docstring: "runs from any
working tree shape"), and the engine's own contract treats a quoted
scalar as a live reason. A card a human quotes to silence YAML's
bool-coercion (`waiting_on: "true"` meaning a literal reason string)
would be hidden from the queue by the engine but announced as resumable
by the session-start reminder — the exact "agent cannot resume" /
"agent can resume" disagreement the family card
[`session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting`](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/)
catalogs.

Distinct from the closed
[`deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers`](../deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers/):
that card aligned *which* readers strip quotes; this one is the
quote-strip × coercion interaction in the two readers that already do.

## Fix

Make the null/bool/int coercion quote-aware — apply it only when the
authored token carried no surrounding quotes (a quoted scalar stays a
live `str` in yaml-lite, which the engine keeps as a reason):

- Factor a `_comment_free_tail(line)` helper that does the inline-comment
  strip and whitespace trim but **preserves quotes**; have
  `_frontmatter_tail` delegate to it then strip quotes (no behavior
  change for `_card_status` / `_card_human_gate`).
- Rewrite `_card_waiting_on` to read the comment-free tail, detect a
  leading `"`/`'`, and skip null/bool/int coercion when quoted.
- Make `_scalar_or_none` skip the `_NULL_SET` coercion when the token
  was quoted (fixes `waiting_until: "null"`).
- Mirror all three in `openclaw-plugin/index.ts`.
