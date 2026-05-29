"""Prove that `goc status active --worker-who X` is silently dropped when
the target card is already in `status: active`.

Run via `uv run python .game-of-cards/deck/<title>/reproduce.py`.
Expected (defect present): exits 2 with "DEFECT: worker field unchanged
after override".
Expected (defect fixed under decision-path 1): exits 0 with "OK: worker
field updated to bob-claimer".
"""
from __future__ import annotations

import os
import shutil
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


REPO_ROOT = _repo_root()
sys.path.insert(0, str(REPO_ROOT))


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, check=False, timeout=60
    )


def _worker_line(readme: Path) -> str:
    for line in readme.read_text().splitlines():
        if line.startswith("worker:"):
            return line.strip()
    return "<no worker line>"


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="goc-repro-worker-overrides-"))
    try:
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = "test-runner"
        env["GIT_AUTHOR_EMAIL"] = "test@example.com"
        env["GIT_COMMITTER_NAME"] = "test-runner"
        env["GIT_COMMITTER_EMAIL"] = "test@example.com"

        subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
        subprocess.run(
            ["git", "config", "user.name", "alice-orig"], cwd=workdir, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "alice@example.com"],
            cwd=workdir,
            check=True,
        )

        python_bin = REPO_ROOT / ".venv" / "bin" / "python"
        if not python_bin.exists():
            python_bin = Path(sys.executable)

        def goc(args: list[str]) -> subprocess.CompletedProcess:
            return _run([str(python_bin), "-m", "goc.cli", *args], cwd=workdir)

        r = goc(["install", "--local-skills"])
        if r.returncode != 0:
            print("FAIL: goc install errored:", r.stderr[-300:])
            return 1

        r = goc(["new", "sample-card", "--contribution", "medium"])
        if r.returncode != 0:
            print("FAIL: goc new errored:", r.stderr[-300:])
            return 1

        # 1st claim: as alice-orig (the git config user.name)
        r = goc(["status", "sample-card", "active", "--no-commit"])
        if r.returncode != 0:
            print("FAIL: 1st goc status active errored:", r.stderr[-300:])
            return 1

        readme = workdir / ".game-of-cards" / "deck" / "sample-card" / "README.md"
        before = _worker_line(readme)
        print(f"After 1st claim: {before}")
        if "alice-orig" not in before:
            print(f"FAIL: 1st claim did not set worker to alice-orig: {before!r}")
            return 1

        # 2nd invocation: card already active, pass --worker-who bob and
        # --worker-where feature/bar.
        r = goc(
            [
                "status",
                "sample-card",
                "active",
                "--worker-who",
                "bob-claimer",
                "--worker-where",
                "feature/bar",
                "--no-commit",
            ]
        )
        # The current behavior exits 0 with a WARNING to stderr.
        after = _worker_line(readme)
        print(f"After 2nd attempt (overrides bob-claimer / feature/bar): {after}")

        if "bob-claimer" in after and "feature/bar" in after:
            print("OK: worker field updated to bob-claimer (defect fixed).")
            return 0

        print(
            "DEFECT: worker field unchanged after override — "
            "--worker-who and --worker-where were silently dropped."
        )
        return 2
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
