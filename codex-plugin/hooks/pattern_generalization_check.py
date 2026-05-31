"""Stop hook — prompt agent to file generalization cards for pattern instances.

Fires only on turns that included code-mutating tool calls (Edit, Write, or
NotebookEdit, or Bash containing a git-commit). Blocks the stop and feeds the
agent a reminder asking it to self-assess whether the change is an instance of
a broader pattern that warrants its own generalization card.

Claude Code's Stop event has no non-blocking channel to the model: exit-0
stdout is shown only in the user's transcript view, never injected into
context. To reach the agent, the hook must block — exit code 2 with the
reminder on stderr (Claude Code feeds stderr back to the model on a block).
The host's own `stop_hook_active` flag (checked below) prevents an infinite
re-block loop: the second Stop after the agent's continuation turn carries
`stop_hook_active: true` and is a no-op.

Opt-out per-repo in .game-of-cards/config.yaml:
  hooks:
    pattern_generalization_check: false
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

CODE_MUTATING_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})

# Broad-staging flags for `git add`: short single-letter forms plus their
# long-form aliases documented in `git-add(1)`. The bare `.` pathspec is
# handled separately as a non-flag token.
_BROAD_STAGING_FLAGS = frozenset(
    {"-A", "-p", "-u", "--all", "--update", "--patch"}
)


def _is_broad_git_mutation(cmd: str) -> bool:
    """Return True iff `cmd` is a broad index-mutating git invocation.

    Matches `git commit ...` (any form) and `git add` with one of the
    broad-staging flags in :data:`_BROAD_STAGING_FLAGS` or the bare `.`
    pathspec. Deliberately rejects `git add -- <path>` and `git add <path>`
    — those stage explicit paths and are the parallel-agent-safe idiom
    documented in AGENTS.md.

    The matcher tokenizes via :func:`shlex.split` and inspects tokens by
    equality, so future git long-form alias additions can be picked up by
    extending :data:`_BROAD_STAGING_FLAGS` without re-deriving regex
    alternations.
    """
    try:
        tokens = shlex.split(cmd, comments=False, posix=True)
    except ValueError:
        return False
    if len(tokens) < 2 or tokens[0] != "git":
        return False
    if tokens[1] == "commit":
        return True
    if tokens[1] != "add":
        return False
    for tok in tokens[2:]:
        if tok == "--":
            # Pathspec separator: explicit paths follow, not broad staging.
            return False
        if tok == "." or tok in _BROAD_STAGING_FLAGS:
            return True
    return False

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


def _is_tool_result_only(entry: dict) -> bool:
    """True for a role=user entry whose content is a non-empty list of all tool_result blocks.

    Claude Code wraps every tool_result in a role=user message. Such entries
    are continuations of the assistant's tool-using turn, not the prior user
    prompt, so the backward walk in `_had_code_mutation` must not treat them
    as the turn boundary.
    """
    if isinstance(entry.get("message"), dict):
        msg = entry["message"]
        role, content = msg.get("role"), msg.get("content", [])
    else:
        role, content = entry.get("role"), entry.get("content", [])

    if role != "user" or not isinstance(content, list) or not content:
        return False
    return all(
        isinstance(b, dict) and b.get("type") == "tool_result" for b in content
    )


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
            if _is_broad_git_mutation(cmd):
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
            if role == "user" and found_assistant and not _is_tool_result_only(entry):
                break
            if role == "assistant":
                found_assistant = True

    return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if not isinstance(data, dict):
        return 0

    if data.get("stop_hook_active"):
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or "."
    if _opted_out(project_dir):
        return 0

    transcript_path = data.get("transcript_path", "")
    if not isinstance(transcript_path, str) or not transcript_path:
        return 0

    if _had_code_mutation(transcript_path):
        print(REMINDER, file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
