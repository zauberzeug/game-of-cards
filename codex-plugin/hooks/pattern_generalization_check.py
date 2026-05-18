"""Stop hook — prompt agent to file generalization cards for pattern instances.

Fires only on turns that included code-mutating tool calls (Edit or Write, or
Bash containing a git-commit). Injects a system reminder asking the agent to
self-assess whether the change is an instance of a broader pattern that warrants
its own generalization card.

Design A+B+A: lightweight prompt-only / code-mutating-turns only / reminder-only.
Opt-out per-repo in .game-of-cards/config.yaml:
  hooks:
    pattern_generalization_check: false
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

CODE_MUTATING_TOOLS = frozenset({"Edit", "Write"})
BASH_COMMIT_TOKENS = ("git commit", "git add -", "git add .")

REMINDER = (
    "[GoC | pattern-check] Before yielding: did your recent change touch a pattern "
    "with broader applicability? If yes, file a generalization card via "
    "Skill(create-card) before stopping. "
    'If no generalization is warranted, respond "no generalization needed" and stop.'
)


def _opted_out(project_dir: str) -> bool:
    config = Path(project_dir) / ".game-of-cards" / "config.yaml"
    if not config.exists():
        return False
    try:
        m = re.search(
            r"pattern_generalization_check\s*:\s*(false|true)", config.read_text()
        )
        return bool(m and m.group(1) == "false")
    except OSError:
        return False


def _extract_tool_names(entry: dict) -> list[str]:
    """Return tool names from an assistant message entry (handles nested and flat)."""
    if isinstance(entry.get("message"), dict):
        msg = entry["message"]
        role, content = msg.get("role"), msg.get("content", [])
    else:
        role, content = entry.get("role"), entry.get("content", [])

    if role != "assistant" or not isinstance(content, list):
        return []
    return [
        b.get("name", "")
        for b in content
        if isinstance(b, dict) and b.get("type") == "tool_use"
    ]


def _is_code_mutating(tool_name: str, entry: dict) -> bool:
    if tool_name in CODE_MUTATING_TOOLS:
        return True
    if tool_name == "Bash":
        msg = entry.get("message", entry)
        content = msg.get("content", []) if isinstance(msg, dict) else []
        for block in content:
            if not isinstance(block, dict) or block.get("name") != "Bash":
                continue
            cmd = (block.get("input") or {}).get("command", "")
            if any(tok in cmd for tok in BASH_COMMIT_TOKENS):
                return True
    return False


def _had_code_mutation(transcript_path: str) -> bool:
    """Return True if the most recent assistant turn used a code-mutating tool."""
    path = Path(transcript_path)
    if not path.is_file():
        return False
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return False

    found_assistant = False
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

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


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if data.get("stop_hook_active"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or "."
    if _opted_out(project_dir):
        return 0

    transcript_path = data.get("transcript_path", "")
    if not transcript_path:
        return 0

    if _had_code_mutation(transcript_path):
        print(REMINDER)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
