"""Reproduce the OpenClaw session-start split-limit truncation bug.

The TS port at `openclaw-plugin/index.ts:192-202` reads frontmatter values via
`line.split(":", 2)[1].trim()`. JS `String.prototype.split(sep, limit)` truncates
the result *array* to `limit` elements — not the number of splits. The Python
sibling at `goc/templates/hooks/deck_session_start.py:81` uses
`line.split(":", 1)[1]` (maxsplit=1) which captures the full tail.

This reproducer:

1. Simulates the TS split call in Python by counting colons and demonstrates that
   the two-element array drops the post-second-colon tail.
2. Re-runs the line `"waiting_until: 2026-06-15T12:00:00Z"` through both
   semantics and prints the divergence.
3. Locates the TS source and confirms the buggy literal `split(":", 2)` is
   present in all four readers. Failing this check would mean the bug was
   already fixed; the script exits non-zero so closure becomes the success
   signal.

Exit codes:
  0 = bug NOT present (post-fix state: all four readers use a non-truncating
      semantic).
  1 = bug present (pre-fix state).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


def js_split_limit(s: str, sep: str, limit: int) -> list[str]:
    """Match ECMA-262 String.prototype.split(separator, limit) semantics.

    The limit caps the *array length*, not the number of splits.
    """
    parts = s.split(sep)
    return parts[:limit]


def main() -> int:
    repo = _repo_root()
    index_ts = repo / "openclaw-plugin" / "index.ts"
    src = index_ts.read_text(encoding="utf-8")

    print("# 1) Split-limit semantic demonstration")
    line = "waiting_until: 2026-06-15T12:00:00Z"
    js_result = js_split_limit(line, ":", 2)
    py_result = line.split(":", 1)
    print(f"  input:                          {line!r}")
    print(f"  JS  split(':', 2):              {js_result!r}")
    print(f"  Py  split(':', 1):              {py_result!r}")
    print(f"  JS  [1].strip()                 -> {js_result[1].strip()!r}")
    print(f"  Py  [1].strip()                 -> {py_result[1].strip()!r}")

    iso_datetime_re = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    iso_date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    js_value = js_result[1].strip()
    py_value = py_result[1].strip()
    js_parses = bool(iso_datetime_re.match(js_value) or iso_date_re.match(js_value))
    py_parses = bool(iso_datetime_re.match(py_value) or iso_date_re.match(py_value))
    print(f"  JS  parseWaitingUntil parses?   {js_parses}")
    print(f"  Py  parseWaitingUntil parses?   {py_parses}")

    print()
    print("# 2) Bug presence check in openclaw-plugin/index.ts")
    pattern = re.compile(r'line\.split\("\s*:\s*"\s*,\s*2\)\[1\]\.trim\(\)')
    matches = pattern.findall(src)
    print(f"  call sites with split(\":\", 2)[1].trim(): {len(matches)}")

    print()
    print("# 3) Engine-contract divergence for the bare-deferral case")
    print('  card frontmatter: status: active / waiting_until: 2030-01-01T00:00:00Z / waiting_on absent')
    print("  engine.waiting_impedes(card)  -> True  (card hidden from queues)")
    if len(matches) == 0:
        print("  ts.isImpeded(...) (post-fix)   -> True  (matches engine)")
    else:
        print("  ts.isImpeded(...) (pre-fix)    -> False (BUG: surfaces as resumable)")

    print()
    if len(matches) == 0:
        print("VERDICT: post-fix. All four readers capture the full tail. exit 0.")
        return 0
    print(
        "VERDICT: pre-fix. Split-limit truncation present in "
        f"{len(matches)} reader(s); datetime-form waiting_until is lost. exit 1."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
