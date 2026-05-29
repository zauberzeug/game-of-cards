"""Reproduce: skill bodies still describe the queue sort as
"impact-sorted" / "Impact ladder" / "sorted by impact desc" after the
sibling card renamed the `impact:` field references to `contribution:`.
The engine sorts by GRPW `value` built from `CONTRIBUTION_RANK`, and no
"impact" concept exists in `engine.py`, `schema.yaml`, or `cli.py`.

Exit code 0 means the defect is FIXED (no surviving "impact"-as-sort-name
prose remains in the audited skill bodies). Exit code 1 means the defect
is LIVE.
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


REPO = _repo_root()

# Phrases that describe the queue's sort dimension as "impact".
# Each pattern is a verbatim quote from a current SKILL body. Adjective
# uses ("research-impacting", "high-impact seams") are NOT in this set —
# they don't claim the engine sorts by an impact field.
DRIFT_PATTERNS = [
    r"impact-sorted",
    r"sorted by impact",
    r"Impact ladder",
    r"impact, why it's the highest-leverage",
]

AUDIT_FILES = [
    "goc/templates/skills/next-card/SKILL.md",
    "goc/templates/skills/deck/SKILL.md",
    "goc/templates/skills/audit-deck/SKILL.md",
]

ENGINE_SOURCES = [
    "goc/engine.py",
    "goc/schema.yaml",
    "goc/cli.py",
]


def main() -> int:
    print("Engine source-of-truth — bare 'impact' token search:")
    engine_hits = 0
    for src in ENGINE_SOURCES:
        text = (REPO / src).read_text()
        hits = re.findall(r"\bimpact\b", text)
        print(f"  {src}: {len(hits)} occurrences")
        engine_hits += len(hits)
    print(f"  TOTAL: {engine_hits} (any non-zero contradicts the skill prose)")
    print()

    print("Skill bodies — drift-phrase hits:")
    total_drift = 0
    for rel in AUDIT_FILES:
        path = REPO / rel
        lines = path.read_text().splitlines()
        for i, ln in enumerate(lines, 1):
            for pat in DRIFT_PATTERNS:
                if re.search(pat, ln):
                    print(f"  {rel}:{i}: {ln.strip()}")
                    total_drift += 1
                    break
    print(f"  TOTAL drift hits: {total_drift}")
    print()

    if engine_hits == 0 and total_drift == 0:
        print("PASS: engine has no 'impact' concept and skill prose no longer claims it does.")
        return 0
    print("FAIL: skill prose still names a sort dimension the engine does not have.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
