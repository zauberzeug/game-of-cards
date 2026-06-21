"""Reproduce: the queue table crashes on a card whose `tags` list contains
a non-string element (e.g. an int).

Before the fix (render_table joins tags directly):
    render_table CRASH: TypeError sequence item 1: expected str instance, int found

After the fix (join coerces each element to str):
    render_table renders; exit 0. (render_board does not render tags;
    render_json emits the list as-is — both already tolerate the shape.)
"""

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


def _card():
    fm = {
        "title": "x",
        "status": "open",
        "contribution": "low",
        "human_gate": "none",
        "tags": ["bug", 42],  # non-string element — accepted by the parser
    }
    return engine.Card(
        title="x", frontmatter=fm, body="", path=None, dod_open=1, dod_done=0
    )


def main() -> int:
    c = _card()
    vals = engine.compute_values([c])
    failures = 0

    for label, fn in (
        ("render_table", lambda: engine.render_table([c], values=vals, verbose=0, no_color=True)),
        ("render_table (verbose)", lambda: engine.render_table([c], values=vals, verbose=1, no_color=True)),
    ):
        try:
            fn()
            print(f"{label} OK")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"{label} CRASH: {type(exc).__name__} {exc}")

    # These two already tolerate the shape — assert they stay healthy.
    try:
        engine.render_board([c], values=vals, no_color=True, max_rows=20)
        print("render_board OK (no tags in cell)")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print(f"render_board CRASH: {type(exc).__name__} {exc}")
    try:
        json.loads(engine.render_json([c], values=vals))
        print("render_json OK")
    except Exception as exc:  # noqa: BLE001
        failures += 1
        print(f"render_json CRASH: {type(exc).__name__} {exc}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
