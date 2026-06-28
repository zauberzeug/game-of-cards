## 2026-05-30T01:39:17Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Two credible fix paths:

**Option A — Skip user entries with only `tool_result` content.**
Distinguish "real user prompt" from "tool_result wrapper" inside the
boundary check. A user entry whose content is a list and every block
is `{"type": "tool_result", ...}` is a tool_result wrapper and must
not break the loop. Concretely:

```python
def _is_tool_result_only(entry: dict) -> bool:
    msg = entry.get("message", entry)
    content = msg.get("content") if isinstance(msg, dict) else None
    if not isinstance(content, list) or not content:
        return False
    return all(
        isinstance(b, dict) and b.get("type") == "tool_result"
        for b in content
    )
```

Then in the `else` branch:

```python
if role == "user" and found_assistant and not _is_tool_result_only(entry):
    break
```

Pros: minimal change, matches the documented intent (cross into the
prior user *prompt*, not a tool_result echo). Pros: still recognizes
the boundary cleanly when a new user prompt arrives.

Cons: relies on content-block shape inspection. If Claude Code ever
changes how it stores tool_results in the transcript (e.g., flattening
content or moving to a top-level `tool_results` field), this check
silently degrades.

**Option B — Use a turn-level marker, not the user-role boundary.**
Walk forward from the start of the most recent assistant turn rather
than backward from the tail. The "start of the most recent assistant
turn" is the first non-tool-result user entry encountered scanning
backward. That requires a two-pass walk: scan back to find the user
prompt, then scan forward from there checking every assistant entry
for code-mutating tools.

Pros: independent of tool_result encoding details — only the user
prompt boundary matters.

Cons: larger refactor; ties to the meaning of "turn" more
explicitly, which makes the loop harder to reason about than the
current "walk back, return on first hit" shape.

The decision is **A vs B** — they encode the same boundary, just
identified by different signals. Project preference between
"defensive shape inspection" and "explicit turn boundary" is the
call.

Default recommendation: **Option A**. The fix is one helper plus
one extra condition; the cost of degradation if Claude Code changes
its transcript shape is identical to the existing risk that
`_extract_tool_names` already carries (it reads `type == "tool_use"`
from the same content-block schema). If that schema changes, both
sites break together — there is no extra surface area introduced.


## 2026-05-30T14:00:10Z: decision recorded

Option A: add an _is_tool_result_only() helper and only break the backward walk on a real user prompt — a user entry whose content is a non-empty list of all tool_result blocks must not be treated as the prior-turn boundary — minimal change (one helper plus one condition) that matches the documented intent of crossing into the prior user prompt rather than a tool_result echo; the transcript-shape degradation risk is identical to what _extract_tool_names already carries, so no new surface area is introduced. Gate decision → none.
