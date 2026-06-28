"""Reproduce: a card with `human_gate: null` crashes the table renderer.

Exits non-zero while the defect is live (`render_table` raises), and exits
zero once `Card.human_gate` coerces the None/non-string value to a string so
the renderer produces output. Sibling of the null-`status` crash; `render_board`
and the JSON dump already tolerate the value, so only the table view is tested
for the crash.
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
title: ghost-gate
status: open
contribution: medium
created: 2026-06-26
human_gate: null
---
body
"""


def _make_card() -> engine.Card:
    fm, body = engine.parse_frontmatter(FRONTMATTER)
    return engine.Card(
        title="ghost-gate",
        path=None,
        frontmatter=fm,
        body=body,
        dod_open=0,
        dod_done=0,
    )


def main() -> int:
    card = _make_card()
    print(f"parsed Card.human_gate: {card.human_gate!r}")

    failed = False
    try:
        engine.render_table([card], no_color=True, verbose=False)
        print("render_table v0: OK")
    except Exception as e:  # noqa: BLE001
        print(f"render_table v0: CRASH {type(e).__name__}: {e}")
        failed = True

    try:
        engine.render_table([card], no_color=True, verbose=1)
        print("render_table v1: OK")
    except Exception as e:  # noqa: BLE001
        print(f"render_table v1: CRASH {type(e).__name__}: {e}")
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
