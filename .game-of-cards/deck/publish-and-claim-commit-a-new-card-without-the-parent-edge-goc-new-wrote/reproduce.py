"""Prove the release verbs commit a new card without the edge `goc new` wrote.

For each of the four combinations of {`goc new --advances`,
`goc new --advanced-by`} x {`goc publish`, `goc status <title> active`}, in a
fresh scratch repo with `workflow.auto_commit: true`:

1. commit an authored `parent-card`;
2. `goc new child-card --advances parent-card` (or `--advanced-by`) WITHOUT
   `--commit`, the default, which writes the parent's counterpart edge to disk
   and leaves it uncommitted;
3. replace the child's scaffold placeholders (author it);
4. release it with the verb under test (auto-commit on);
5. report whether the parent's README is still uncommitted, and whether
   `goc validate` passes on a fresh clone of HEAD.

Exit-code contract (the DoD convention): exits 1 while the defect fires in
any combination, 0 once every combination leaves the counterpart edge
committed and HEAD validating.
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
DECK_REL = ".game-of-cards/deck"

ENV = dict(
    os.environ,
    PYTHONPATH=str(ROOT),
    # Isolate git from the host's global and system config (signing keys,
    # global hooks, safe.bareRepository) so the verdict is about goc alone.
    GIT_CONFIG_GLOBAL=os.devnull,
    GIT_CONFIG_NOSYSTEM="1",
    GIT_AUTHOR_NAME="repro",
    GIT_AUTHOR_EMAIL="repro@example.invalid",
    GIT_COMMITTER_NAME="repro",
    GIT_COMMITTER_EMAIL="repro@example.invalid",
)


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True, check=False)


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd)


def goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, "-m", "goc.cli", *args], cwd)


def must(result: subprocess.CompletedProcess[str], what: str) -> None:
    if result.returncode != 0:
        raise SystemExit(f"setup step failed ({what}):\n{result.stdout}{result.stderr}")


def author(repo: Path, title: str) -> None:
    readme = repo / DECK_REL / title / "README.md"
    text = readme.read_text()
    text = text.replace("- [ ] (replace with real criteria)", "- [ ] PROCESS: repro criterion")
    text = text.replace("(write the design doc here)", "Authored body.")
    readme.write_text(text)


def scenario(tmp: Path, wire_flag: str, release: str) -> bool:
    """Run one combination; return True when the defect fires."""
    repo = tmp / f"repo{wire_flag}-{release}"
    repo.mkdir()
    must(git(repo, "init", "-q", "-b", "main"), "git init")
    (repo / ".game-of-cards").mkdir()
    (repo / ".game-of-cards" / "config.yaml").write_text("workflow:\n  auto_commit: true\n")
    (repo / DECK_REL).mkdir()
    must(git(repo, "add", "-A"), "git add")
    must(git(repo, "commit", "-qm", "init"), "git commit")

    must(goc(repo, "new", "parent-card", "--summary", "parent", "--gate", "none", "--tag", "bug", "--commit"),
         "goc new parent-card")
    author(repo, "parent-card")
    must(goc(repo, "publish", "parent-card"), "goc publish parent-card")

    must(goc(repo, "new", "child-card", wire_flag, "parent-card", "--summary", "child",
             "--gate", "none", "--tag", "bug"),
         f"goc new child-card {wire_flag} parent-card")
    author(repo, "child-card")
    if release == "publish":
        verb = ["publish", "child-card"]
    else:
        verb = ["status", "child-card", "active"]
    released = goc(repo, *verb)
    must(released, "goc " + " ".join(verb))

    porcelain = git(repo, "status", "--porcelain").stdout
    stray = [line for line in porcelain.splitlines() if "parent-card" in line]

    clone = tmp / f"clone{wire_flag}-{release}"
    must(git(tmp, "clone", "-q", str(repo), str(clone)), "git clone")
    validated = goc(clone, "validate", "--quiet")

    print(f"=== goc new child-card {wire_flag} parent-card; goc {' '.join(verb)}")
    print(f"  release output: {released.stdout.strip().splitlines()[-1]}")
    print(f"  uncommitted parent paths: {stray or 'none'}")
    print(f"  validate on a fresh clone of HEAD: exit={validated.returncode}")
    for line in (validated.stdout + validated.stderr).strip().splitlines():
        print(f"    {line}")
    fires = bool(stray) or validated.returncode != 0
    print(f"  verdict: {'DEFECT' if fires else 'ok'}")
    return fires


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        fired = [
            scenario(tmp, wire_flag, release)
            for wire_flag in ("--advances", "--advanced-by")
            for release in ("publish", "claim")
        ]
    if any(fired):
        print(f"DEFECT: {sum(fired)} of {len(fired)} release paths commit a half-edge")
        return 1
    print("OK: every release path commits the counterpart edge; HEAD validates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
