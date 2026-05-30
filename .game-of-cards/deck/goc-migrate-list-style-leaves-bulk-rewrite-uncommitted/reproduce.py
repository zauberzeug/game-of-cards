"""Reproduce: `goc migrate-list-style` rewrites cards but never commits.

Seeds a temp git repo with a card whose frontmatter uses inline-flow edge
lists (the legacy shape `migrate-list-style` is meant to rewrite), runs the
verb, and inspects `git status --porcelain` + `git log` to confirm the
working tree is dirty and HEAD did not advance.

Compare with the sibling verb `goc advance`, which auto-commits its
mutations by default (see `engine.py:4391-4409`).
"""

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


REPO = _repo_root()


def _run(cmd, cwd, env=None, check=True):
    result = subprocess.run(
        cmd, cwd=str(cwd), env=env, capture_output=True, text=True
    )
    if check and result.returncode != 0:
        print(f"COMMAND FAILED: {' '.join(cmd)}", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    return result


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="goc-migrate-list-style-"))
    try:
        deck = tmp / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        (tmp / "pyproject.toml").write_text("[project]\nname='fixture'\nversion='0.0.0'\n")

        # Two cards with inline-flow edges — the shape migrate-list-style rewrites.
        card_a = deck / "card-a"
        card_a.mkdir()
        (card_a / "README.md").write_text(
            "---\n"
            "title: card-a\n"
            'summary: "fixture a"\n'
            "status: open\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-01-01\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: [card-b]\n"
            "advanced_by: []\n"
            "tags: [story]\n"
            "definition_of_done: |\n"
            "  - [ ] (placeholder)\n"
            "---\n"
            "\n# card-a\n"
        )
        (card_a / "log.md").write_text("")
        card_b = deck / "card-b"
        card_b.mkdir()
        (card_b / "README.md").write_text(
            "---\n"
            "title: card-b\n"
            'summary: "fixture b"\n'
            "status: open\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-01-01\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: [card-a]\n"
            "tags: [story]\n"
            "definition_of_done: |\n"
            "  - [ ] (placeholder)\n"
            "---\n"
            "\n# card-b\n"
        )
        (card_b / "log.md").write_text("")

        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = "test"
        env["GIT_AUTHOR_EMAIL"] = "test@example.com"
        env["GIT_COMMITTER_NAME"] = "test"
        env["GIT_COMMITTER_EMAIL"] = "test@example.com"

        _run(["git", "init", "-q", "-b", "main"], cwd=tmp, env=env)
        _run(["git", "add", "-A"], cwd=tmp, env=env)
        _run(["git", "commit", "-q", "-m", "seed"], cwd=tmp, env=env)

        head_before = _run(["git", "rev-parse", "HEAD"], cwd=tmp, env=env).stdout.strip()
        status_before = _run(["git", "status", "--porcelain"], cwd=tmp, env=env).stdout

        # Run migrate-list-style from the engine in the project venv.
        goc_env = env.copy()
        goc_env["PYTHONPATH"] = str(REPO)
        _run(
            [sys.executable, "-m", "goc.cli", "migrate-list-style"],
            cwd=tmp,
            env=goc_env,
        )

        head_after = _run(["git", "rev-parse", "HEAD"], cwd=tmp, env=env).stdout.strip()
        status_after = _run(["git", "status", "--porcelain"], cwd=tmp, env=env).stdout

        print("=" * 60)
        print("HEAD before:        ", head_before)
        print("HEAD after :        ", head_after)
        print("HEAD advanced?      ", head_before != head_after)
        print("Working tree before:", repr(status_before))
        print("Working tree after :")
        for line in status_after.splitlines():
            print("  ", line)
        print("Working tree dirty? ", bool(status_after.strip()))
        print("=" * 60)

        head_unchanged = head_before == head_after
        tree_dirty = bool(status_after.strip())
        defect = head_unchanged and tree_dirty
        print("DEFECT REPRODUCED:  ", defect)
        if defect:
            print("→ migrate-list-style rewrote cards but did not commit.")
            print("→ Compare with `goc advance`, which auto-commits on the same fixture.")
        return 0 if defect else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
