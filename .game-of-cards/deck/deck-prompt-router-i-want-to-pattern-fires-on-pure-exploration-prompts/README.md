---
title: deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts
summary: "The UserPromptSubmit hook's WORK_INITIATING regex `\\bi\\s+(want|need)\\s+(to|a|an|the|this)\\b` and its sibling `\\bwe\\s+(need|should|want)\\s+to\\b` match every prompt that begins with `I want to …` / `we need to …`, including pure exploration like `I want to understand X` or `we need to investigate Y`. The reminder is then injected because line 73's precedence rule (`exploration-or-tooling AND NOT work`) only suppresses the reminder when no work pattern fires at all — so a work match always wins over an exploration match, contradicting the docstring's `Silent for pure exploration / explanation` contract."
status: open
stage: null
contribution: medium
created: "2026-05-30T02:11:36Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — none of the four pure-exploration prompts (`I want to understand …`, `I want to know …`, `I want to learn about …`, `we need to investigate …`) print the GoC reminder.
  - [ ] TDD: the closed-card canonical work examples (`rename the button to Export`, `add a CSV export`, `fix the auth bug`) STILL print the reminder — the fix must not regress `prompt-hook-misses-rename-work-requests`.
  - [ ] PROCESS: decision recorded in `## Decision required` — which fix path (narrow the `i (want|need) to` / `we (need|should|want) to` regex to specific work verbs, OR flip the precedence so exploration suppresses work, OR add `understand|investigate|know|learn|see` to EXPLORATION). Record reasoning in log.md.
  - [ ] MECHANICAL: `python scripts/sync_plugin_assets.py --check` clean (the hook file ships in three plugin payloads + the `.claude/hooks/` dogfood copy).
  - [ ] MECHANICAL: `uv run goc validate` clean.
---

# `deck_prompt_router` fires the GoC reminder on pure-exploration prompts

## Location

- `goc/templates/hooks/deck_prompt_router.py:16-26` — `WORK_INITIATING`
  patterns. Items 4 and 5 are the offenders:

  ```python
  WORK_INITIATING = [
      r"\blet'?s\s+(do|build|implement|make|add|create|fix|introduce|write|refactor)\b",
      r"\b(implement|build|introduce|refactor)\s+\w",
      r"\b(fix|add|create|write)\s+(a|an|the|this|that|some)\b",
      r"\bi\s+(want|need)\s+(to|a|an|the|this)\b",          # ← matches "I want to <anything>"
      r"\bwe\s+(need|should|want)\s+to\b",                  # ← matches "we need to <anything>"
      r"\bcan\s+you\s+(add|fix|build|create|implement|introduce|write)\b",
      r"\bplease\s+(add|fix|build|create|implement|introduce|write)\b",
      r"\bmake\s+it\s+(work|do|so|happen)\b",
      r"\bship\s+(it|this|the)\b",
  ]
  ```

- `goc/templates/hooks/deck_prompt_router.py:70-77` — precedence rule:

  ```python
  has_work = any(re.search(p, prompt) for p in WORK_INITIATING)
  has_exploration = any(re.search(p, prompt) for p in EXPLORATION)
  has_tooling = any(re.search(p, prompt) for p in TOOLING)
  if (has_exploration or has_tooling) and not has_work:
      return 0
  if has_work:
      print(REMINDER)
  return 0
  ```

  Exploration only suppresses the reminder when **no** work pattern fires.
  Any work match wins.

## What's broken

The hook's stated contract (module docstring, lines 1-8) is:

> Silent for pure exploration / explanation / one-shot tooling — those
> don't need cards. The reminder is opt-in (matched), not blanket.

But the `i (want|need) (to|a|an|the|this)` and `we (need|should|want) to`
patterns match purely exploratory prompts because the verb that follows
"to" is not constrained:

- "I want to **understand** how authentication works in this codebase"
- "I want to **know** what happens when a card has no DoD"
- "I want to **learn** about the deck design"
- "we need to **investigate** why the parser drops blank lines"

None of these are work-initiating. The user is asking for an
explanation. But all four trip `WORK_INITIATING[3]` or `WORK_INITIATING[4]`,
and the precedence rule at line 73 lets work always win, so the REMINDER
fires.

The REMINDER text (lines 47-58) tells the agent definitively:

> The user's prompt above is a card request. Run the GoC pipeline
> SILENTLY: … 4. Implement the work.

That instruction is wrong for an exploratory question. A diligent agent
that takes the hook at its word will scaffold a card and try to
"implement the work" on a prompt the user meant as a question.

Compounding: the second WORK pattern (`r"\b(implement|build|introduce|refactor)\s+\w"`)
also matches the exploration phrase **"explain how to implement an auth
flow"** — has_work=True, has_exploration=True ("explain"), and line 73's
condition still resolves to False. So even prompts whose first word is an
explicit exploration verb get the work reminder.

## Empirical evidence

`uv run python .game-of-cards/deck/deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts/reproduce.py`:

```text
FIRE: i want to understand how authentication works in this codebase
FIRE: we need to investigate why the parser drops blank lines
FIRE: i want to know what happens when a card has no DoD
silent: we should review the recent commits
FIRE: I want to learn about the deck design
FIRE: explain how to implement an auth flow
```

Five of six pure-exploration prompts fire the reminder. (The one silent
case lacks an "I want/need" or "we need/should/want to" opener — it uses
"we should review", which doesn't match `we (need|should|want) to`.)

## Why it matters

The hook runs on every UserPromptSubmit event for plugin-mode and
local-skills Claude installs (registered in `goc/templates/agents/claude/manifest.json`
and `claude-plugin/hooks/hooks.json`). False positives don't just inject
a stray system message — the REMINDER's literal text instructs the agent
to "Run the GoC pipeline SILENTLY … Implement the work." A user who asks
"I want to understand the auth flow" can plausibly trigger a card-filing
detour instead of an explanation.

Reachability: every plugin-payload and dogfood Claude install runs this
hook on every prompt; an `I want to` / `we need to` opener is one of the
most common phrasings in conversational coding sessions. The previous
related card `prompt-hook-misses-rename-work-requests` (done 2026-05-05)
fixed the OPPOSITE failure mode (work prompts not matching). This card is
that fix's mirror: work patterns over-matching exploration.

## Decision required

Three credible fix paths; pick one.

1. **Narrow the regex.** Require the verb after `(to|a|an|the|this)` to
   come from a work-verb whitelist (`add|fix|build|create|write|implement|
   refactor|introduce|rename|update|change|remove|delete|extract`). Tightest
   match, but every new work verb requires a regex edit (the same kind of
   miss that motivated `prompt-hook-misses-rename-work-requests`).

2. **Flip the precedence.** Change line 73 to
   `if has_exploration or has_tooling: return 0` — exploration always
   suppresses, even when a work pattern co-fires. Risk: prompts that
   genuinely mix exploration and work ("explain X, then implement Y")
   would go silent.

3. **Expand EXPLORATION.** Add `understand|investigate|know|learn|see|read`
   to the EXPLORATION list AND keep the current precedence. The
   exploration verbs would catch most of the false positives without
   tightening WORK_INITIATING. Doesn't fix prompts that lack any
   exploration keyword (e.g. plain "I want to think about X").

The trade-off is over-fire vs. under-fire. The previous card establishes
that under-fire (work missed) is the worse failure mode, so option 1 is
the conservative pick if the whitelist is generous; option 3 is the
minimal-risk pick.

## Fix sketch

For option 1, the patch is local — only the two offending regexes need
narrowing:

```python
WORK_VERBS = r"(add|fix|build|create|write|implement|refactor|introduce|rename|update|change|remove|delete|extract|ship|make)"
WORK_INITIATING = [
    r"\blet'?s\s+" + WORK_VERBS + r"\b",
    r"\b(implement|build|introduce|refactor)\s+\w",
    r"\b(fix|add|create|write)\s+(a|an|the|this|that|some)\b",
    r"\bi\s+(want|need)\s+to\s+" + WORK_VERBS + r"\b",
    r"\bwe\s+(need|should|want)\s+to\s+" + WORK_VERBS + r"\b",
    r"\bcan\s+you\s+" + WORK_VERBS + r"\b",
    r"\bplease\s+" + WORK_VERBS + r"\b",
    r"\bmake\s+it\s+(work|do|so|happen)\b",
    r"\bship\s+(it|this|the)\b",
]
```

(The closed-card canonical examples — `rename the button to Export`,
`add a CSV export`, `fix the auth bug` — still match via patterns 1, 3,
or 6.)

The fix also lands the same `WORK_VERBS` list in the OpenClaw plugin's
TypeScript port at `openclaw-plugin/index.ts` (which reimplements this
hook).
