---
title: deck-prompt-router-work-verb-as-noun-fires-reminder-on-exploration-questions
summary: "The UserPromptSubmit hook's `WORK_INITIATING` work-verb-plus-any-word pattern (deck_prompt_router.py:28) matches a work verb followed by any word anywhere in a prompt, so a pure exploration question that merely names a work verb as a noun ('how does the update logic work?') sets has_work True and the precedence rule fires the GoC reminder, contradicting the hook's 'silent for pure exploration' contract. Distinct trigger from the sibling `deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts` (that card blames the i-want-to / we-need-to patterns; this one is the general work-verb matcher)."
status: open
stage: null
contribution: medium
created: "2026-06-25T13:44:07Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — none of the five pure-exploration prompts (`how does the update logic work?`, `what does the move command do?`, `explain the rename function`, `what is the build pipeline?`, `how does add work in this codebase?`) print the GoC reminder.
  - [ ] TDD: the canonical work examples (`rename the button to Export`, `add a CSV export`, `fix the auth bug`) STILL print the reminder — the fix must not regress work detection or `prompt-hook-misses-rename-work-requests`.
  - [ ] PROCESS: decision recorded in `## Decision required` — which fix path, coordinated with the sibling card `deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts` (both cards share the precedence root cause; verify the chosen path closes both). Record reasoning in log.md.
  - [ ] MECHANICAL: `python scripts/sync_plugin_assets.py --check` clean (the hook ships in three plugin payloads + the `.claude/hooks/` dogfood copy).
  - [ ] MECHANICAL: `uv run goc validate` clean.
---

# `deck_prompt_router` fires the GoC reminder when a work verb appears as a noun in an exploration question

## Summary

The UserPromptSubmit hook's `WORK_INITIATING` pattern `\b({WORK_VERBS})\s+\w`
matches a work verb followed by any word *anywhere* in the prompt, so a pure
exploration question that merely *names* a work verb as a noun — "how does the
**update** logic work?", "what does the **move** command do?" — sets
`has_work` True. The precedence rule then lets work beat the matched
exploration pattern, and the reminder fires, contradicting the hook's
"Silent for pure exploration / explanation" contract. This is a sibling of
`deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts`, but
a distinct trigger: that card blames the `i want to` / `we need to` patterns
(lines 30-31); this one is the general work-verb matcher (line 28).

## Location

- `goc/templates/hooks/deck_prompt_router.py:26-36` — `WORK_INITIATING`.
  The offender is item 2 (line 28):

  ```python
  WORK_INITIATING = [
      rf"\blet'?s\s+(do|make|ship|{WORK_VERBS})\b",
      rf"\b({WORK_VERBS})\s+\w",                          # ← matches a work verb + ANY word, anywhere
      rf"\b({WORK_VERBS})\s+(a|an|the|this|that|some)\b",
      ...
  ]
  ```

  with `WORK_VERBS = "add|build|change|create|delete|extract|fix|implement|introduce|move|refactor|remove|rename|update|write"`.

- `goc/templates/hooks/deck_prompt_router.py:83-90` — the precedence rule:

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

The hook's stated contract (module docstring, lines 4-7) is:

> Silent for pure exploration / explanation / one-shot tooling — those
> don't need cards. The reminder is opt-in (matched), not blanket.

But line 28's `\b({WORK_VERBS})\s+\w` cannot distinguish a verb used as an
imperative ("**update** the config") from the same token used as a noun /
adjective inside an exploration question ("how does the **update** logic
work?"). Several common nouns ARE in `WORK_VERBS` — `update`, `move`,
`change`, `build`, `rename`, `extract` — so an explanatory question that
mentions one of these subsystems by name trips `has_work`. The precedence
rule then injects the REMINDER even though `\bhow\s+does\b` /
`\bwhat\s+is\b` / `\bexplain\b` also matched.

The REMINDER tells the agent definitively to run the create-card pipeline
("file it", "claim it", "Implement the work") on what is actually a
request for an explanation — the agent is steered to scaffold a card for a
question the user never intended as work.

## Empirical evidence

`reproduce.py` output on a clean checkout:

```
hook: goc/templates/hooks/deck_prompt_router.py

Pure-exploration prompts (should be SILENT):
  [FIRES (bug)] 'how does the update logic work?'
  [FIRES (bug)] 'what does the move command do?'
  [FIRES (bug)] 'explain the rename function'
  [FIRES (bug)] 'what is the build pipeline?'
  [FIRES (bug)] 'how does add work in this codebase?'

Canonical work prompts (must still FIRE):
  [        fires (ok)] 'rename the button to Export'
  [        fires (ok)] 'add a CSV export'
  [        fires (ok)] 'fix the auth bug'

DEFECT: 5 exploration prompt(s) wrongly fired the work reminder.
```

All five exploration prompts wrongly fire; the three canonical work prompts
still fire (so the bug is the false-positive direction only).

## Why it matters

This is the **same root cause** as the open sibling card
[deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts](../deck-prompt-router-i-want-to-pattern-fires-on-pure-exploration-prompts/):
an over-broad `WORK_INITIATING` pattern combined with the
work-always-wins precedence rule. The two cards matter together because they
**constrain the fix path**:

- The sibling's narrow-regex fix path (path 1: tighten `i (want|need) to` /
  `we (need|should|want) to` to specific verbs) would NOT fix *this* card —
  the false positive here comes from line 28, not lines 30-31.
- The sibling's "add `understand|investigate|know|learn` to EXPLORATION"
  path (path 3) also would not help here: these prompts already match an
  EXPLORATION pattern, yet `has_work` still wins under the current
  precedence rule. Adding more exploration matches changes nothing while
  precedence favors work.
- Only **flipping the precedence** (exploration suppresses work) or making
  line 28 part-of-speech-aware fixes both cards at once.

So whichever path the human picks for the sibling should be evaluated
against this card's prompts too, or the family stays half-fixed.

Reachability: this is a live `UserPromptSubmit` hook registered in
`GOC_CLAUDE_HOOKS` and shipped in all four payloads (the three plugins +
the `.claude/hooks/` dogfood copy). Every interactive Claude Code / Codex /
OpenClaw session routes the user's prompt through it, so any exploration
question that names an `update`/`move`/`build`/etc. subsystem triggers the
false positive in normal use.

## Decision required

The fix is a judgment call shared with the sibling card. Credible paths:

1. **Flip the precedence** so a matched exploration/tooling pattern
   suppresses the reminder even when a work pattern also matches
   (`if has_exploration or has_tooling: return 0` before the work check).
   Fixes both cards. Risk: a genuine mixed prompt ("explain X, then add Y")
   would be silenced — may be acceptable since the user can still ask
   explicitly.
2. **Anchor line 28 to imperative position** — only treat a work verb as
   work-initiating at the start of the prompt or after a clause boundary
   (`^`, sentence start, or after a connective), not when preceded by an
   article/determiner ("the update", "a move"). Narrower; preserves
   mixed-prompt behavior but is more fragile.
3. **Negative lookbehind for determiners** on line 28
   (`(?<!\b(the|a|an|this|that|its|your|our)\s)({WORK_VERBS})\s+\w`) so a
   verb following an article reads as a noun. Targeted; leaves the
   precedence rule and the sibling's lines 30-31 untouched.

Pick one (ideally one that closes both sibling cards), then implement and
record the reasoning in `log.md`.
