"""Reproduce the phantom '→ cycle (?)' hop in the WHY-trace renderer.

On a cyclic `advances` deck, `compute_values` returns the sentinel
["cycle"] when a descendant re-enters an in-progress node. Every
ancestor *prepends* its descendant slug, so the sentinel rides along in
the tail of every multi-hop path (e.g. ["C", "A", "cycle"]).
`_format_why` only special-cased the exact singleton ["cycle"], so a
longer path ending in `cycle` rendered a phantom '→ cycle (?)' hop —
the same class as the sibling 'self' bug fixed in cc2d4ce.

Exits 0 when the renderer is correct (no phantom cycle hop, cycle still
signalled), 1 when the defect is present.
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
    by_title = {"A": _Stub("med"), "C": _Stub("low")}

    # A cyclic chain (C advances A, A advances C) yields a multi-hop
    # top_path whose tail is the "cycle" sentinel, e.g. ["C", "A", "cycle"].
    multi_cycle = _format_why(["C", "A", "cycle"], by_title)
    one_hop_cycle = _format_why(["A", "cycle"], by_title)
    singleton_cycle = _format_why(["cycle"], {})

    # Regression: non-cyclic paths and the self sentinel are unchanged.
    valid_chain = _format_why(["C", "A"], by_title)
    self_leaf = _format_why(["self"], {})
    self_multi = _format_why(["C", "A", "self"], by_title)

    print(f"multi cycle    : {multi_cycle!r}")
    print(f"one-hop cycle  : {one_hop_cycle!r}")
    print(f"singleton cycle: {singleton_cycle!r}")
    print(f"valid chain    : {valid_chain!r}")
    print(f"self leaf      : {self_leaf!r}")
    print(f"self multi     : {self_multi!r}")

    failures = []
    # No phantom '→ cycle (?)' hop on any multi-hop path.
    if "→ cycle" in multi_cycle or multi_cycle != "→ C (low) → A (med) (cycle)":
        failures.append(f"multi cycle: got {multi_cycle!r}, want '→ C (low) → A (med) (cycle)'")
    if "→ cycle" in one_hop_cycle or one_hop_cycle != "→ A (med) (cycle)":
        failures.append(f"one-hop cycle: got {one_hop_cycle!r}, want '→ A (med) (cycle)'")
    # The singleton still renders the bare cycle label.
    if singleton_cycle != "(cycle)":
        failures.append(f"singleton cycle: got {singleton_cycle!r}, want '(cycle)'")
    # Valid multi-hop and self handling unchanged.
    if valid_chain != "→ C (low) → A (med)":
        failures.append(f"valid chain: got {valid_chain!r}, want '→ C (low) → A (med)'")
    if self_leaf != "":
        failures.append(f"self leaf: got {self_leaf!r}, want ''")
    if "self" in self_multi or self_multi != "→ C (low) → A (med)":
        failures.append(f"self multi: got {self_multi!r}, want '→ C (low) → A (med)'")

    if failures:
        print("\nDEFECT PRESENT — phantom 'cycle' hop or contract regression:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("\nOK — no phantom 'cycle' hop; WHY trace matches the contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
