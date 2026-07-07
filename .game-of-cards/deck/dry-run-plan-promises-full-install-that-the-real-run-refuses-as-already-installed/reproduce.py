"""Reproduce: `goc install --dry-run` prints a full write plan and exits 0
on a repo that already has GoC installed, while the real run performs zero
writes and exits 1 with "already installed".

`install()` (goc/install.py) short-circuits on `dry_run` before the
`_find_installed_deck_dir` already-installed guard runs, so the preview
promises an install the executor refuses.

Run on a clean checkout:
    uv run python .game-of-cards/deck/dry-run-plan-promises-full-install-that-the-real-run-refuses-as-already-installed/reproduce.py
"""

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


def _run_goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


with tempfile.TemporaryDirectory() as td:
    target = Path(td) / "consumer"
    deck = target / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)
    (deck / ".goc-version").write_text("0.0.30\n")

    dry = _run_goc(target, "install", "--dry-run")
    real = _run_goc(target, "install")

    print(f"  dry-run exit: {dry.returncode}")
    print(f"  dry-run plans writes: {'writes planned' in dry.stdout}")
    print(f"  real run exit: {real.returncode}")
    print(f"  real run refuses as already installed: {'already installed' in real.stderr}")

print()
if real.returncode == 1 and "already installed" in real.stderr and (
    dry.returncode == 0 or "writes planned" in dry.stdout
):
    print(
        "DEFECT REPRODUCED: dry-run promises a full install (write plan, exit 0) "
        "that the real run refuses as already installed (exit 1)."
    )
    sys.exit(1)
print("No defect: dry-run and real run agree on the already-installed refusal.")
sys.exit(0)
