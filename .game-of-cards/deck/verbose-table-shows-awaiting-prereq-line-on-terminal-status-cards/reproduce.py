"""Reproduce: verbose table prints the `awaiting: ... (you may start)`
advisory on a terminal-status card.

A `done` card that still carries a non-terminal `advanced_by` prereq is
labelled `awaiting: <prereq> (you may start)` by render_table at verbose
level — even though a terminal card cannot start. The board renderer gates
the same dependency signal behind a liveness check, so the two renderers
disagree.

Exits non-zero while the defect is present, zero once it is fixed.
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

from goc import engine  # noqa: E402


def _card(title, status, advanced_by, created, closed_at=None):
    fm = {
        "title": title,
        "status": status,
        "contribution": "medium",
        "human_gate": "none",
        "created": created,
        "summary": f"{title} summary",
        "tags": [],
        "advances": [],
        "advanced_by": advanced_by,
        "supersedes": [],
        "superseded_by": [],
        "definition_of_done": "- [x] done\n",
    }
    if closed_at:
        fm["closed_at"] = closed_at
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}/README.md"),
        frontmatter=fm,
        body="body",
        dod_open=0,
        dod_done=1,
    )


def main() -> int:
    closed = _card(
        "closed-child", "done", ["prereq-open"], "2026-06-17",
        closed_at="2026-06-18",
    )
    prereq = _card("prereq-open", "open", [], "2026-06-18")
    cards = [closed, prereq]

    out = engine.render_table(cards, verbose=1, no_color=True)
    print(out)
    print("-" * 60)

    # Find the block of lines belonging to the terminal `closed-child` card.
    lines = out.splitlines()
    in_closed_block = False
    offending = None
    for line in lines:
        stripped = line.strip()
        if line.startswith("closed-child"):
            in_closed_block = True
            continue
        if in_closed_block:
            # An indented continuation line belongs to the current card;
            # a non-indented line starts the next card's block.
            if line.startswith("    "):
                if stripped.startswith("awaiting:"):
                    offending = stripped
                    break
            else:
                in_closed_block = False

    if offending is not None:
        print(
            "DEFECT: terminal-status card 'closed-child' shows an awaiting "
            f"advisory in the verbose table: {offending!r}"
        )
        return 1

    print(
        "OK: no 'awaiting:' advisory under the terminal-status card "
        "'closed-child'."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
