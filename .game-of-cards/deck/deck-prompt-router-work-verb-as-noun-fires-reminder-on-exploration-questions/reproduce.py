"""Reproduce: the deck_prompt_router WORK_INITIATING pattern
`\\b({WORK_VERBS})\\s+\\w` (line 28) fires the GoC work reminder on pure
exploration questions where a work verb appears as a *noun*.

The hook's docstring promises it is "Silent for pure exploration /
explanation". But a question like "how does the update logic work?" contains
the work verb `update` followed by a word, so `has_work` is True; the
precedence rule (`(exploration or tooling) and not has_work`) then lets work
win over the matched exploration pattern, and the REMINDER is injected.

Run: uv run python .game-of-cards/deck/<this-card>/reproduce.py
Exit 0 == defect fixed (none of the exploration prompts fire).
Exit 1 == defect present (at least one exploration prompt fires).
"""

import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
HOOK = ROOT / "goc" / "templates" / "hooks" / "deck_prompt_router.py"

# Pure-exploration prompts. Each contains a WORK_VERB used as a noun, never as
# an imperative. The hook should stay SILENT on all of them.
EXPLORATION_PROMPTS = [
    "how does the update logic work?",
    "what does the move command do?",
    "explain the rename function",
    "what is the build pipeline?",
    "how does add work in this codebase?",
]

# Canonical work prompts. The hook MUST keep firing on these — the fix must not
# regress real work-initiation detection.
WORK_PROMPTS = [
    "rename the button to Export",
    "add a CSV export",
    "fix the auth bug",
]


def _fires(prompt: str) -> bool:
    """True if the hook injects the reminder for `prompt`."""
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"prompt": prompt}),
        capture_output=True,
        text=True,
    )
    return "[Game of Cards | runtime active]" in proc.stdout


def main() -> int:
    print(f"hook: {HOOK.relative_to(ROOT)}\n")

    false_positives = []
    print("Pure-exploration prompts (should be SILENT):")
    for prompt in EXPLORATION_PROMPTS:
        fired = _fires(prompt)
        verdict = "FIRES (bug)" if fired else "silent (ok)"
        print(f"  [{verdict:>11}] {prompt!r}")
        if fired:
            false_positives.append(prompt)

    print("\nCanonical work prompts (must still FIRE):")
    regressions = []
    for prompt in WORK_PROMPTS:
        fired = _fires(prompt)
        verdict = "fires (ok)" if fired else "SILENT (regression)"
        print(f"  [{verdict:>18}] {prompt!r}")
        if not fired:
            regressions.append(prompt)

    print()
    if false_positives or regressions:
        if false_positives:
            print(
                f"DEFECT: {len(false_positives)} exploration prompt(s) wrongly "
                f"fired the work reminder."
            )
        if regressions:
            print(f"REGRESSION: {len(regressions)} work prompt(s) stopped firing.")
        return 1

    print("OK: exploration silent, work fires. Defect fixed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
