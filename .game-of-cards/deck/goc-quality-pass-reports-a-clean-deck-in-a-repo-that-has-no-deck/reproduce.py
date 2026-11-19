"""Reproduce: `goc quality-pass` reports a clean deck where there is no deck.

In a scratch git repo with no `.game-of-cards/`, run the default view (the
control: it prints the missing-deck notice on stderr) and `goc quality-pass`,
at its default `--status open` and at `--status all`. Each quality-pass run
must print the same notice line on stderr as the control, while its exit code
and stdout stay what a zero-card pass gives: exit 0 and the two `clean.` lines.

Exit codes: 0 — the defect no longer fires (quality-pass names the missing
deck); 1 — the defect fires; 2 — the control printed no notice, so there is
no verdict.

Run: uv run python .game-of-cards/deck/goc-quality-pass-reports-a-clean-deck-in-a-repo-that-has-no-deck/reproduce.py
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


def zero_card_pass(status: str) -> str:
    """What a pass over zero cards prints; the notice must not change it."""
    return (
        f"Quality pass over 0 cards (status={status}):\n\n"
        "Title antipatterns: clean.\n\n"
        "Missing summary: clean."
    )


FORMS = {
    ("quality-pass",): zero_card_pass("open"),
    ("quality-pass", "--status", "all"): zero_card_pass("all"),
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
        for argv, want_stdout in FORMS.items():
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
    print("\n[OK] defect no longer fires: quality-pass names the missing deck")
    return 0


if __name__ == "__main__":
    sys.exit(main())
