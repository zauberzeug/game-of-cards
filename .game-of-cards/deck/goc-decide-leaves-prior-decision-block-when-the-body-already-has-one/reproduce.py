"""Reproduce: `replace_or_append_decision` leaves a prior `## Decision` block
when the body carries both a resolved decision AND a re-raised `## Decision
required` section. Run via `uv run python deck/<title>/reproduce.py`.

Exits 1 on the defect (two `## Decision` headings produced); 0 once the engine
keeps exactly one.
"""

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


sys.path.insert(0, str(_repo_root()))

from goc.engine import replace_or_append_decision  # noqa: E402


BODY = """
## Background

Some framing.

## Decision required

A re-raised question.

## Decision

*Resolved 2026-04-01:* old-answer

*Reasoning:* old reason

## Aftermath

Subsequent prose.
"""


def main() -> int:
    out = replace_or_append_decision(BODY, "new-answer", "new reason", "2026-05-30")
    headings = re.findall(r"^## Decision(?: |\n|$)", out, re.MULTILINE)
    n = len(headings)
    print(f"Decision heading count after replace_or_append_decision: {n}")
    if n == 1:
        print("expected 1, got 1 — OK")
        return 0
    print(f"expected 1, got {n} — FAIL")
    print("---- produced body ----")
    print(out)
    return 1


if __name__ == "__main__":
    sys.exit(main())
