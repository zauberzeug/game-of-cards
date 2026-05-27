"""Reproduce: a malformed `waiting_until` whose first 10 chars form a valid
calendar date is silently un-deferred by the read-time guard `waiting_impedes`,
even though `goc validate` (`_is_iso_date`) rejects the same value.

Root cause: `_date_part` prefix-truncates any >=10-char string to its first 10
chars, so `date.fromisoformat(_date_part("2026-05-20xx"))` parses cleanly to
2026-05-20 instead of raising. The malformed-impede branch installed by the
closed card `waiting-impedes-treats-malformed-waiting-until-as-no-impediment`
is therefore unreachable for prefix-valid garbage.

Run: uv run python deck/<title>/reproduce.py
Defect fires if the prefix-garbage card reports impeded=False while the
validator rejects the same value.
"""
import sys
from datetime import date
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc.engine import Card, _date_part, _is_iso_date, waiting_impedes  # noqa: E402

TODAY = date(2026, 5, 27)


def mk(value):
    return Card(
        title="t",
        path=Path("."),
        frontmatter={"waiting_on": "external", "waiting_until": value},
        body="",
        dod_open=1,
        dod_done=0,
    )


def main() -> int:
    prefix_garbage = "2026-05-20xx"   # validator rejects; first 10 chars valid past date
    total_garbage = "not-a-date"       # validator rejects; cannot be parsed at all

    print("== input the validator rejects ==")
    print(f"  _is_iso_date({prefix_garbage!r}) = {_is_iso_date(prefix_garbage)}")
    print(f"  _date_part({prefix_garbage!r})   = {_date_part(prefix_garbage)!r}")
    print()

    pg_impeded = waiting_impedes(mk(prefix_garbage), today=TODAY)
    tg_impeded = waiting_impedes(mk(total_garbage), today=TODAY)
    none_impeded = waiting_impedes(mk(None), today=TODAY)  # bare reason -> impeded

    print("== waiting_impedes (today = 2026-05-27) ==")
    print(f"  prefix-garbage '2026-05-20xx' -> impeded={pg_impeded}  (EXPECTED True)")
    print(f"  total-garbage  'not-a-date'   -> impeded={tg_impeded}  (control: True)")
    print(f"  no date, reason set           -> impeded={none_impeded}  (control: True)")
    print()

    # The contract: a value the validator rejects must NOT be treated as a
    # usable date by the read-time guard. A card with waiting_on=external and a
    # rejected waiting_until must stay impeded (same as the total-garbage case).
    defect = (not pg_impeded) and tg_impeded and none_impeded
    if defect:
        print("DEFECT CONFIRMED: prefix-valid garbage un-defers the card "
              "(impeded=False) while total garbage and bare-reason both impede.")
        return 1
    print("No defect: prefix-garbage impedes like every other rejected value.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
