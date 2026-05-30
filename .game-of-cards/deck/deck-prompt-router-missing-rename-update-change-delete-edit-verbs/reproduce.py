"""Prove that `deck_prompt_router` no longer fires on rename/update/change/delete/move edit prompts.

The closed card `prompt-hook-misses-rename-work-requests` (done 2026-05-05)
established the contract: edit-style work prompts MUST fire the GoC reminder.
A stale-tree merge orphaned that fix when the hook file was renamed; the
shipping `deck_prompt_router.py` is missing the rename / update / change /
delete / remove / move verbs from its WORK_INITIATING list.

This reproducer feeds the canonical AGENTS examples plus four sibling
edit verbs to the hook and asserts every one fires the reminder. Exits 0
once all seven prompts fire; exits 1 with the failure list today.
"""

from __future__ import annotations

import json
import subprocess
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
sys.path.insert(0, str(ROOT))

HOOK = ROOT / "goc" / "templates" / "hooks" / "deck_prompt_router.py"

# Each case must fire the reminder. The first three are the canonical
# AGENTS_GOC.md examples; the next four are sibling edit verbs that the
# orphaned-fix commit (14864cc) added before the rename to deck_prompt_router.
CASES: list[tuple[str, str]] = [
    ("rename the button to Export",   "canonical: rename"),
    ("add a CSV export",              "canonical: add"),
    ("fix the auth bug",              "canonical: fix"),
    ("update the timeout to 30s",     "sibling: update"),
    ("change the default port",       "sibling: change"),
    ("delete the legacy module",      "sibling: delete"),
    ("move the helper to utils/",     "sibling: move"),
]


def _fires(prompt: str) -> bool:
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"prompt": prompt}),
        capture_output=True,
        text=True,
        check=True,
    )
    return "Game of Cards | runtime active" in r.stdout


def main() -> int:
    print(f"Probing {HOOK.relative_to(ROOT)} with {len(CASES)} edit-style work prompts:\n")
    failures: list[str] = []
    for prompt, label in CASES:
        fires = _fires(prompt)
        verdict = "OK " if fires else "BUG"
        print(f"  [{verdict}] {label}: fires={fires} (want=True): {prompt!r}")
        if not fires:
            failures.append(label)

    print()
    if failures:
        print(f"DEFECT: {len(failures)} edit-verb prompt(s) silently classified as non-work: {failures}")
        return 1
    print("OK: every canonical edit-verb prompt fires the GoC reminder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
