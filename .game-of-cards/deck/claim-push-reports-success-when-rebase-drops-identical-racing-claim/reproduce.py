"""Prove _git_claim_push_with_retry reports a successful claim when the rebase
silently drops a patch-identical racing claim (same worker identity).

Sets up a bare remote and two clones with `workflow.claim_push: true`.
Clone A claims a card with --worker-who 'claude[bot]' and pushes. Clone B
(behind, never fetched) runs the byte-identical claim:

  - git rebase deduplicates B's commit via patch-id (returncode 0),
  - push reports "Everything up-to-date",
  - the engine prints "pushed (after rebase)" and returns True,
  - B's claim commit no longer exists; B proceeds to work an
    already-claimed card — the double-work race claim_push was designed
    to stop.

Control: a third clone claims with a DIFFERENT identity — the rebase
conflicts and the designed "claim race — already claimed by" abort fires,
showing the protection is identity-conditional.

Defect proven when B's identical claim exits 0 with "pushed (after
rebase)" while the different-identity claim exits nonzero with the
claim-race error.
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


REPO = _repo_root()
ENV = {
    "PYTHONPATH": str(REPO),
    "PATH": "/usr/bin:/bin",
    "GIT_AUTHOR_NAME": "repro",
    "GIT_AUTHOR_EMAIL": "repro@example.com",
    "GIT_COMMITTER_NAME": "repro",
    "GIT_COMMITTER_EMAIL": "repro@example.com",
    "HOME": tempfile.mkdtemp(prefix="goc-claim-home-"),
}


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=ENV, capture_output=True, text=True, check=True
    )


def goc(cwd: Path, *args: str, when: str | None = None) -> subprocess.CompletedProcess:
    env = dict(ENV)
    if when:
        # Distinct commit timestamps per clone: otherwise the two claims
        # produce the SAME commit SHA (same tree/parent/message/author and
        # same-second timestamp) and B's push trivially reports
        # "Everything up-to-date" without even reaching the rebase path —
        # an even stronger variant of the same silent-success hole.
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="goc-claim-race-"))
    bare = tmp / "remote.git"
    bare.mkdir()
    git(bare, "init", "--bare", "--initial-branch=main", ".")

    a = tmp / "clone-a"
    git(tmp, "clone", str(bare), str(a))
    git(a, "checkout", "-b", "main")
    goc(a, "new", "fix-the-widget", "--gate", "none", "--no-commit")
    cfg = a / ".game-of-cards" / "config.yaml"
    cfg.parent.mkdir(exist_ok=True)
    cfg.write_text("workflow:\n  claim_push: true\n")
    git(a, "add", "-A")
    git(a, "commit", "-m", "seed card + claim_push config")
    git(a, "push", "origin", "main")

    b = tmp / "clone-b"
    git(tmp, "clone", str(bare), str(b))
    c = tmp / "clone-c"
    git(tmp, "clone", str(bare), str(c))

    ra = goc(
        a,
        "status",
        "fix-the-widget",
        "active",
        "--worker-who",
        "claude[bot]",
        when="2026-01-01T10:00:00 +0000",
    )
    print(f"[clone A claim, who=claude[bot]] exit={ra.returncode}")

    rb = goc(
        b,
        "status",
        "fix-the-widget",
        "active",
        "--worker-who",
        "claude[bot]",
        when="2026-01-01T10:05:00 +0000",
    )
    print(f"[clone B same-identity claim]    exit={rb.returncode}")
    for line in (rb.stdout + rb.stderr).strip().splitlines():
        print(f"  {line}")
    b_ahead = git(b, "rev-list", "origin/main..HEAD").stdout.strip()
    print(f"  clone B unpushed commits after 'success': {b_ahead or '<none — claim commit vanished>'}")

    rc = goc(c, "status", "fix-the-widget", "active", "--worker-who", "other-agent")
    print(f"[clone C different-identity claim] exit={rc.returncode}")
    race_line = [
        line for line in (rc.stdout + rc.stderr).splitlines() if "claim race" in line
    ]
    print(f"  {race_line[0] if race_line else '<no claim-race error>'}")

    same_id_slipped = (
        rb.returncode == 0
        and "pushed (after rebase)" in rb.stdout
        and not b_ahead
    )
    diff_id_aborted = rc.returncode != 0 and bool(race_line)

    if same_id_slipped and diff_id_aborted:
        print(
            "\nDEFECT CONFIRMED: a same-identity racing claim is reported as"
            " pushed while its commit was silently dropped; only a"
            " different-identity race triggers the designed abort."
        )
        return 0
    print("\nDefect no longer fires (or output shape changed) — inspect manually.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
