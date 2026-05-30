---
title: pattern-generalization-mutation-detector-skips-tool-result-turns
summary: "`_had_code_mutation` in `pattern_generalization_check.py` walks the transcript backwards and `break`s on the first `role: user` entry that has no `tool_use` blocks, AFTER any assistant entry has been seen. Claude Code wraps every `tool_result` in a `role: user` message, so the loop breaks on the tool_result instead of crossing back through it to the actual `tool_use`. Any turn that ends with an assistant text reply (the typical Edit-then-explain shape) trips the break BEFORE the loop reaches the Edit, and `_had_code_mutation` returns False — the reminder is suppressed. The hook only fires when the LAST entry of the most recent assistant turn is itself a `tool_use` block with no subsequent text reply, which is the minority case. Compounds the already-filed [pattern-generalization-stop-hook-reminder-never-reaches-the-agent](../pattern-generalization-stop-hook-reminder-never-reaches-the-agent/) (channel bug, which incorrectly claims `_had_code_mutation correctly fires on code-mutating turns`): even if the channel is fixed, the detector itself misfires on the common Edit-then-text shape."
status: open
stage: null
contribution: high
created: "2026-05-30T01:39:17Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: Decision recorded in the body's `## Decision required` section (skip-tool-result-user-entries vs other boundary signal) and the gate lowered.
  - [ ] TDD: `reproduce.py` exits zero — both the realistic Edit-then-text shape AND the no-tool-mutation baseline are detected correctly.
  - [ ] MECHANICAL: The fix lands in `goc/templates/hooks/pattern_generalization_check.py` and the plugin/consumer mirrors are re-synced (pre-commit `sync-plugin-assets` regenerates `.claude/hooks/`, `claude-plugin/hooks/`, `codex-plugin/hooks/`).
  - [ ] MECHANICAL: The OpenClaw TS port in `openclaw-plugin/index.ts` is audited for the same misfire and patched if it carries the same boundary logic.
  - [ ] TDD: A regression test in `tests/` pins the realistic Edit-then-text transcript shape to `_had_code_mutation == True`.
---

# pattern-generalization-mutation-detector-skips-tool-result-turns

## Location

`goc/templates/hooks/pattern_generalization_check.py:79-104` — the
`_had_code_mutation` function, specifically the `else` branch's
boundary-break logic:

```python
def _had_code_mutation(transcript_path: str) -> bool:
    """Return True if the most recent assistant turn used a code-mutating tool."""
    path = Path(transcript_path)
    ...
    found_assistant = False
    for line in reversed(lines):
        ...
        tool_names = _extract_tool_names(entry)

        if tool_names:
            found_assistant = True
            for name in tool_names:
                if _is_code_mutating(name, entry):
                    return True
        else:
            # Determine role to know when we've crossed into the prior user turn
            msg = entry.get("message", entry)
            role = msg.get("role") if isinstance(msg, dict) else entry.get("role")
            if role == "user" and found_assistant:
                break
            if role == "assistant":
                found_assistant = True

    return False
```

The four mirrored copies of this file under `.claude/hooks/`,
`claude-plugin/hooks/`, `codex-plugin/hooks/` are byte-synced from the
template; the OpenClaw TS port at `openclaw-plugin/index.ts` is a
hand-port and must be audited separately (the existing card
[pattern-generalization-stop-hook-reminder-never-reaches-the-agent](../pattern-generalization-stop-hook-reminder-never-reaches-the-agent/)
notes the TS port may not carry this exact logic).

## What's broken

Claude Code transcripts use the standard Anthropic message shape:
every `tool_result` content block is wrapped in a `role: user`
message. A realistic Edit-then-explain turn looks like:

```jsonl
{"message":{"role":"user","content":"please fix the bug"}}
{"message":{"role":"assistant","content":[{"type":"tool_use","name":"Edit","input":{...}}]}}
{"message":{"role":"user","content":[{"type":"tool_result","tool_use_id":"x","content":"ok"}]}}
{"message":{"role":"assistant","content":[{"type":"text","text":"Done."}]}}
```

`_extract_tool_names` returns `[]` for ANY user entry (it filters on
`role == "assistant"`), including the tool_result wrapper. The
`reversed` walk therefore proceeds:

1. assistant `text "Done."` → `tool_names = []`. Falls into `else`.
   `role == "assistant"`. `found_assistant = True`. Continue.
2. user `tool_result` → `tool_names = []`. Falls into `else`.
   `role == "user"` AND `found_assistant == True`. **break.**

The loop exits without ever inspecting the earlier `tool_use Edit`.
`_had_code_mutation` returns `False`, and the Stop hook silently
suppresses the `REMINDER`. The comment on line 91 (*"to know when
we've crossed into the prior user turn"*) reveals the design
intent — but every `tool_result` looks exactly like a prior user
turn to this loop.

The hook only correctly fires when the transcript's last entry is
itself the `tool_use` block (no text reply, no trailing
tool_result). That happens when the model emits a code-mutating
tool call as its very last action and then stops without explaining
itself — an unusual shape. The typical "edit, then say what changed"
shape never triggers the reminder.

## Empirical evidence

Two synthetic transcripts run through the unmodified hook (full
script in [`reproduce.py`](reproduce.py)):

```
case A: realistic Edit-then-text shape (Edit → tool_result → text)
  expected: REMINDER on stdout
  actual:   stdout empty, exit 0
  PASS?     False

case B: degenerate shape used by the sibling card's reproduce.py (Edit as final entry)
  expected: REMINDER on stdout
  actual:   REMINDER on stdout, exit 0
  PASS?     True

case C: no-tool baseline (user prompt → text reply)
  expected: stdout empty
  actual:   stdout empty, exit 0
  PASS?     True
```

Case B is what the existing card
`pattern-generalization-stop-hook-reminder-never-reaches-the-agent`'s
`reproduce.py` exercises — it ends the transcript with the Edit
entry, which avoids this defect's trigger entirely and so leaves the
boundary bug invisible. That is why the sibling card's summary
asserts `_had_code_mutation correctly fires on code-mutating turns`
— the assertion is true for case B but false for case A, which is
the shape real sessions actually produce.

## Why it matters

The pattern-generalization Stop hook's whole job is to nudge the
agent to file a generalization card after a code-mutating turn.
Stop hooks fire when the assistant has decided to stop — which in
practice is almost always *after* the assistant has spoken a final
text reply explaining the edits it just made. That is exactly the
shape this loop misclassifies as "no code mutation."

Reachability path: every assistant turn in Claude Code that includes
at least one `tool_use` followed by a `tool_result` followed by a
final `text` block (i.e., "edit, observe result, report") flows
through this loop and trips the break. The Stop hook then fires
with `_had_code_mutation == False`, the `REMINDER` is suppressed,
and the agent never gets the prompt to self-assess for
generalization. The hook has been silently inert on the most common
real-session shape since it shipped.

Combined with the already-filed channel defect
([pattern-generalization-stop-hook-reminder-never-reaches-the-agent](../pattern-generalization-stop-hook-reminder-never-reaches-the-agent/)),
the hook is effectively non-functional: even if the output channel
is fixed to actually reach the model, the detector itself only
fires on a small subset of turns. Both bugs must be fixed for the
feature to deliver its stated value.

## Decision required

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

## Fix

Per the decision above. Either option lands in the source-of-truth
template; the byte-mirror sync (`scripts/sync_plugin_assets.py`)
propagates the change to `.claude/hooks/`, `claude-plugin/hooks/`,
and `codex-plugin/hooks/` on the next pre-commit run. The OpenClaw
TS port at `openclaw-plugin/index.ts` is hand-maintained and must
be audited for the same boundary defect and patched if it carries
the same logic.

A regression test should land alongside the fix in `tests/`,
exercising both the realistic Edit-then-text shape (must return
True) and the no-tool baseline (must return False). The existing
sibling card's `reproduce.py` covers only the degenerate Edit-as-
last-entry shape and so does not protect against re-introduction
of this defect — the new test must use the realistic transcript
shape this card's `reproduce.py` ships.
