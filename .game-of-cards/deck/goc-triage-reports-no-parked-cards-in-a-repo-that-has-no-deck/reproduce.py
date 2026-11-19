"""Reproduce: `goc triage` stays silent about a missing deck.

In a scratch git repo with no `.game-of-cards/`, run the default view (the
control: it prints the missing-deck notice on stderr) and both triage forms,
`goc triage` and `goc triage --json`. Each triage form must print the same
notice line on stderr as the control, while its exit code and stdout stay
what an empty park queue gives: exit 0, the empty-triage line, `[]`.

Exit codes: 0 — the defect no longer fires (both triage forms name the
missing deck); 1 — the defect fires; 2 — the control printed no notice, so
there is no verdict.

Run: uv run python .game-of-cards/deck/goc-triage-reports-no-parked-cards-in-a-repo-that-has-no-deck/reproduce.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
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

from goc.engine import MISSING_DECK_PHRASE  # noqa: E402

# What an empty park queue prints; the notice must not change it.
EXPECTED_STDOUT = {
    ("triage",): "No parked cards (status: open; gate ≠ none).",
    ("triage", "--json"): "[]",
}


def goc(cwd: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env.pop("GOC_WORKTREE_DECK", None)
    # The launcher by path, not `-m`: the scratch cwd must not shadow the engine.
    return subprocess.run(
        [sys.executable, str(ROOT / "goc" / "_launch.py"), *argv],
        cwd=cwd, env=env, capture_output=True, text=True, check=False,
    )


def notice_line(stderr: str) -> str | None:
    return next((ln for ln in stderr.splitlines() if MISSING_DECK_PHRASE in ln), None)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        subprocess.run(["git", "init", "-q", str(root)], check=True)

        control = goc(root)
        expected = notice_line(control.stderr)
        print(f"--- control: goc (default view)  exit={control.returncode}")
        print(f"stdout: {control.stdout.strip()!r}")
        print(f"stderr: {control.stderr.strip()!r}")
        if control.returncode != 0 or expected is None:
            print("\n[NO VERDICT] the control printed no missing-deck notice")
            return 2

        failures: list[str] = []
        for argv, want_stdout in EXPECTED_STDOUT.items():
            result = goc(root, *argv)
            label = "goc " + " ".join(argv)
            print(f"--- {label}  exit={result.returncode}")
            print(f"stdout: {result.stdout.strip()!r}")
            print(f"stderr: {result.stderr.strip()!r}")
            got = notice_line(result.stderr)
            if got is None:
                failures.append(f"{label}: no missing-deck notice on stderr")
            elif got != expected:
                failures.append(f"{label}: notice differs from the default view's: {got!r}")
            if result.returncode != 0:
                failures.append(f"{label}: exit {result.returncode}, want 0")
            if result.stdout.strip() != want_stdout:
                failures.append(f"{label}: stdout {result.stdout.strip()!r}, want {want_stdout!r}")

    if failures:
        print("\n[FAIL] defect fires:")
        for failure in failures:
            print(" -", failure)
        return 1
    print("\n[OK] defect no longer fires: both triage forms name the missing deck")
    return 0


if __name__ == "__main__":
    sys.exit(main())
