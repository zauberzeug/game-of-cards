#!/usr/bin/env python3
"""Reproduce: render_json emits the dependency advisory on terminal cards.

A terminal card (done / disproved / superseded) that still references a
non-terminal `advanced_by` prereq is reported by `render_json` with a
non-empty `awaiting` and `dependency_awaiting: true` — the "you may
start" hint, which is meaningless on a card that cannot start. The
table and board renderers suppress it; the JSON record does not.

Exit 0 when the defect is GONE (terminal cards report empty advisory),
exit 1 while it is present.
"""

from __future__ import annotations

import json
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

TERMINAL = {"done", "disproved", "superseded"}


def _card(title: str, status: str, advanced_by: list[str]) -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}/README.md"),
        frontmatter={
            "title": title,
            "status": status,
            "contribution": "medium",
            "human_gate": "none",
            "created": "2026-06-17",
            "summary": f"{title} summary",
            "tags": [],
            "advances": [],
            "advanced_by": advanced_by,
            "supersedes": [],
            "superseded_by": [],
            "definition_of_done": "- [x] done\n",
        },
        body="body",
        dod_open=0,
        dod_done=1,
    )


def main() -> int:
    prereq = _card("prereq-open", "open", [])
    live = _card("live-child", "open", ["prereq-open"])
    cards = [prereq, live]
    bad = []
    for status in ("done", "disproved", "superseded"):
        closed = _card("closed-child", status, ["prereq-open"])
        records = json.loads(engine.render_json([prereq, live, closed]))
        rec = next(r for r in records if r["title"] == "closed-child")
        print(
            f"status={status:11s} awaiting={rec['awaiting']!r} "
            f"dependency_awaiting={rec['dependency_awaiting']!r}"
        )
        if rec["awaiting"] or rec["dependency_awaiting"]:
            bad.append(status)

    # A live card with the same open prereq must still report it.
    live_rec = next(
        r for r in json.loads(engine.render_json(cards)) if r["title"] == "live-child"
    )
    print(
        f"live-child   awaiting={live_rec['awaiting']!r} "
        f"dependency_awaiting={live_rec['dependency_awaiting']!r}"
    )

    if bad:
        print(f"\nFAIL: terminal cards leak the advisory in JSON: {bad}")
        return 1
    if live_rec["awaiting"] != ["prereq-open"] or not live_rec["dependency_awaiting"]:
        print("\nFAIL: live card lost its advisory")
        return 1
    print("\nPASS: terminal cards omit the advisory; live card keeps it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
