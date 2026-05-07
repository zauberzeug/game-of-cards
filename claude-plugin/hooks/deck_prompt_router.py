"""UserPromptSubmit hook — detect work-initiating prompts and inject deck-first reminder.

Reads the user prompt from stdin (Claude Code passes JSON with a `prompt` field).
If the prompt looks work-initiating, emits a reminder that gets prepended to
Claude's view of the message.

Silent for pure exploration / explanation / one-shot tooling — those don't
need cards. The reminder is opt-in (matched), not blanket.
"""

from __future__ import annotations

import json
import re
import sys

WORK_INITIATING = [
    r"\blet'?s\s+(do|build|implement|make|add|create|fix|introduce|write|refactor)\b",
    r"\b(implement|build|introduce|refactor)\s+\w",
    r"\b(fix|add|create|write)\s+(a|an|the|this|that|some)\b",
    r"\bi\s+(want|need)\s+(to|a|an|the|this)\b",
    r"\bwe\s+(need|should|want)\s+to\b",
    r"\bcan\s+you\s+(add|fix|build|create|implement|introduce|write)\b",
    r"\bplease\s+(add|fix|build|create|implement|introduce|write)\b",
    r"\bmake\s+it\s+(work|do|so|happen)\b",
    r"\bship\s+(it|this|the)\b",
]

EXPLORATION = [
    r"\bexplain\b",
    r"\bwhat\s+does\b",
    r"\bwhat\s+is\b",
    r"\bhow\s+does\b",
    r"\bwhy\s+(is|does|are)\b",
    r"\bshow\s+me\b",
    r"\b(can|could)\s+you\s+(explain|tell|show|describe)\b",
    r"\bwalk\s+me\s+through\b",
]

TOOLING = [
    r"\bgit\s+(status|log|diff|stash)\b",
    r"\brebase\b",
    r"\brun\s+(pytest|the\s+tests)\b",
    r"\bnpm\s+(install|run)\b",
    r"\buv\s+(sync|run|pip)\b",
]

REMINDER = """\
[Game of Cards | runtime active]
The user's prompt above is a card request. Run the GoC pipeline SILENTLY:
  1. Skill(scan-deck) — does a card already cover this?
  2. Skill(create-card) — if not, file it. The user's words ARE the briefing.
  3. Skill(advance-card) <title> active — claim it.
  4. Implement the work.
  5. Skill(finish-card) <title> — close (DoD-gated). Then commit the work and closure.
DO NOT announce card operations to the user ("I'll file a card now…",
"closing the card…"). The user is a vibe coder; they see code, not
bookkeeping. Mention card titles only if they ask to see the deck.
The deck is the implementation, not the workflow.
"""


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    prompt = (data.get("prompt") or "").lower()
    if not prompt:
        return 0
    has_work = any(re.search(p, prompt) for p in WORK_INITIATING)
    has_exploration = any(re.search(p, prompt) for p in EXPLORATION)
    has_tooling = any(re.search(p, prompt) for p in TOOLING)
    if (has_exploration or has_tooling) and not has_work:
        return 0
    if has_work:
        print(REMINDER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
