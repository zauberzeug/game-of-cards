#!/usr/bin/env python3
"""Reproduce: yaml-lite flow mapping drops `key:value` pairs lacking a space after the colon.

Before the fix, `_parse_flow_mapping` splits each pair on the literal `": "`,
so a hand-written mapping like `{who:rodja, where:foo}` (no space) yields an
empty mapping. After the fix, the parser splits on the first `:` with optional
surrounding whitespace.

Exit 0 = fixed, exit 1 = defect present.
"""
from goc._vendor import yaml_lite


def main() -> int:
    # No space after the colon — the regression case.
    got = yaml_lite.safe_load("w: {who:a, where:b}")
    want = {"w": {"who": "a", "where": "b"}}
    if got != want:
        print(f"FAIL (no-space): expected {want!r}, got {got!r}")
        return 1

    # Space after the colon must still parse (no regression).
    got = yaml_lite.safe_load("w: {who: a, where: b}")
    if got != want:
        print(f"FAIL (with-space regression): expected {want!r}, got {got!r}")
        return 1

    # Mixed spacing in a single mapping.
    got = yaml_lite.safe_load("w: {who:a, where: b}")
    if got != want:
        print(f"FAIL (mixed): expected {want!r}, got {got!r}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
