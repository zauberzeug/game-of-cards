---
title: session-start-hook-comment-stripper-truncates-quoted-scalar-with-internal-hash
summary: "The SessionStart hook's `_comment_free_tail` strips inline `#` comments without quote-awareness, so a quoted frontmatter scalar containing an internal `# ` (e.g. `waiting_until: \"2020-01-01 # note\"`) is truncated at the `#`, diverging from the engine's quote-aware `_strip_comment`. An elapsed quoted-with-comment `waiting_until` then reads as resumable in the hook while the engine treats it as impeded. 11th instance of the session-start-hook reimplements-engine drift family."
status: done
stage: null
contribution: medium
created: "2026-06-23T07:52:19Z"
closed_at: "2026-06-23T07:59:32Z"
human_gate: none
advances:
  - session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: a regression test asserts the four hook readers (`_card_status`, `_card_human_gate`, `_card_waiting_on`, `_card_waiting_until`) keep a `#` that sits *inside* a quoted scalar, matching `yaml_lite.safe_load` for the same line
  - [x] TDD: a regression test asserts `_is_impeded` agrees with `engine.waiting_impedes` for a card whose `waiting_until` is a quoted past date carrying an inline comment (engine impedes; hook must impede too)
  - [x] TDD: existing inline-comment tests (comment outside quotes, bare-value `#`) still pass — no regression
  - [x] MECHANICAL: `_comment_free_tail` in `goc/templates/hooks/deck_session_start.py` is made quote-aware, mirroring `goc/_vendor/yaml_lite.py::_strip_comment`; plugin/dogfood mirrors re-synced by pre-commit
  - [x] reproduce.py exits zero (the divergence no longer fires)
worker: {who: "claude[bot]", where: main}
---

# SessionStart hook truncates a quoted scalar at an internal `#`

## Location

`goc/templates/hooks/deck_session_start.py:46-53` — `_comment_free_tail`.

## What's broken

`_comment_free_tail` backs all four frontmatter readers in the hook
(`_card_status`, `_card_human_gate`, `_card_waiting_on`, and — via
`_frontmatter_tail` / `_scalar_or_none` — `_card_waiting_until`). It strips
an inline YAML `# comment` with a naive left-to-right scan that has **no
quote awareness**:

```python
tail = line.split(":", 1)[1]
i = 0
while i < len(tail):
    if tail[i] == "#" and (i == 0 or tail[i - 1].isspace()):
        tail = tail[:i]
        break
    i += 1
return tail.strip()
```

Its docstring claims it "Mirrors the YAML 1.1/1.2 rule for inline comments."
But YAML only honours a `#` as a comment when it sits **outside** a quoted
scalar. The engine's vendored parser implements exactly that — see
`goc/_vendor/yaml_lite.py:450-485` (`_strip_comment`), which tracks quote
state for a value that starts with a quote and treats a `#` inside the quotes
as content:

```python
quoted = text[:1] in ('"', "'")
...
elif (quoted or flow) and c in ('"', "'"):
    in_q = c
elif c == "#" and depth == 0 and i > 0 and text[i - 1] in (" ", "\t"):
    return text[:i].rstrip()
```

The hook's helper does the comment scan on the raw tail with no quote
tracking, so a `#` *inside* the quotes is amputated. The closed instance
[deck-session-start-hook-misreads-frontmatter-fields-with-inline-yaml-comments](../deck-session-start-hook-misreads-frontmatter-fields-with-inline-yaml-comments/)
added this stripper, but its only quoted test
(`test_quoted_then_comment_unwraps_to_inner_value`) covers a comment
*outside* the closing quote (`"active" # note`) — never a `#` *inside* the
quotes.

## Empirical evidence

Before the fix the hook truncated each quoted scalar at the internal `#`,
diverging from the engine and reporting an engine-impeded card as resumable.
After making `_comment_free_tail` quote-aware, `reproduce.py` exits zero:

```
$ uv run python deck/session-start-hook-comment-stripper-truncates-quoted-scalar-with-internal-hash/reproduce.py

scalar-parse divergence (hook _frontmatter_tail vs engine yaml_lite.safe_load):
  'waiting_on: "external # waiting on PR review"'
    engine: 'external # waiting on PR review'
    hook  : 'external # waiting on PR review'
  'status: "done # closed early"'
    engine: 'done # closed early'
    hook  : 'done # closed early'
  'human_gate: "decision # needs sign-off"'
    engine: 'decision # needs sign-off'
    hook  : 'decision # needs sign-off'

impede-decision divergence (hook _is_impeded vs engine waiting_impedes):
  card: status=active, waiting_until="2020-01-01 # deferred, see note"
    engine waiting_impedes : True   (date is unparseable -> backstop hides card)
    hook   _is_impeded     : True  (truncated to '2020-01-01' -> elapsed -> resumable)

PASS: hook readers match the engine for quoted scalars with internal '#'.
```

## Why it matters

The hook runs at every session start (`deck_session_start.py::main`) and
classifies each active card as **resumable** / **parked** / **impeded**, then
prints a one-line primer telling the agent which active cards to resume. Its
helpers exist precisely to mirror the engine so that primer matches the
engine's queue view.

The reachability path: a hand-edited / pre-`goc validate` card — exactly the
shape the hook's own docstrings repeatedly say they must handle ("err on the
side of hiding pre-validate / hand-edited decks") — with a quoted
`waiting_until` carrying an inline note. The engine parses the quoted string
whole, finds it is not a bare ISO date, and applies its `until_unparseable`
backstop → the card is impeded (hidden from queues). The hook truncates the
quoted value at the `#`, parses the leading date, sees it elapsed, and reports
the card **resumable** — so the session primer invites the agent to resume a
card the engine considers hidden. The quoted `status` / `human_gate` cases are
latent today (those fields are enum-controlled and the truncated prefix lands
in the same classification bucket), but they are the same defect and the fix
closes them too.

This is the **11th instance** of the catalogued drift family
[session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/)
— the hook hand-reimplements engine parsing and drifts one bug at a time. The
architectural parity guard tracked by that (decision-gated) meta-fix is the
systemic fix; this card is the concrete point fix, matching how the prior ten
instances were resolved.

The identical defect exists in the OpenClaw TypeScript port
(`openclaw-plugin/index.ts::frontmatterTail`); that drift family is tracked
separately by
[openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/),
so it is out of scope for this single-site Python fix.

## Fix (applied)

`_comment_free_tail` in `goc/templates/hooks/deck_session_start.py` is now
quote-aware, mirroring `yaml_lite._strip_comment`'s quoted-scalar branch: it
trims leading whitespace, returns `""` for a leading-`#` line, and then scans
with quote tracking — when the value starts with a quote it enters quote mode
on the opening quote and suppresses comment detection until the matching close,
honouring the `\` escape inside double quotes. A `#` is only treated as a
comment when it is outside the quotes and preceded by a space/tab (matching the
engine's exact `in (" ", "\t")` rule). Quotes stay preserved (the helper's
existing contract; `_frontmatter_tail` / `_scalar_or_none` strip them
downstream). Flow-collection handling is intentionally omitted — these four
readers only touch scalar enum/date fields, never flow collections.

The fix lands in the source template; the pre-commit sync regenerated the
`.claude`, `claude-plugin`, and `codex-plugin` mirrors. The OpenClaw TS port
(`frontmatterTail`) carries the same defect but is out of scope here — tracked
by [openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/).
