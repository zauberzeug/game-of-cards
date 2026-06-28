"""Reproduce: `--closed-since <huge-window>` crashes with an OverflowError.

`parse_closed_since` validates the syntax of a relative window
(`<N>[h|d|w]`) and rejects non-positive N with a clean `goc: error:` /
exit 2, but applies no upper bound before constructing the timedelta. A
syntactically valid but very large window overflows `timedelta` and the
CLI dies with an uncaught traceback instead of the clean exit-2 error
every other bad `--closed-since` input produces.

Expected (after fix): an out-of-range window exits 2 with a
`goc: error: --closed-since: ...` message — never a traceback.
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

from goc.engine import parse_closed_since


def main() -> int:
    try:
        result = parse_closed_since("99999999999w")
    except SystemExit as exc:
        print(f"OK: clean exit({exc.code}) on out-of-range window")
        return 0 if exc.code == 2 else 1
    except OverflowError as exc:
        print(f"DEFECT CONFIRMED: OverflowError instead of clean exit 2 -> {exc}")
        return 1
    print(f"DEFECT? returned {result!r} without bounding the window")
    return 1


if __name__ == "__main__":
    sys.exit(main())
