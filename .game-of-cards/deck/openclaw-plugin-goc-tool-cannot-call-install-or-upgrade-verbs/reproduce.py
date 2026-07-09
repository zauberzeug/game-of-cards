"""Prove the OpenClaw goc tool schema cannot express the `goc install` /
`goc upgrade` invocations the plugin's own ported kickoff skills instruct.

Exits non-zero while the defect is present.
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

index_ts = (ROOT / "openclaw-plugin" / "index.ts").read_text(encoding="utf-8")
m = re.search(r"const GOC_VERBS = \[(.*?)\] as const;", index_ts, re.DOTALL)
if not m:
    print("GOC_VERBS literal not found in openclaw-plugin/index.ts")
    sys.exit(2)
verbs = [t.strip().strip('"').strip("'") for t in m.group(1).split(",") if t.strip()]
print(f"GOC_VERBS ({len(verbs)}): {', '.join(verbs)}")

missing = sorted({"install", "upgrade"} - set(verbs))

sites = 0
for skill in ("kickoff", "openclaw-kickoff"):
    path = ROOT / "openclaw-plugin" / "skills" / skill / "SKILL.md"
    sites += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if "goc install" in line)
print(f"ported kickoff skills instruct `goc install` at {sites} site(s)")

if missing and sites:
    print(f"missing from GOC_VERBS: {missing}")
    print("FAIL: the shipped onboarding flow is unexpressible through the shipped tool schema.")
    sys.exit(1)

print("OK: tool schema and shipped kickoff instructions are consistent.")
sys.exit(0)
