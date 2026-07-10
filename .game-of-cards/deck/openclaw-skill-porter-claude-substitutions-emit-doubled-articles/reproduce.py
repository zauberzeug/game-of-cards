"""Prove the OpenClaw skill porter's Claude substitutions ship ungrammatical
text: doubled articles ("the the agent", "a the host") and sentence-initial
lowercase replacements ("**...** the host gates").

Exits non-zero while any artifact is present in openclaw-plugin/skills/.
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
SKILLS = ROOT / "openclaw-plugin" / "skills"

doubled = re.compile(r"\bthe the\b|\ba the\b")
# A replacement dropped at sentence start: terminator (or bold-run end) then
# a lowercase "the host"/"the agent" opening the next sentence.
midcase = re.compile(r"(?:[.!?]\*{0,2}) (?:the host|the agent)\b")

hits = []
for path in sorted(SKILLS.rglob("*.md")):
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        for pattern, kind in ((doubled, "doubled-article"), (midcase, "sentence-initial-lowercase")):
            m = pattern.search(line)
            if m:
                hits.append((kind, path.relative_to(ROOT), lineno, line.strip()))

for kind, rel, lineno, line in hits:
    print(f"{kind}: {rel}:{lineno}: {line}")

if hits:
    print(f"FAIL: {len(hits)} ungrammatical substitution artifact(s) in ported skills.")
    sys.exit(1)

print("OK: no doubled-article or sentence-initial-lowercase artifacts found.")
sys.exit(0)
