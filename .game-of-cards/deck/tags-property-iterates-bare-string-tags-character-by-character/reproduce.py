"""Reproduce the bare-string `tags` field misbehavior in engine render/filter paths.

A card whose frontmatter has been hand-edited to `tags: bug` (scalar
string instead of list) flows through `Card.tags` unchanged. Two
consumer sites in `goc/engine.py` then treat the string as an iterable
of characters or substring-match haystack.

After the fix lands (mirror the `isinstance(..., list)` guard added in
`compute_values` / `find_half_edges` onto the `tags` property), this
script exits 0; before the fix, it exits 1.
"""

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

from goc.engine import Card  # noqa: E402


def main() -> int:
    # Simulate a card whose frontmatter has tags as a bare string
    # (hand-edited `tags: bug` instead of `tags: [bug]`).
    card = Card.__new__(Card)
    card.frontmatter = {"tags": "bug"}
    card.title = "x"
    card.path = Path("/tmp/x")

    # Render path: lines 2171-2173 in engine.py.
    render_str = ",".join(card.tags[:4])
    if len(card.tags) > 4:
        render_str += "+"
    print(f"render of card with tags='bug':      {render_str!r}")

    # Filter path: line 1921 in engine.py.
    match_b = all(tag in card.tags for tag in ["b"])
    print(f"filter '--tag b' matches card with tags='bug': {match_b}   "
          f"(BUG: should be False)" if match_b else "(correct)")

    match_other = all(tag in card.tags for tag in ["bug-other"])
    print(f"filter '--tag bug-other' matches card with tags='bug': {match_other}  "
          f"(correct)" if not match_other else "(BUG: should be False)")

    # Pass condition (post-fix):
    #   - render shows the tag verbatim (e.g. "bug" or "" — depends on
    #     chosen coercion; both are correct, "b,u,g" is the defect).
    #   - filter '--tag b' does NOT match (no substring fallthrough).
    if render_str == "b,u,g" or match_b:
        print("FAIL: bare-string tags misbehave in render or filter path")
        return 1
    print("PASS: bare-string tags handled safely")
    return 0


if __name__ == "__main__":
    sys.exit(main())
