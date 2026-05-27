#!/usr/bin/env python3
"""Demonstrate that `goc --board` crashes on a card with no `contribution`.

`render_board`'s `card_cell` does `f" [{t.contribution[0]}]"`, indexing the
first character of `contribution`. A card that omits the key (property
returns "") or blanks it (`contribution:` -> None) loads without validation
on the --board path and crashes the renderer for the WHOLE deck.

Exits 0 when the renderer tolerates the malformed card (defect fixed),
non-zero while the crash is live.
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


def _card(title, frontmatter):
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}"),
        frontmatter={"title": title, **frontmatter},
        body="",
        dod_open=1,
        dod_done=0,
    )


def main() -> int:
    valid = _card("valid-card", {
        "status": "open", "human_gate": "none", "contribution": "high",
        "advanced_by": [], "advances": [],
    })
    # Blank YAML value `contribution:` parses to None (key present, value None).
    blank = _card("blank-contribution-card", {
        "status": "open", "human_gate": "none", "contribution": None,
        "advanced_by": [], "advances": [],
    })
    # Absent key -> the property returns "".
    absent = _card("absent-contribution-card", {
        "status": "open", "human_gate": "none",
        "advanced_by": [], "advances": [],
    })

    for label, deck in (("blank (None)", [valid, blank]),
                        ("absent (\"\")", [valid, absent])):
        try:
            engine.render_board(deck, max_rows=20, no_color=True)
            print(f"{label}: render_board OK")
        except Exception as exc:  # noqa: BLE001
            print(f"{label}: render_board CRASHED -> "
                  f"{type(exc).__name__}: {exc}")
            print("\nFAIL: one card with no contribution crashes the whole board.")
            return 1

    print("\nPASS: render_board tolerates cards with no contribution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
