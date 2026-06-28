"""Reproduce: a card with `status: null` crashes both human-facing renderers.

Exits non-zero while the defect is live (either renderer raises), and exits
zero once `Card.status` coerces the None/non-string value to a string so both
renderers produce output.
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

FRONTMATTER = """---
title: ghost-card
status: null
contribution: medium
created: 2026-06-26
human_gate: none
---
body
"""


def _make_card() -> engine.Card:
    fm, body = engine.parse_frontmatter(FRONTMATTER)
    return engine.Card(
        title="ghost-card",
        path=None,
        frontmatter=fm,
        body=body,
        dod_open=0,
        dod_done=0,
    )


def main() -> int:
    card = _make_card()
    print(f"parsed Card.status: {card.status!r}")

    failed = False
    try:
        engine.render_table([card], no_color=True, verbose=False)
        print("render_table:  OK")
    except Exception as e:  # noqa: BLE001
        print(f"render_table:  CRASH {type(e).__name__}: {e}")
        failed = True

    try:
        engine.render_board([card], max_rows=20, no_color=True)
        print("render_board:  OK")
    except Exception as e:  # noqa: BLE001
        print(f"render_board:  CRASH {type(e).__name__}: {e}")
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
