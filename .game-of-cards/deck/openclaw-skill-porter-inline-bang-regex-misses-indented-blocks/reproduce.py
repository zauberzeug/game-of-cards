"""Prove the OpenClaw skill porter leaves indented `!`-prefixed backtick
blocks un-neutralized in the ported output.

`INLINE_BANG_BLOCK_RE` in scripts/port_skills_to_openclaw.py anchors at
column 0 (`^!\\``), so an inline pre-exec block that sits inside an
indented list item survives the port verbatim. OpenClaw has no `!`
pre-execute syntax, so the shipped skill carries dead Claude Code-only
syntax at the exact step whose instructions depend on its output.

Exits non-zero while the defect fires; exits zero once every ported
SKILL.md is free of `!`-prefixed backtick blocks at any indentation.
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


ROOT = _repo_root()
sys.path.insert(0, str(ROOT / "scripts"))

from port_skills_to_openclaw import SRC_DIR, render_skill  # noqa: E402

BANG_LINE = re.compile(r"^[ \t]*!`")

failures = []
for skill_md in sorted(SRC_DIR.glob("*/SKILL.md")):
    ported = render_skill(skill_md)
    for lineno, line in enumerate(ported.splitlines(), start=1):
        if BANG_LINE.match(line):
            failures.append((skill_md.parent.name, lineno, line))

if failures:
    for name, lineno, line in failures:
        print(f"DEFECT: ported {name}/SKILL.md line {lineno} keeps pre-exec syntax: {line!r}")
    sys.exit(1)

print("OK: no ported SKILL.md line carries a `!`-prefixed backtick block")
