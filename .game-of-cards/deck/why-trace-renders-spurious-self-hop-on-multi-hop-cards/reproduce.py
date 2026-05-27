"""Reproduce the spurious '→ self (?)' hop in the WHY-trace renderer.

A leaf card terminates its value path with the sentinel ["self"]
(engine.py compute_values). Every ancestor *prepends* its descendant
slug, so the sentinel rides along in the tail of every multi-hop path
(e.g. ["B", "C", "self"]). `_format_why` only suppresses the exact leaf
path ["self"], so longer paths render a bogus '→ self (?)' hop.

Exits 0 when the renderer is correct (no trailing self hop), 1 when the
defect is present.
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

from goc.engine import _format_why  # noqa: E402


class _Stub:
    def __init__(self, contribution: str) -> None:
        self.contribution = contribution


def main() -> int:
    by_title = {"B": _Stub("low"), "C": _Stub("low")}

    # A 3-hop chain A -> B -> C(leaf) yields top_path ["B", "C", "self"].
    three_hop = _format_why(["B", "C", "self"], by_title)
    two_hop = _format_why(["C", "self"], by_title)
    leaf = _format_why(["self"], {})
    cycle = _format_why(["cycle"], {})

    print(f"A 3-hop: {three_hop!r}")
    print(f"B 2-hop: {two_hop!r}")
    print(f"leaf   : {leaf!r}")
    print(f"cycle  : {cycle!r}")

    expected_three = "→ B (low) → C (low)"
    expected_two = "→ C (low)"

    failures = []
    if "self" in three_hop or three_hop != expected_three:
        failures.append(f"3-hop: got {three_hop!r}, want {expected_three!r}")
    if "self" in two_hop or two_hop != expected_two:
        failures.append(f"2-hop: got {two_hop!r}, want {expected_two!r}")
    if leaf != "":
        failures.append(f"leaf: got {leaf!r}, want ''")
    if cycle != "(cycle)":
        failures.append(f"cycle: got {cycle!r}, want '(cycle)'")

    if failures:
        print("\nDEFECT PRESENT — spurious 'self' hop or contract regression:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("\nOK — no spurious 'self' hop; WHY trace matches the contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
