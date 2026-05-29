"""Reproduce the asymmetric worker-field refresh on re-claim.

Sets up a temp repo, files a card as Alice on branch feature/alice, releases
it, then re-claims as Bob on branch feature/bob without `--worker-who`. The
expected behavior (under the live-git-is-source-of-truth model) is
worker.who == 'bob'. Today the script demonstrates worker.who == 'alice'
because `_auto_populate_worker` preserves the prior `who` while still
refreshing `where`.
"""

from __future__ import annotations

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


REPO = _repo_root()
sys.path.insert(0, str(REPO))


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.stderr.write(f"FAIL: {' '.join(cmd)}\n{r.stdout}\n{r.stderr}\n")
        sys.exit(2)
    return r.stdout


def _git(args: list[str], cwd: Path, who_name: str | None = None) -> str:
    import os

    env = os.environ.copy()
    if who_name is not None:
        env["GIT_AUTHOR_NAME"] = who_name
        env["GIT_COMMITTER_NAME"] = who_name
        env["GIT_AUTHOR_EMAIL"] = f"{who_name}@example.com"
        env["GIT_COMMITTER_EMAIL"] = f"{who_name}@example.com"
    return _run(["git"] + args, cwd, env=env)


def _set_user_name(cwd: Path, name: str) -> None:
    _git(["config", "user.name", name], cwd)
    _git(["config", "user.email", f"{name}@example.com"], cwd)


def _read_worker_field(card_dir: Path) -> str:
    text = (card_dir / "README.md").read_text()
    for line in text.splitlines():
        if line.startswith("worker:"):
            return line.strip()
    return "(no worker field)"


def main() -> int:
    import os

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "repo"
        tmp_path.mkdir()
        _git(["init", "-q", "-b", "main"], tmp_path)
        _set_user_name(tmp_path, "alice")
        (tmp_path / "seed").write_text("x")
        _git(["add", "seed"], tmp_path)
        _git(["commit", "-q", "-m", "seed"], tmp_path, who_name="alice")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO)
        cli = [sys.executable, "-m", "goc.cli"]

        _run(cli + ["install", "--agents", "claude"], tmp_path, env=env)

        # Alice files and claims on her branch
        _git(["checkout", "-q", "-b", "feature/alice"], tmp_path)
        _run(cli + ["new", "demo-card", "--tag", "story", "--gate", "none"], tmp_path, env=env)
        _run(cli + ["status", "demo-card", "active", "--no-commit"], tmp_path, env=env)

        card_dir = tmp_path / ".game-of-cards" / "deck" / "demo-card"
        print("after Alice claims:")
        print(" ", _read_worker_field(card_dir))

        # Alice releases the card
        _run(cli + ["status", "demo-card", "open", "--no-commit"], tmp_path, env=env)
        print("after Alice releases (status open):")
        print(" ", _read_worker_field(card_dir))

        # Bob switches identity and re-claims on his branch, no --worker-who
        _set_user_name(tmp_path, "bob")
        _git(["checkout", "-q", "-b", "feature/bob"], tmp_path)
        _run(cli + ["status", "demo-card", "active", "--no-commit"], tmp_path, env=env)

        observed = _read_worker_field(card_dir)
        print("after Bob re-claims (no --worker-who):")
        print(" ", observed)

        expected_who = "bob"
        actual_who = "alice" if "who: alice" in observed else ("bob" if "who: bob" in observed else "<other>")
        print()
        print(f"expected worker.who: {expected_who}")
        print(f"actual   worker.who: {actual_who}")

        if actual_who == expected_who:
            print("PASS — defect not reproduced (behavior matches expectation).")
            return 0
        print("FAIL — defect reproduced: Bob's re-claim is attributed to Alice.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
