"""Prove auto_commit publishes a dangling edge when the counterpart is a draft.

Builds a fresh git repo with `workflow.auto_commit: true`, files a committed
parent card, scaffolds a draft epic (default no-commit, born draft), then runs
`goc advance parent-card --by draft-epic`. Before the fix: the auto-commit
contains only the parent's edge write — the draft dir is dropped — so HEAD's
tree carries `advanced_by: [draft-epic]` with no such card dir; prints DEFECT
and exits 1. After the fix: the committed tree is self-consistent; exits 0.
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


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        env = dict(
            os.environ,
            PYTHONPATH=str(ROOT),
            GIT_AUTHOR_NAME="repro",
            GIT_AUTHOR_EMAIL="r@e",
            GIT_COMMITTER_NAME="repro",
            GIT_COMMITTER_EMAIL="r@e",
        )

        def git(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run(["git", *args], cwd=work, env=env, capture_output=True, text=True)

        def goc(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, "-m", "goc.cli", *args],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
            )

        git("init", "-q", "-b", "main")
        gm = work / ".game-of-cards"
        gm.mkdir()
        (gm / "config.yaml").write_text("workflow:\n  auto_commit: true\n")
        (gm / "deck").mkdir()
        git("add", "-A")
        git("commit", "-qm", "init")

        print("setup: fresh git repo, workflow.auto_commit: true, parent-card committed")
        r = goc("new", "parent-card", "--gate", "none", "--commit")
        assert r.returncode == 0, r.stderr
        parent_readme = gm / "deck" / "parent-card" / "README.md"
        authored = parent_readme.read_text()
        authored = authored.replace(
            "- [ ] (replace with real criteria)", "- [ ] PROCESS: repro criterion"
        ).replace("(write the design doc here)", "Authored body.")
        parent_readme.write_text(authored)
        r = goc("publish", "parent-card")
        assert r.returncode == 0, r.stderr
        print("goc publish parent-card (draft cleared, committed) ...")
        r = goc("new", "draft-epic", "--gate", "none")
        assert r.returncode == 0, r.stderr
        print("goc new draft-epic (stays draft) ...")

        r = goc("advance", "parent-card", "--by", "draft-epic")
        assert r.returncode == 0, r.stderr
        print("goc advance parent-card --by draft-epic ...")

        head_files = git("show", "--stat", "--name-only", "--format=", "HEAD").stdout.split()
        print("committed HEAD touches:", " ".join(head_files) or "(nothing)")
        untracked = git("status", "--porcelain").stdout.strip()
        if untracked:
            print("untracked (dropped from commit):", untracked)

        in_head = git("cat-file", "-e", "HEAD:.game-of-cards/deck/draft-epic/README.md").returncode == 0
        parent_head = git("show", "HEAD:.game-of-cards/deck/parent-card/README.md").stdout
        edge_in_head = "draft-epic" in parent_head

        if edge_in_head and not in_head:
            print(
                "DEFECT: committed tree has parent-card.advanced_by -> 'draft-epic' "
                "but no such card dir in HEAD"
            )
            return 1
        if edge_in_head and in_head:
            print("OK: committed tree is self-consistent (both endpoints in HEAD)")
            return 0
        print("OK: edge not committed (no dangling reference in HEAD)")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
