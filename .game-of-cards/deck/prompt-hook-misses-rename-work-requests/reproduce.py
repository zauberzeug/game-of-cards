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


def _run_hook(prompt: str) -> subprocess.CompletedProcess[str]:
    repo = _repo_root()
    payload = json.dumps({"prompt": prompt})
    return subprocess.run(
        [sys.executable, str(repo / "goc" / "templates" / "hooks" / "user-prompt-submit.py")],
        input=payload,
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    cases = [
        ("rename the button to Export", True),
        ("add a CSV export", True),
        ("fix the auth bug", True),
        ("explain the auth flow", False),
        ("git status", False),
    ]
    failures: list[str] = []
    for prompt, should_remind in cases:
        result = _run_hook(prompt)
        reminded = "[Game of Cards | runtime active]" in result.stdout
        print(f"{prompt!r}: exit={result.returncode}; reminded={reminded}")
        if result.returncode != 0:
            failures.append(f"{prompt!r} exited {result.returncode}")
        if reminded != should_remind:
            failures.append(f"{prompt!r} reminded={reminded}, expected {should_remind}")
    if failures:
        print("defect present:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("ok: hook classifies canonical work and non-work prompts correctly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
