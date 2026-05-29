"""Reproduce: --advances / --advanced-by CLI filters substring-match a
bare-string-scalar edge value instead of doing list membership.

Exits zero when the defect is GONE (filter_cards returns no false-positive
on the substring query); non-zero while the defect is live.
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

from goc.engine import Card, filter_cards  # noqa: E402


def main() -> int:
    scalar = Card(
        title="scalar-card",
        path=Path("/tmp/scalar"),
        body="",
        dod_open=0,
        dod_done=0,
        frontmatter={
            "title": "scalar-card",
            "status": "open",
            "advances": "foo-card-extended",  # bare-string scalar shape
        },
    )
    list_c = Card(
        title="list-card",
        path=Path("/tmp/list"),
        body="",
        dod_open=0, dod_done=0,
        frontmatter={
            "title": "list-card",
            "status": "open",
            "advances": ["foo-card-extended"],  # canonical list shape
        },
    )

    substring_hit = filter_cards([scalar, list_c], status=None, advances="foo")
    full_hit = filter_cards(
        [scalar, list_c], status=None, advances="foo-card-extended"
    )

    print("substring foo matched:", [c.title for c in substring_hit])
    print("full title match:", [c.title for c in full_hit])

    # 'foo' is not a card title — membership over an edge list cannot
    # produce a match. While the bug is live, the bare-string-scalar
    # card matches by substring.
    if substring_hit:
        print(
            "DEFECT: --advances 'foo' returned",
            [c.title for c in substring_hit],
            "(expected []).",
        )
        return 1

    print("OK: --advances 'foo' returned [] for the bare-string scalar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
