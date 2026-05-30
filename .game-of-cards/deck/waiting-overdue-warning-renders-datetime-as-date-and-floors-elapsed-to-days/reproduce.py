"""Reproducer for the WAITING_OVERDUE rendering precision drop.

`validate_waiting_overlay` decides overdue-ness at full datetime precision
(its docstring at engine.py:1469-1472 explicitly defends this), but the
rendered warning string at engine.py:1493-1498 calls `until_dt.date().isoformat()`
and `(now - until_dt).days`, collapsing sub-day precision back to date+integer-days.

This script constructs a non-terminal card whose `waiting_until` is a
datetime in the recent past, runs `validate_waiting_overlay`, and prints
what the operator would see.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc.engine import Card, validate_waiting_overlay  # noqa: E402


def main() -> int:
    until_str = "2026-05-30T23:00:00Z"
    now = datetime(2026, 5, 31, 0, 30, tzinfo=timezone.utc)
    until_dt = datetime.strptime(until_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    actual_elapsed = now - until_dt

    fm = {
        "title": "test-card",
        "status": "open",
        "contribution": "medium",
        "human_gate": "none",
        "waiting_on": "external",
        "waiting_until": until_str,
        "advances": [],
        "advanced_by": [],
        "tags": [],
        "definition_of_done": "- [ ] x",
    }
    card = Card(
        title="test-card",
        path=Path("/dev/null"),
        frontmatter=fm,
        body="",
        dod_open=1,
        dod_done=0,
    )

    warnings = validate_waiting_overlay([card], today=now)
    assert len(warnings) == 1, f"predicate must fire — got {warnings}"
    msg = warnings[0].message

    hours = actual_elapsed.total_seconds() / 3600
    fractional_days = actual_elapsed.total_seconds() / 86400

    print(f"stored waiting_until  : {until_str}")
    print(f"comparison instant    : {now.isoformat()}")
    print(f"actual elapsed        : {hours:.2f}h  ({fractional_days:.4f} days)")
    print(f"predicate fires?      : True")
    print(f"rendered warning      : {msg!r}")
    print(f"contains stored time? : {('T23:00:00Z' in msg)}")
    print(f"shows fractional day? : {('0d ago' not in msg)}")
    print()

    failures = []
    if "T23:00:00Z" in msg:
        print("PASS: rendered message echoes the stored datetime")
    else:
        failures.append("rendered message dropped the time component — "
                        "got date-only form despite a datetime input")
    if "0d ago" in msg:
        failures.append("elapsed rendered as '0d ago' for a 1h30m overrun — "
                        "sub-day precision was floored away")
    else:
        print("PASS: elapsed rendered with sub-day granularity")

    if failures:
        print()
        print("DEFECT CONFIRMED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
