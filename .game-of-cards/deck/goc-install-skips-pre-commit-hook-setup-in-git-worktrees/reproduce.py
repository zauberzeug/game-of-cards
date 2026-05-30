"""Reproduce: _append_precommit_hook silently skips git worktrees.

In a git worktree, `<repo>/.git` is a *file* (containing `gitdir: …`), not
a directory. `_append_precommit_hook` guards on `(target.parent /
".git").is_dir()` — which returns False for a file — and so the
`.pre-commit-config.yaml` install step is silently skipped inside any
worktree, even though the worktree is unambiguously a git checkout.

Expected: after `_append_precommit_hook`, the worktree contains a
`.pre-commit-config.yaml` with the `goc-validate` hook.

Actual: the file is not written; the guard returns early.

Run via `uv run python deck/<title>/reproduce.py` from the repo root.
"""

from __future__ import annotations

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


def main() -> int:
    sys.path.insert(0, str(_repo_root()))
    from goc.install import _append_precommit_hook  # noqa: PLC0415

    tmp_root = Path(tempfile.mkdtemp(prefix="goc-worktree-repro-"))
    try:
        main_repo = tmp_root / "main"
        worktree = tmp_root / "worktree"
        main_repo.mkdir()
        env_args: dict[str, str | None] = {"check": True, "capture_output": True}
        subprocess.run(["git", "init", "-q"], cwd=main_repo, check=True, capture_output=True)
        subprocess.run(["git", "-C", str(main_repo), "config", "user.email", "x@x.com"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(main_repo), "config", "user.name", "x"], check=True, capture_output=True)
        (main_repo / "README").write_text("init\n")
        subprocess.run(["git", "-C", str(main_repo), "add", "README"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(main_repo), "commit", "-qm", "init"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(main_repo), "worktree", "add", "-q", "-b", "branch", str(worktree)],
            check=True, capture_output=True,
        )

        dot_git = worktree / ".git"
        print(f"worktree .git is_dir() : {dot_git.is_dir()}")
        print(f"worktree .git is_file(): {dot_git.is_file()}")
        print(f"worktree .git exists() : {dot_git.exists()}")

        target = worktree / ".pre-commit-config.yaml"
        _append_precommit_hook(target)

        if target.exists():
            print(f"PASS: {target.relative_to(tmp_root)} written")
            return 0
        print(f"FAIL: {target.relative_to(tmp_root)} NOT written — _append_precommit_hook returned early because (.git).is_dir() is False in a worktree")
        return 1
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
