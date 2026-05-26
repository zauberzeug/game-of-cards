"""Reproduce: emit_frontmatter does not quote scalars the parser won't
round-trip bare.

Two failure modes, one root cause (the quote-trigger predicate is
incomplete):

1. A value beginning with a YAML indicator char (`*`, `&`) is emitted
   bare, and the next parse of that frontmatter CRASHES.
2. A value with leading/trailing whitespace is emitted bare and silently
   stripped on re-parse (data loss).

Exit 0 only if every value survives an emit->parse round-trip unchanged.
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

from goc.engine import emit_frontmatter, parse_frontmatter  # noqa: E402


def main() -> int:
    cases = ["* asterisk start", "&anchor start", "trailing space ", " leading space"]
    all_ok = True
    for val in cases:
        fm = {"title": "t", "summary": val}
        text = emit_frontmatter(fm)
        emitted_line = next(
            (ln for ln in text.splitlines() if ln.startswith("summary:")), "?"
        )
        print(f"=== {val!r} ===")
        print(f"  emitted: {emitted_line!r}")
        try:
            parsed, _body = parse_frontmatter(text)
            got = parsed.get("summary")
            if got == val:
                print(f"  round-trip OK: {got!r}")
            else:
                all_ok = False
                print(f"  DRIFT on re-parse: got {got!r} (lost surrounding whitespace)")
        except Exception as e:  # noqa: BLE001
            all_ok = False
            print(f"  CRASH on re-parse: {type(e).__name__}: {e}")

    print()
    if all_ok:
        print("PASS: every value survived the emit->parse round-trip.")
        return 0
    print("FAIL: emitter produced frontmatter it cannot round-trip (see above).")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
