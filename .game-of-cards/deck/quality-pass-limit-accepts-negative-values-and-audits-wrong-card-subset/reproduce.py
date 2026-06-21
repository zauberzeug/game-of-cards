"""Reproduce: `goc quality-pass --limit` accepts negative values.

A count flag must reject negatives the way the peer `--max-rows` flag
already does. Before the fix, the parser accepts `--limit -2` (and `0`),
which then flows into `cards[:limit]` and audits the wrong subset.

Exits zero once the defect is fixed (negative `--limit` is rejected at
the argparse layer); exits non-zero while the defect is present.
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

import argparse

from goc.engine import _build_parser

parser = _build_parser()

failures = []

# 1. Negative --limit must be rejected, exactly like --max-rows.
try:
    parser.parse_args(["quality-pass", "--limit", "-2"])
    failures.append(
        "quality-pass --limit -2 was ACCEPTED; expected a non-negative-integer error"
    )
    accepted_negative = True
except SystemExit:
    accepted_negative = False
    print("OK: quality-pass --limit -2 rejected at argparse layer")

# 2. Demonstrate the silent-mis-slice the unguarded converter enables.
sample = ["a", "b", "c", "d", "e"]
print(f"slice demo: cards[:-2] = {sample[:-2]}  (drops the last 2, not a cap)")
print(f"slice demo: cards[:0]  = {sample[:0]}  (audits nothing)")

# 3. Non-negative values must still parse fine.
for good in ["0", "3"]:
    try:
        ns = parser.parse_args(["quality-pass", "--limit", good])
        assert ns.limit == int(good)
        print(f"OK: quality-pass --limit {good} parses to {ns.limit}")
    except SystemExit:
        failures.append(f"quality-pass --limit {good} was rejected; expected success")

if failures:
    print("\nDEFECT PRESENT:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)

print("\nAll checks passed: --limit rejects negatives and accepts non-negatives.")
sys.exit(0)
