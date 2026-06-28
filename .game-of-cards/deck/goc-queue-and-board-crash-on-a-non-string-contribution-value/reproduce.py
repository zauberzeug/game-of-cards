"""Reproduce: the queue table and kanban board crash on a card whose
`contribution` frontmatter is a non-string scalar (e.g. an int).

Before the fix (Card.contribution returns the raw value):
    render_table CRASH: TypeError object of type 'int' has no len()
    render_board CRASH: TypeError 'int' object is not subscriptable

After the fix (Card.contribution coerces to str, mirroring `created`):
    both renderers print a row/cell; exit 0.
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


def _card(contribution):
    fm = {
        "title": "x",
        "status": "open",
        "human_gate": "none",
    }
    if contribution is not _ABSENT:
        fm["contribution"] = contribution
    return engine.Card(
        title="x", frontmatter=fm, body="", path=None, dod_open=1, dod_done=0
    )


_ABSENT = object()


def main() -> int:
    failures = 0

    # Primary defect: a non-string scalar (int) contribution.
    c = _card(42)
    vals = engine.compute_values([c])
    print(
        "compute_values OK (int contribution does not crash the value walk):",
        vals.get("x"),
    )
    for label, fn in (
        ("render_table", lambda: engine.render_table([c], values=vals, verbose=0, no_color=True)),
        ("render_table (verbose)", lambda: engine.render_table([c], values=vals, verbose=1, no_color=True)),
        ("render_board", lambda: engine.render_board([c], values=vals, no_color=True, max_rows=20)),
    ):
        try:
            fn()
            print(f"{label} OK (int)")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"{label} CRASH (int): {type(exc).__name__} {exc}")

    # Regression guard: the empty/None shape the sibling card fixed must
    # keep showing the `[?]` board marker (None stays falsy after coercion).
    cn = _card(None)
    board = engine.render_board([cn], values=engine.compute_values([cn]), no_color=True, max_rows=20)
    if "[?]" in board:
        print("render_board OK (None still marked [?])")
    else:
        failures += 1
        print("render_board REGRESSION (None): expected [?] marker, got:\n" + board)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
