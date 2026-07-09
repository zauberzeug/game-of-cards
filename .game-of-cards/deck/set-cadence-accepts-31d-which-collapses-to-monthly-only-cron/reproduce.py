"""Prove interval_to_cron accepts '31d' while emitting a day-of-month step
that matches only day 1 — the same silent monthly collapse its N > 31 guard
rejects.

Exits zero once '31d' raises ValueError; exits non-zero while the defect is
present.
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT / "scripts"))

import set_cadence as setc  # noqa: E402

try:
    cron = setc.interval_to_cron("31d", 13)
except ValueError as exc:
    print(f"interval_to_cron('31d', 13) raised ValueError: {exc}")
    print("OK: the day-1-only 31d spec is rejected, matching the guard's rationale.")
    sys.exit(0)

step = int(cron.split()[2].lstrip("*/"))
days = [d for d in range(1, 32) if (d - 1) % step == 0]
print(f"interval_to_cron('31d', 13) returned {cron!r}")
print(f"  -> fires on days-of-month: {days}")
if days == [1]:
    print("FAIL: '31d' collapsed to 'monthly on the 1st' with no error — the same")
    print("      day-1-only collapse the N > 31 guard rejects.")
    sys.exit(1)

print("UNEXPECTED: 31d fires on more than day 1; re-examine the claim.")
sys.exit(2)
