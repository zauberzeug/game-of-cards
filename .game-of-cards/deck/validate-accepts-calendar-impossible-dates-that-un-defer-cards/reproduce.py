"""Reproduce: goc validate accepts calendar-impossible dates that un-defer cards.

A `waiting_until` like `2026-13-45` matches the validator's regex-only date
predicate (`_is_iso_date`) and so passes `goc validate`. But the read-time
guard `waiting_impedes` parses it with `date.fromisoformat`, fails, and — for a
bare deferral with no `waiting_on` — silently treats the card as NOT impeded,
re-admitting it to the pull queue.

Defect fires (exit 1) while the validator predicate is weaker than the parser.
After the fix (tighten `_is_iso_date` to parse the calendar), this exits 0.
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

from goc.engine import Card, _is_iso_date, waiting_impedes  # noqa: E402

IMPOSSIBLE = "2026-13-45"  # month 13, day 45 — ISO-shaped, calendar-impossible
VALID_FUTURE = "2099-01-01"


def _card(fm: dict) -> Card:
    return Card(
        title=fm.get("title", "x"),
        path=Path("."),
        frontmatter=fm,
        body="",
        dod_open=0,
        dod_done=0,
    )


def main() -> int:
    today = date(2026, 1, 1)

    # Chosen contract (both sides — belt and suspenders):
    #   1. `_is_iso_date` is the validator's net: it must REJECT a
    #      calendar-impossible ISO-shaped value (predicate == parser).
    #   2. `waiting_impedes` is the read-time backstop: a bare deferral with
    #      an unparseable date stays impeded (no silent un-defer) for decks
    #      that predate the tightened validator.
    predicate_accepts = _is_iso_date(IMPOSSIBLE)
    bad_bare_impedes = waiting_impedes(
        _card({"waiting_until": IMPOSSIBLE}), today=today
    )
    valid_bare_impedes = waiting_impedes(
        _card({"waiting_until": VALID_FUTURE}), today=today
    )
    valid_predicate = _is_iso_date(VALID_FUTURE)
    valid_datetime_predicate = _is_iso_date("2026-05-10T00:00:00Z")

    print(f"_is_iso_date({IMPOSSIBLE!r}): {predicate_accepts}   (want False)")
    print(f"_is_iso_date({VALID_FUTURE!r}): {valid_predicate}   (control: True)")
    print(
        f"_is_iso_date('2026-05-10T00:00:00Z'): {valid_datetime_predicate}"
        "   (control: True)"
    )
    print(
        f"waiting_impedes(bare deferral, waiting_until={IMPOSSIBLE!r}): "
        f"{bad_bare_impedes}   (want True — stays deferred)"
    )
    print(
        f"waiting_impedes(bare deferral, waiting_until={VALID_FUTURE!r}): "
        f"{valid_bare_impedes}   (control: True)"
    )

    # Controls must always hold — no regression for genuinely valid shapes.
    assert valid_predicate is True, "control regressed: valid date rejected"
    assert valid_datetime_predicate is True, "control regressed: valid datetime rejected"
    assert valid_bare_impedes is True, "control regressed: valid future date no longer impedes"

    ok = (predicate_accepts is False) and (bad_bare_impedes is True)
    if not ok:
        print(
            "\nDEFECT: validate accepts a calendar-impossible waiting_until "
            "and/or the bare-deferral card silently re-enters the pull queue."
        )
        return 1

    print(
        "\nOK: calendar-impossible dates are rejected by the validator "
        "predicate, and the bare deferral holds at read time."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
