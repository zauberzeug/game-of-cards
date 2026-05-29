"""Reproduce: bare-string `supersedes` slips past `validate_supersedes_targets`.

A hand-edited card with `supersedes: <slug>` (bare string instead of a
list) makes the validator iterate the string character-by-character. If
any one-character title in the deck happens to be `status: superseded`,
the dangling pointer silently passes the integrity check.

Run: `uv run python deck/<this-card>/reproduce.py`

Exits zero once the engine guards the iteration with `isinstance(..., list)`.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402


class FakeCard:
    """Minimal stand-in matching the attributes engine.validate_supersedes_targets reads."""

    def __init__(self, title: str, status: str, frontmatter: dict) -> None:
        self.title = title
        self.status = status
        self.frontmatter = frontmatter


def main() -> int:
    # Card `a` claims to supersede "nonexistent" via a bare-string scalar
    # (the hand-edited shape that breaks list-style frontmatter).
    a = FakeCard(
        title="a",
        status="open",
        frontmatter={"title": "a", "status": "open", "supersedes": "nonexistent"},
    )
    # Card `n` has a single-character title matching the FIRST char of
    # "nonexistent" and is `status: superseded` — so the buggy
    # char-by-char walk finds a "valid" supersedes target on iteration 0.
    n = FakeCard(
        title="n",
        status="superseded",
        frontmatter={"title": "n", "status": "superseded"},
    )

    errors = engine.validate_supersedes_targets([a, n])
    print("validate_supersedes_targets errors:", errors)

    # Expected (post-fix): an error naming the dangling 'nonexistent' target.
    # Actual (pre-fix): [] — the validator iterated the string, matched 'n',
    # found a superseded card, and silently passed.
    if any("nonexistent" in e for e in errors):
        print("PASS: validator flagged the dangling bare-string target.")
        return 0
    print(
        "FAIL: dangling supersedes target 'nonexistent' was not reported. "
        "Loop iterated the string character-by-character; char 'n' silently "
        "matched a superseded card."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
