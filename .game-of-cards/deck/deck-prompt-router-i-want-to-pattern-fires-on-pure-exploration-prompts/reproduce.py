"""Prove that `deck_prompt_router` fires the GoC reminder on pure-exploration prompts.

The hook's docstring states it stays silent for "pure exploration /
explanation / one-shot tooling". This reproducer feeds six prompts to the
hook and asserts:

- Five prompts that are unambiguously exploration ("I want to understand …",
  "I want to know …", "I want to learn …", "we need to investigate …",
  "explain how to implement …") DO fire the reminder — the defect.
- One prompt that uses an opener outside the offending regexes
  ("we should review …") stays silent — the contrast case.

Exits 0 once the hook stops firing on the four `I want/need to` / `we
need/should/want to` exploration prompts (i.e. when at least four of the
five "FIRE expected → silent observed" assertions flip). Today the script
prints the as-found failure list and exits non-zero.
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

# Each case: (prompt, expected_silent_after_fix, label)
CASES: list[tuple[str, bool, str]] = [
    ("i want to understand how authentication works in this codebase", True, "exploration: understand"),
    ("we need to investigate why the parser drops blank lines",        True, "exploration: investigate"),
    ("i want to know what happens when a card has no DoD",             True, "exploration: know"),
    ("I want to learn about the deck design",                          True, "exploration: learn"),
    ("explain how to implement an auth flow",                          True, "exploration: explain (with 'implement')"),
    ("we should review the recent commits",                            True, "exploration: review (contrast — already silent today)"),

    # Regression guards — these MUST keep firing after any fix.
    ("rename the button to Export",                                    False, "work: rename"),
    ("add a CSV export",                                               False, "work: add"),
    ("fix the auth bug",                                               False, "work: fix"),
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
    print(f"Probing {HOOK.relative_to(ROOT)} with {len(CASES)} prompts:\n")
    failures: list[str] = []
    for prompt, want_silent, label in CASES:
        fires = _fires(prompt)
        want_fires = not want_silent
        ok = fires == want_fires
        verdict = "OK" if ok else "BUG"
        print(f"  [{verdict}] {label}: fires={fires} (want fires={want_fires})")
        print(f"        prompt: {prompt!r}")
        if not ok:
            failures.append(label)

    print()
    if failures:
        print(f"DEFECT: {len(failures)} prompt(s) classified incorrectly: {failures}")
        return 1
    print("OK: every prompt classified as the contract requires.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
