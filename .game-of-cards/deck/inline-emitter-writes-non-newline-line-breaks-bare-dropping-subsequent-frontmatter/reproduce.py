"""Proof: a single-line frontmatter scalar containing a non-LF line-break
character (CR, VT, FF, FS, GS, RS, NEL, LS, PS) is emitted *bare* by
`_yaml_inline`, then silently truncated on re-parse — dropping the rest of the
value AND every frontmatter field below it.

The emitter's guard (`engine.py:237`) checks only `"\n" in s`. The vendored
parser splits the document with `str.splitlines()`, which treats nine *other*
characters as line breaks. None of them is caught by the guard or the
quote-trigger, so the scalar round-trips lossily and without any error.
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

# The nine non-LF characters str.splitlines() treats as line breaks.
NON_LF_BREAKS = {
    "CR": "\r",
    "VT": "\x0b",
    "FF": "\x0c",
    "FS": "\x1c",
    "GS": "\x1d",
    "RS": "\x1e",
    "NEL": "\x85",
    "LS": " ",
    "PS": " ",
}

any_fail = False
for name, ch in NON_LF_BREAKS.items():
    fm = {
        "title": "demo",
        "status": "open",
        "summary": f"line one{ch}line two",
        "tags": "[bug]",
        "advances": ["some-other-card"],
    }
    emitted = emit_frontmatter(fm)
    parsed, _ = parse_frontmatter(emitted)

    summary_ok = parsed.get("summary") == fm["summary"]
    tail_fields_ok = "advances" in parsed and "tags" in parsed
    quoted = f'"' in emitted.split("summary:", 1)[1].split("\n", 1)[0]

    fail = not summary_ok or not tail_fields_ok
    any_fail = any_fail or fail
    print(
        f"{name:>4}: summary_preserved={summary_ok!s:>5} "
        f"tail_fields_preserved={tail_fields_ok!s:>5} "
        f"emitted_quoted={quoted!s:>5}  -> {'FAIL' if fail else 'ok'}"
    )

print()
print("DEFECT REPRODUCED" if any_fail else "no defect (fix is in place)")
sys.exit(1 if any_fail else 0)
