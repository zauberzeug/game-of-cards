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

Off by default (opt-in): because the hook blocks every code-mutating turn
to inject the reminder — spending an extra agent round-trip even when no
generalization is warranted — it runs only when a repo explicitly enables
it in .game-of-cards/config.yaml:
  hooks:
    pattern_generalization_check: true
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

CODE_MUTATING_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})

# YAML-true spellings the engine's yaml_lite coerces to True. Mirrors the
# sibling `deck_session_start.py` `_TRUE_SET` so `pattern_generalization_check:
# True` / `yes` enable the hook the same way `true` does (see card
# pattern-generalization-hook-enable-regex-misses-capitalized-and-yes-yaml-booleans).
_TRUE_SET = frozenset(("true", "True", "TRUE", "yes", "Yes", "YES"))

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
    "with broader applicability? If NO, respond "
    '"no generalization needed" and stop. '
    "If YES, dedup first (scan the deck): if a generalization/root card already "
    "exists, CONNECT this instance to it (cross-reference or an advances edge) and "
    "name it — do not file a duplicate; only if none exists, file a new card via "
    "Skill(create-card)."
)


# The line `worktree_deck: shared` as the engine's yaml_lite reads it: the bare
# or quoted word, then at most a whitespace-led trailing comment.
_SHARED_DECK_LINE_RE = re.compile(
    r"""worktree_deck:[ \t]+(?:shared|"shared"|'shared')(?:[ \t]+#.*)?$"""
)


def _detect_worktree_common_root(cwd: Path) -> Path | None:
    """Return the primary working tree root if `cwd` is inside a linked git
    worktree, else None. Mirror of `goc.engine._detect_worktree_common_root`:
    there `git rev-parse --git-common-dir` differs from `--git-dir`, compared
    as resolved paths because git prints one absolute and the other relative
    from a subdirectory of the primary working tree.
    """
    try:
        r_git = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, text=True, cwd=str(cwd), timeout=5,
        )
        r_common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, cwd=str(cwd), timeout=5,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        # No git, or a hook-input cwd that is gone or not a directory.
        return None
    if r_git.returncode != 0 or r_common.returncode != 0:
        return None
    # `cwd / p` is `p` itself when git printed an absolute path.
    git_dir = (cwd / r_git.stdout.strip()).resolve()
    common_path = (cwd / r_common.stdout.strip()).resolve()
    if git_dir == common_path:
        return None  # primary working tree, not a worktree
    return common_path.parent


def _config_shares_the_deck(text: str) -> bool:
    """Whether a config.yaml text sets `workflow.worktree_deck` to `shared`.

    The engine parses the file with yaml_lite and compares the value to
    `"shared"`. This reads the block layout the config template ships: the
    key one level under the top-level `workflow:` key, with comment lines
    skipped, so the template's commented-out line stays off. A flow-style
    `workflow: {...}` is not read. Where yaml_lite refuses the file, the
    engine leaves the redirect off, and so does this for the refusals within
    reach: a tab in the indentation, a repeated top-level or `workflow` key.
    """
    top_indent: int | None = None
    child_indent: int | None = None
    top_keys: set[str] = set()
    child_keys: set[str] = set()
    in_workflow = False
    shared = False
    for raw in text.splitlines():
        line = raw.rstrip()
        bare = line.lstrip()
        if not bare or bare.startswith("#"):
            continue
        indent = len(line) - len(bare)
        if "\t" in line[:indent]:
            return False
        if top_indent is None:
            top_indent = indent
        key = bare.split(":", 1)[0]
        if indent <= top_indent:
            if key in top_keys:
                return False
            top_keys.add(key)
            in_workflow = re.match(r"workflow:(?:[ \t]+#.*)?$", bare) is not None
            continue
        if not in_workflow:
            continue
        if child_indent is None:
            child_indent = indent
        if indent == child_indent:
            if key in child_keys:
                return False
            child_keys.add(key)
            if key == "worktree_deck":
                shared = _SHARED_DECK_LINE_RE.match(bare) is not None
    return shared


def _shared_worktree_deck_root(cwd: Path) -> Path | None:
    """Return the primary working tree root when `cwd` is in a linked git
    worktree that opted into `worktree_deck: shared`, else None. Mirror of
    `goc.engine._shared_worktree_deck_root`.
    """
    common_root = _detect_worktree_common_root(cwd)
    if common_root is None:
        return None
    # Env var wins without requiring the config to exist yet.
    if os.environ.get("GOC_WORKTREE_DECK", "").lower() == "shared":
        return common_root
    config_path = common_root / ".game-of-cards" / "config.yaml"
    try:
        text = config_path.read_text(encoding="utf-8")
    except (OSError, ValueError):
        return None
    return common_root if _config_shares_the_deck(text) else None


def _find_project_dir(start: str) -> Path:
    """Return the deck root `goc` resolves from `start`.

    A mirror of `goc.engine._resolve_deck_root` — hooks import nothing from
    the package — pinned to it by tests/test_project_root_from_subdirectory.py.
    In a linked git worktree that opted into `worktree_deck: shared` (the
    `GOC_WORKTREE_DECK=shared` env var, or the key in the primary tree's
    config), that is the primary working tree. Otherwise it is the nearest
    ancestor of `start` holding `.game-of-cards/`: the walk never crosses into
    a different git working tree, and falls back to `start` itself when no
    ancestor holds a deck.
    """
    start_path = Path(start).resolve()
    shared_root = _shared_worktree_deck_root(start_path)
    if shared_root is not None:
        return shared_root
    own_tree_root_passed = False
    for candidate in (start_path, *start_path.parents):
        has_git = (candidate / ".git").exists()
        if own_tree_root_passed and has_git:
            break
        if (candidate / ".game-of-cards").is_dir():
            return candidate
        if has_git:
            own_tree_root_passed = True
    return start_path


def _enabled(project_dir: str) -> bool:
    """Opt-in (default off): run only when config explicitly enables the hook.

    Returns True iff `.game-of-cards/config.yaml` sets
    `pattern_generalization_check` to any YAML-true spelling in
    :data:`_TRUE_SET` (`true`, `True`, `TRUE`, `yes`, `Yes`, `YES`). Absent
    config, absent key, `false`, or any other value leaves the hook disabled,
    and so does a config that cannot be read or decoded.
    """
    config = Path(project_dir) / ".game-of-cards" / "config.yaml"
    if not config.exists():
        return False
    try:
        text = config.read_text(encoding="utf-8")
    except (OSError, ValueError):
        # Read as absent, the way `_shared_worktree_deck_root` above and the
        # engine's `load_deck_config` read a config that does not decode.
        # This runs on every Stop event, so a raise here fails every turn end.
        return False
    m = re.search(r"pattern_generalization_check\s*:\s*(\S+)", text)
    return bool(m and m.group(1) in _TRUE_SET)


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
        # Hosts write the transcript as UTF-8 JSONL, whatever the locale.
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
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

    # Same input precedence as the session-start hook: the hook input's cwd
    # first, then the host's project-dir variable.
    project_dir = _find_project_dir(
        data.get("cwd")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or "."
    )
    if not _enabled(str(project_dir)):
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
