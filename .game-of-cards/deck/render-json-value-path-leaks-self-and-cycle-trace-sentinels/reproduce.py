"""Reproduce the `value_path` sentinel leak in `render_json`.

`compute_values` terminates every argmax chain with an internal sentinel
(`["self"]` for a leaf, `["cycle"]` on a validate-failing cyclic deck).
`_format_why` (the `-v` WHY column) strips that sentinel, but `render_json`
emits the raw path, so the machine-readable `value_path` field presents the
sentinel as if it were a card title.

Exits non-zero while the leak is present, zero once `render_json` strips the
sentinel to match `_format_why`.
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


def _card(title: str, advances: list[str], contrib: str = "medium") -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}/README.md"),
        frontmatter={
            "title": title,
            "status": "open",
            "contribution": contrib,
            "human_gate": "none",
            "created": "2026-06-24",
            "summary": f"{title} summary",
            "tags": [],
            "advances": advances,
            "advanced_by": [],
            "supersedes": [],
            "superseded_by": [],
            "definition_of_done": "- [ ] x\n",
        },
        body="body",
        dod_open=1,
        dod_done=0,
    )


def main() -> int:
    root = _card("root-card", ["mid-card"])
    mid = _card("mid-card", ["leaf-card"])
    leaf = _card("leaf-card", [], contrib="high")
    cards = [root, mid, leaf]

    by_title = {c.title: c for c in cards}
    records = {r["title"]: r for r in json.loads(engine.render_json(cards))}
    values = engine.compute_values(cards)

    print("value_path leak in render_json:")
    for t in ("root-card", "mid-card", "leaf-card"):
        print(f"  {t:<10} -> {records[t]['value_path']}")

    print("WHY column (-v, already correct) for the same chain:")
    for t in ("root-card", "leaf-card"):
        why = engine._format_why(values[t][1], by_title) or "(empty)"
        print(f"  {t:<10} -> {why}")

    leaked = any(
        s in records[t]["value_path"]
        for t in records
        for s in ("self", "cycle")
    )
    if leaked:
        print("LEAK CONFIRMED: value_path emits the 'self' sentinel as a chain member.")
        return 1
    # Post-fix expectations.
    assert records["leaf-card"]["value_path"] == [], records["leaf-card"]["value_path"]
    assert records["mid-card"]["value_path"] == ["leaf-card"]
    assert records["root-card"]["value_path"] == ["mid-card", "leaf-card"]
    print("OK: value_path carries only real card slugs (no sentinel leak).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
