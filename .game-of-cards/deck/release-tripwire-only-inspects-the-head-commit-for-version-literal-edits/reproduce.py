#!/usr/bin/env python3
"""release-tripwire-only-inspects-the-head-commit-for-version-literal-edits

The release.yml tripwire diffs exactly `HEAD~1..HEAD` for version-literal
edits, but AGENTS.md claims it "fails the build on any human commit that
touches those six files". On a main branch receiving autonomous deck commits
every 12h, a human literal edit is almost never at HEAD when a release is
dispatched — one bot commit on top and the guard passes.

Exits ZERO when release.yml no longer uses the depth-1 range (or the miss no
longer reproduces); exits NONZERO while the defect fires.
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
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
DEPTH1_RANGE = "git diff --name-only HEAD~1 HEAD --"
TRACKED_FILE = "claude-plugin/.claude-plugin/plugin.json"


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def main() -> int:
    depth1_present = DEPTH1_RANGE in WORKFLOW.read_text()
    print(f"release.yml tripwire uses depth-1 range ('{DEPTH1_RANGE} ...'): {depth1_present}")

    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        git("init", "-q", ".", cwd=repo)
        git("config", "user.email", "probe@example.com", cwd=repo)
        git("config", "user.name", "probe", cwd=repo)
        tracked = repo / TRACKED_FILE
        tracked.parent.mkdir(parents=True)
        tracked.write_text('{"version": "0.0.27"}\n')
        (repo / "README.md").write_text("baseline\n")
        git("add", "-A", cwd=repo)
        git("commit", "-qm", "baseline", cwd=repo)
        tracked.write_text('{"version": "0.0.99"}\n')  # the human literal bump
        git("add", "-A", cwd=repo)
        git("commit", "-qm", "human: bump version literal by hand", cwd=repo)
        deck_file = repo / ".game-of-cards" / "deck" / "some-card" / "README.md"
        deck_file.parent.mkdir(parents=True)
        deck_file.write_text("autonomous deck commit\n")
        git("add", "-A", cwd=repo)
        git("commit", "-qm", "deck: autonomous card commit", cwd=repo)

        guard_sees = git("diff", "--name-only", "HEAD~1", "HEAD", "--", TRACKED_FILE, cwd=repo)
        truth_sees = git("diff", "--name-only", "HEAD~2", "HEAD", "--", TRACKED_FILE, cwd=repo)
        verdict = "BLOCK" if guard_sees else "'OK — HEAD leaves version literals alone.'"
        print(f"tripwire's own range (HEAD~1..HEAD) sees: {guard_sees!r} -> verdict: {verdict}")
        print(f"range covering every commit since baseline sees: {truth_sees!r}")
        missed = (not guard_sees) and bool(truth_sees)

    if depth1_present and missed:
        print(
            "FAIL: a human version-literal commit one position below HEAD passes "
            "the tripwire, contradicting AGENTS.md ('fails the build on any human "
            "commit that touches those six files')"
        )
        return 1
    print("PASS: tripwire range is no longer depth-1 (or the miss no longer reproduces)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
