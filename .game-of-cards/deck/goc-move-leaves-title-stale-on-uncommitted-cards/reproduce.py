#!/usr/bin/env python3
"""Reproduce: `goc move` skips the moved card's own files when they are
untracked (newly created, not yet committed), leaving the in-file `title:`
field stale and the card failing `goc validate`.

Root cause: `_move_iter_tracked_text_files` enumerates files with
`git ls-files -z` (tracked only). A freshly-created card's README.md/log.md
are untracked, so the in-file rewrites (`title:`, `advances`, `advanced_by`,
H1, cross-links) never touch them. The directory is still renamed (via the
`shutil.move` fallback, since `git mv` also refuses an untracked source), so
the dir name and the `title:` field diverge.

Prints PASS/FAIL and exits non-zero while the defect is live.
"""
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


def _run(args, cwd, **kw):
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, **kw)


def main() -> int:
    goc = [sys.executable, "-m", "goc.cli"]
    env_path = str(ROOT)
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "consumer"
        repo.mkdir()
        import os

        env = dict(os.environ)
        env["PYTHONPATH"] = env_path + os.pathsep + env.get("PYTHONPATH", "")

        _run(["git", "init", "-q"], repo)
        _run(["git", "config", "user.email", "t@t.t"], repo)
        _run(["git", "config", "user.name", "t"], repo)
        (repo / ".game-of-cards" / "deck").mkdir(parents=True)

        def goc_run(extra):
            return subprocess.run(
                goc + extra, cwd=str(repo), capture_output=True, text=True, env=env
            )

        # Create a card and DO NOT commit it (the common file-then-rename flow).
        goc_run(["new", "card-with-typo-in-slog", "--contribution", "low", "--tag", "bug"])
        # Rename it before the first commit.
        goc_run(["move", "card-with-typo-in-slog", "card-with-typo-in-slug"])

        renamed = repo / ".game-of-cards" / "deck" / "card-with-typo-in-slug"
        readme = renamed / "README.md"
        dir_exists = renamed.is_dir()
        title_line = ""
        if readme.exists():
            for ln in readme.read_text().splitlines():
                if ln.startswith("title:"):
                    title_line = ln.strip()
                    break

        validate = goc_run(["validate"])

        print(f"dir renamed to card-with-typo-in-slug: {dir_exists}")
        print(f"in-file title line: {title_line!r}")
        print("validate output (title-mismatch lines):")
        for ln in (validate.stdout + validate.stderr).splitlines():
            if "title:" in ln and "!=" in ln:
                print(f"  {ln}")

        ok = (
            dir_exists
            and title_line == "title: card-with-typo-in-slug"
            and "!=" not in (validate.stdout + validate.stderr)
        )
        print()
        if ok:
            print("PASS: move rewrote the moved card's own title field")
            return 0
        print("FAIL: move renamed the directory but left title: stale → card fails validate")
        return 1


if __name__ == "__main__":
    sys.exit(main())
