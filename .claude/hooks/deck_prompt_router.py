"""UserPromptSubmit hook — detect work-initiating prompts and inject deck-first reminder.

Reads the user prompt from stdin. If the prompt looks work-initiating, emits a
reminder that gets prepended to the agent's view of the message.

Silent for pure exploration / explanation / one-shot tooling — those don't
need cards. The reminder is opt-in (matched), not blanket.
"""

from __future__ import annotations

import json
import re
import sys

# Edit-style work verbs — the single source-of-truth set referenced from every
# WORK_INITIATING alternation site. Adding a verb here teaches the router about
# a new edit shape with a one-line change. Splitting this across multiple
# alternation sites caused the rename/update/change/delete/remove/move
# regression: a verb added to one site, missing from the others.
WORK_VERBS = (
    "add|build|change|create|delete|extract|fix|implement|"
    "introduce|move|refactor|remove|rename|update|write"
)

WORK_INITIATING = [
    rf"\blet'?s\s+(do|make|ship|{WORK_VERBS})\b",
    rf"\b({WORK_VERBS})\s+\w",
    rf"\b({WORK_VERBS})\s+(a|an|the|this|that|some)\b",
    r"\bi\s+(want|need)\s+(to|a|an|the|this)\b",
    r"\bwe\s+(need|should|want)\s+to\b",
    rf"\bcan\s+you\s+({WORK_VERBS})\b",
    rf"\bplease\s+({WORK_VERBS})\b",
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
    if not isinstance(data, dict):
        return 0
    prompt_raw = data.get("prompt")
    if not isinstance(prompt_raw, str) or not prompt_raw:
        return 0
    prompt = prompt_raw.lower()
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
