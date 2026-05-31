---
title: deck-session-start-hook-misreads-frontmatter-fields-with-inline-yaml-comments
summary: "The SessionStart hook's four frontmatter readers (`_card_status`, `_card_human_gate`, `_card_waiting_on`, `_card_waiting_until`) split on the first colon and `.strip()` the tail, but never strip a trailing YAML inline `# comment`. A card whose author added an explanatory inline comment (`status: active # resumable note`) gets misclassified: the equality check `_card_status(readme) != 'active'` sees `'active # resumable note'` and silently drops the card from the session-start briefing. The same misread misclassifies `human_gate`, `waiting_on`, and `waiting_until`. Sibling to the closed [deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers](../deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers/), which fixed the quote-stripping asymmetry but didn't touch the comment case."
status: done
stage: null
contribution: low
created: "2026-05-31T01:16:45Z"
closed_at: "2026-05-31T01:20:38Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — all four readers strip inline comments and return the canonical bare value
  - [x] TDD: a regression test in `tests/` covers each of the four readers receiving a value with a trailing ` # comment`, asserting the comment-free tail is returned
  - [x] MECHANICAL: helper added to `goc/templates/hooks/deck_session_start.py`; all four readers route their tails through it
  - [x] MECHANICAL: OpenClaw TypeScript port (`openclaw-plugin/index.ts`) gets the same fix in `frontmatterTail` so the host-neutral behavior stays aligned
  - [x] PROCESS: plugin mirrors re-synced (`python3 scripts/sync_plugin_assets.py`)
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` both pass
---

# `deck_session_start.py` misreads frontmatter fields with inline YAML comments

## Location

`goc/templates/hooks/deck_session_start.py:33, 48, 64, 80` — four
frontmatter readers each call
`line.split(":", 1)[1].strip().strip('"').strip("'")` and return the
result without stripping a YAML inline `# comment` suffix.

Parallel defect in the TypeScript port:
`openclaw-plugin/index.ts:134-143` (`frontmatterTail`) — same shape,
mirroring the Python hook.

## What's broken

YAML allows an inline `# comment` after a scalar value, terminated by
the end of line: `status: active # resumable note` is well-formed YAML
and parses to the string `"active"`. The four readers' line-by-line
tail extraction does not honor this:

```python
# line 32-33 — _card_status
if line.startswith("status:"):
    return line.split(":", 1)[1].strip().strip('"').strip("'")
```

For the input `status: active # resumable note`, the tail is
`" active # resumable note"`; `.strip()` returns
`"active # resumable note"`; the quote-strips are no-ops. The check at
line 191 (`if _card_status(readme) != "active": continue`) compares
`"active # resumable note" != "active"` → `True`, so the card is
silently skipped from the SessionStart briefing.

The same misread fires on `human_gate` (line 47-49), `waiting_on`
(line 62-65), and `waiting_until` (line 78-81). The `waiting_until`
case is particularly bad: a value like `2026-06-05 # deferred` fails
the `_ISO_DATE_RE` shape check, so `_parse_waiting_until` returns
`None` and `_is_impeded` treats the value as `until_unparseable`,
which collapses to the open-ended-wait branch.

## Empirical evidence

```
$ uv run python .game-of-cards/deck/deck-session-start-hook-misreads-frontmatter-fields-with-inline-yaml-comments/reproduce.py
status raw   = 'active # resumable note'   expected 'active'
human_gate   = 'decision # parked'         expected 'decision'
waiting_on   = 'external # see GH-123'     expected 'external'
waiting_until= '2026-06-05 # deferred'     expected '2026-06-05'
DEFECT: all four readers leak the inline YAML comment into the value
```

## Why it matters

**Reachability.** The engine's `emit_frontmatter` never produces
inline comments, so the engine-emitted card files stay safe. The
realistic input paths are:

1. **Hand-edit.** An author refining a card adds an inline comment to
   document why a field is set the way it is — a natural YAML
   convention, encouraged by every YAML style guide.
2. **Migration / import tooling.** A future migration script (or a
   third-party importer for an external tracker) that annotates
   migrated fields with `# migrated from X`.
3. **Schema rev.** A future schema change that documents the chosen
   enum value inline — analogous to comments on Python `Literal` types.

The SessionStart hook briefs the agent on which cards are active at
the start of every session. Silent misclassification of active cards
means an agent loses context for in-progress work and may start
duplicate work, or — when the misread flips an impeded card into the
resumable list — try to resume a card whose `waiting_on` overlay
should have suppressed it.

Latent, but mechanical to fix; same fix surface as the closed sibling
[deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers](../deck-session-start-hook-strips-quotes-asymmetrically-across-frontmatter-readers/).

## Fix

Add a private helper inside `deck_session_start.py` that strips a YAML
inline comment from a bare scalar tail, then route the four readers
through it. YAML semantics: a `#` ends the value only when preceded by
whitespace (or at the very start) — `foo#bar` is a single bare scalar,
`foo #bar` is the bare scalar `foo` followed by the comment ` #bar`.

```python
def _strip_inline_comment(s: str) -> str:
    """Strip a trailing YAML inline `# comment` from a bare scalar tail.

    Matches the YAML 1.1/1.2 rule: a `#` terminates a bare scalar only
    when preceded by whitespace (or at the very start of the value).
    """
    i = 0
    while i < len(s):
        if s[i] == "#" and (i == 0 or s[i - 1].isspace()):
            return s[:i].rstrip()
        i += 1
    return s
```

Each reader then becomes `_strip_inline_comment(line.split(":",
1)[1]).strip().strip('"').strip("'")` — apply comment strip on the raw
tail before the outer whitespace/quote strips.

Parallel TS edit in `openclaw-plugin/index.ts`: extend
`frontmatterTail` to perform the same comment-strip after the colon
split.

## DoD

See frontmatter. Plugin mirror sync runs after the source-of-truth
edit so the Claude / Codex plugin payloads stay byte-for-byte aligned
with `goc/templates/hooks/deck_session_start.py`.
