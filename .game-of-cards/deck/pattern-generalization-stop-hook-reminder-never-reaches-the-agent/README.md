---
title: pattern-generalization-stop-hook-reminder-never-reaches-the-agent
summary: "The pattern-generalization Stop hook prints its reminder to stdout and returns 0. For a Claude Code Stop hook, exit-0 stdout is shown only to the user in transcript mode — it is NOT injected into the model's context. So the agent never sees the self-assessment prompt and the hook has been inert (for its stated purpose) since it shipped. The sibling SessionStart / UserPromptSubmit hooks use the same print()+return-0 idiom correctly, because those hook types DO inject stdout into context — the Stop hook copied an idiom that does not transfer."
status: open
stage: null
contribution: high
created: "2026-05-26T20:20:14Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] PROCESS: Decision recorded (block-the-stop vs drop-the-hook vs accept-transcript-only) in the body's `## Decision required` section and gate lowered.
  - [ ] TDD: reproduce.py exits zero (the chosen output mechanism is asserted to reach the agent for the block path, or the hook is removed for the drop path).
  - [ ] MECHANICAL: the fix lands in `goc/templates/hooks/pattern_generalization_check.py` and the plugin/consumer mirrors are re-synced (pre-commit `sync-plugin-assets` + `port_skills_to_openclaw` where applicable).
  - [ ] MECHANICAL: AGENTS.md / card-schema or wherever the hook's behavior is documented matches the chosen mechanism.
  - [ ] TDD: `uv run goc validate` passes.
---

# Pattern-generalization Stop hook reminder never reaches the agent

## Location

`goc/templates/hooks/pattern_generalization_check.py:134-137`

```python
    if _had_code_mutation(transcript_path):
        print(REMINDER)

    return 0
```

(The consumer mirror `.claude/hooks/pattern_generalization_check.py`,
`claude-plugin/hooks/...`, and `codex-plugin/hooks/...` carry the same
code; the OpenClaw TS port at `openclaw-plugin/index.ts` does NOT — see
below.)

## What's broken

This is a **Stop** hook (its docstring, line 1: *"Stop hook — prompt
agent to file generalization cards…"*; registered on the `Stop` event).
It emits its reminder with `print(REMINDER)` and then `return 0`.

In Claude Code's hook contract, a hook's behavior on **exit code 0**
differs by event type:

- For **`UserPromptSubmit`** and **`SessionStart`**, stdout *is* added
  to the model's context.
- For **every other event, including `Stop`**, exit-0 stdout is shown
  only to the *user* in transcript mode (Ctrl-R). It is **not** injected
  into the model's context.

To get text in front of the agent from a Stop hook you must either exit
code `2` with the message on **stderr** (which blocks the stop and feeds
stderr back to the model), or emit JSON `{"decision": "block", "reason":
"…"}` (also blocks the stop, `reason` shown to the model). There is no
non-blocking channel from a Stop hook to the model — once the agent has
stopped, there is nothing left to inject into.

So the `REMINDER` string is silently dropped: `_had_code_mutation`
correctly fires on code-mutating turns, but the prompt the agent is
supposed to self-assess against never arrives. The hook has been a
no-op for its stated purpose since it shipped (the feature card
[agent-flags-unfiled-pattern-generalization-cards-before-stop](../agent-flags-unfiled-pattern-generalization-cards-before-stop/),
closed 2026-05-06).

### The idiom was copied from hooks where it works

The two sibling hooks emit the identical way and are **correct**,
because their event types inject stdout into context:

- `goc/templates/hooks/deck_session_start.py` (SessionStart) —
  `print(f"[GoC] Active card(s): …")`. We can see this one working: the
  SessionStart reminder appears injected at the top of every session.
- `goc/templates/hooks/deck_prompt_router.py` (UserPromptSubmit) —
  `print(REMINDER)`.

The Stop hook reused `print()+return 0` from these without accounting
for the event-type difference in the exit-0 stdout contract. The
OpenClaw TS port of the same logic (`openclaw-plugin/index.ts`) instead
calls the host's explicit notify/append-context API, which is why it
does not exhibit the bug — further evidence the Python sibling is the
outlier.

## Empirical evidence

The defect is in the host runtime's routing of exit-0 stdout for Stop
events, which `reproduce.py` cannot exercise without the Claude Code
runtime. Instead the reproducer asserts the *observable code property*
that proves the bug: the hook writes the reminder to **stdout** and
exits **0** — neither the exit-2/stderr nor the JSON-block channel that
a Stop hook needs to reach the model. See `reproduce.py` output pasted
in `log.md` at implementation time.

## Why it matters

The whole point of this hook is to nudge the agent — on code-mutating
turns — to file generalization cards it would otherwise forget (the
failure mode the originating card documents: narrow work ships, the
broader pattern evaporates with the conversation). Because the nudge
never reaches the agent, that failure mode is entirely un-mitigated
while the deck's documentation (and the originating card's DoD item:
*"the agent is expected to file via Skill(create-card) before yielding;
the hook's prompt explicitly says so"*) claims it is handled. Silent
doc/behavior drift on a methodology mechanism.

## Decision required

The defect is certain; the fix has a genuine fork because making the
hook functional reverses a deliberate prior decision. The originating
card's recorded design was **A+B+A**: *"lightweight prompt-only Stop
hook … reminder-only (no stop-block)"*, with reasoning that the low
false-positive cost came precisely from *"no forced action."* But on
Claude Code, "reminder reaches the agent" and "does not block the stop"
are mutually exclusive for a Stop hook. So a human must pick:

1. **Block-the-stop (make it functional).** Switch to exit code `2`
   with `REMINDER` on stderr (or JSON `{"decision":"block","reason":
   REMINDER}`). The existing `stop_hook_active` guard (line 123) already
   prevents an infinite re-block loop. Cost: forces one continuation
   turn on every code-mutating stop — exactly the "forced action" the
   original decision chose to avoid. Benefit: the hook does what its
   card says.
2. **Drop the hook.** Accept that a non-blocking generalization nudge
   cannot be delivered on Claude Code's Stop event, remove the hook and
   its registration, and rely on the UserPromptSubmit router + agent
   discipline instead. Cost: the automated nudge is gone (but it was
   never actually firing).
3. **Accept transcript-only + re-document.** Keep `print()+return 0`,
   but rewrite the hook's docstring and AGENTS/card-schema docs to state
   honestly that this is a *user-facing transcript note*, not an
   agent-facing prompt. Cost: the originating card's intent (agent
   self-assesses) is formally abandoned; lowest churn.

Recommendation: option 1 if the team still wants the automated nudge
(the `stop_hook_active` guard makes the loop safe and the FP cost is one
extra turn), else option 2. Option 3 only if forcing a continuation turn
is judged too costly and the team is content to drop the automation.
