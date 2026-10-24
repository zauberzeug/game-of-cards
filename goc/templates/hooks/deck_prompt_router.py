"""UserPromptSubmit hook — detect work-initiating prompts and inject deck-first reminder.

Reads the user prompt from stdin. If the prompt looks work-initiating, emits a
reminder that gets prepended to the agent's view of the message.

Silent for pure exploration / explanation / one-shot tooling — those don't
need cards. The reminder is opt-in (matched), not blanket.

Silent, too, in a repo that never opted in. The plugin registers its hooks
globally, so this one runs in every repo the user works in; it speaks only
where the session-start hook reads a deck — `.game-of-cards/deck/`, or the
legacy `deck/`, at the root `goc` resolves from the session's directory.
`goc install` (via `Skill(kickoff)`) opts a repo in; a work-shaped prompt
never does.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

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


def _project_dir(data: dict) -> Path:
    """The root `goc` resolves for this session, from the same inputs as the
    session-start hook: the hook input's cwd first, then the host's
    project-dir variable."""
    cwd = data.get("cwd")
    return _find_project_dir(
        (cwd if isinstance(cwd, str) else "")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.environ.get("CODEX_PROJECT_DIR")
        or "."
    )


def _has_deck(project_dir: Path) -> bool:
    """Whether the repo opted in: it holds the deck the session-start hook
    reads, the canonical `.game-of-cards/deck/` or the legacy `deck/`."""
    return (project_dir / ".game-of-cards" / "deck").is_dir() or (project_dir / "deck").is_dir()


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
    # The deck is looked up only for a work-shaped prompt, so no other prompt
    # pays for the git probes behind the project-dir resolution.
    if has_work and _has_deck(_project_dir(data)):
        print(REMINDER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
