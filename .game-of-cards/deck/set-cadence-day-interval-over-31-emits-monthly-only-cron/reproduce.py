"""Reproduce: interval_to_cron accepts N-day intervals above 31 and emits a
cron that fires only on the 1st of the month instead of "every N days".

Run: uv run python .game-of-cards/deck/set-cadence-day-interval-over-31-emits-monthly-only-cron/reproduce.py

Exits non-zero while the defect is present (no upper-bound guard), and exits
zero once the day path rejects N > 31 the way the hour path rejects
out-of-range steps.
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


sys.path.insert(0, str(_repo_root() / "scripts"))

from set_cadence import interval_to_cron  # noqa: E402


def step_matches_day_of_month(cron: str) -> list[int]:
    """Return the days 1..31 a `M H */N * *`-style cron actually fires on."""
    fields = cron.split()
    dom = fields[2]  # day-of-month field
    if dom == "*":
        return list(range(1, 32))
    if dom.startswith("*/"):
        step = int(dom[2:])
        return [d for d in range(1, 32) if (d - 1) % step == 0]
    return [int(dom)]


def main() -> int:
    spec = "40d"
    try:
        cron = interval_to_cron(spec, 15)
    except ValueError as exc:
        print(f"interval_to_cron({spec!r}, 15) correctly raised ValueError: {exc}")
        print("PASS: out-of-range day interval is rejected.")
        return 0

    days = step_matches_day_of_month(cron)
    print(f"interval_to_cron({spec!r}, 15) returned {cron!r}")
    print(f"  -> fires on days-of-month: {days}")
    if days == [1]:
        print(
            "FAIL: a 40-day interval collapsed to 'monthly on the 1st' with no error."
        )
        print("      cron's day-of-month field caps at 31; */40 can only match day 1.")
        return 1
    print("UNEXPECTED: 40d did not collapse to day 1 — re-examine.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
