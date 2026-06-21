"""Reproduce: `goc validate` accepts a `closed_at` that predates `created`.

Builds three `done` cards and runs `validate_card` on each:
  1. closed_at months BEFORE created  -> must be flagged (today: not flagged)
  2. closed_at hours BEFORE created, same day, datetime shape -> must be flagged
  3. closed_at AFTER created (control) -> must NOT be flagged

Exit 0 once the validator flags cases 1 and 2 while leaving case 3 clean.
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

from goc.engine import Card, load_schema, validate_card  # noqa: E402


def _card(created, closed_at):
    fm = {
        "title": "demo",
        "summary": "demo",
        "status": "done",
        "contribution": "low",
        "created": created,
        "closed_at": closed_at,
        "human_gate": "none",
        "tags": [],
        "definition_of_done": "- [x] done",
    }
    return Card(
        title="demo",
        path=Path("demo"),
        frontmatter=fm,
        body="",
        dod_open=0,
        dod_done=1,
    )


def _ordering_errors(card, schema):
    return [e for e in validate_card(card, schema, {"demo"}) if "closed_at" in e and "created" in e]


def main() -> int:
    schema = load_schema()

    before = _card("2026-06-15", "2026-01-01")
    intraday = _card("2026-06-15T12:00:00Z", "2026-06-15T08:00:00Z")
    control = _card("2026-01-01", "2026-06-15")

    e_before = _ordering_errors(before, schema)
    e_intraday = _ordering_errors(intraday, schema)
    e_control = _ordering_errors(control, schema)

    print(f"closed_at BEFORE created (2026-01-01 < 2026-06-15): {e_before or '(none -> DEFECT)'}")
    print(f"closed_at 08:00 BEFORE created 12:00 same day:       {e_intraday or '(none -> DEFECT)'}")
    print(f"closed_at AFTER created (control):                   {e_control or '(none -> correct)'}")

    ok = bool(e_before) and bool(e_intraday) and not e_control
    print()
    print("PASS: validator flags inverted ordering, leaves valid ordering clean" if ok
          else "FAIL: defect present (inverted closed_at/created not flagged)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
