"""`goc status <t> active` reports a claim race whenever `git rebase` fails.

With `workflow.claim_push: true`, a claim commit that loses the push race is
re-fetched and rebased onto the remote. `_git_claim_push_with_retry`
(`goc/engine.py:5202`) then treats EVERY non-zero rebase exit as proof that
another worker claimed the card:

    if rebase.returncode != 0:
        ...
        print(f"ERROR: {title}: claim race - already claimed by {other!r} on "
              f"origin/{branch}. Your local claim commit is unpushed; reset to "
              f"origin/{branch} and pull a different card.")

`git rebase` also exits non-zero when it never inspected the card at all - a
dirty working tree, or a conflict in an unrelated file. Both are reported as a
rival claim; the "rival" is read from a `worker` field that survives release,
and the prescribed remedy discards the working tree.

Cases (each on its own throwaway origin, so they cannot contaminate one
another):

  1. control - clean tree, divergent origin -> claim pushed after rebase.
  2. BUG     - unrelated unstaged file, divergent origin -> "claim race"
               (git actually said "cannot rebase: You have unstaged changes").
  3. BUG     - unrelated-file rebase conflict -> "claim race", naming a worker
               whose copy of the card is `status: open` on the remote.

Exits 0 once the defect no longer fires.
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

CONFIG = """\
layer_2_project_dod: []
layer_3_goc_dod: []
workflow:
  auto_commit: true
  claim_push: true
"""

CARD = """\
---
title: claim-race-probe
summary: "Probe card for the claim-push reproduction."
status: open
stage: null
contribution: medium
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
{worker}definition_of_done: |
  - [ ] MECHANICAL: nothing
---

# claim-race-probe

Fixture card for the claim-push reproduction.
"""


def _env(home: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": str(ROOT),
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": str(home / "gitconfig"),
        "GIT_CONFIG_SYSTEM": str(home / "gitconfig"),
        "GIT_TERMINAL_PROMPT": "0",
        "GOC_WORKER": "",
    }


def _git(cwd: Path, home: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *argv], cwd=cwd, capture_output=True, text=True, env=_env(home)
    )


def _goc(cwd: Path, home: Path, who: str, *argv: str) -> subprocess.CompletedProcess[str]:
    env = _env(home)
    env["GOC_WORKER"] = who
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *argv],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


def _clone(origin: Path, dest: Path, home: Path, who: str) -> Path:
    subprocess.run(
        ["git", "clone", "--quiet", str(origin), str(dest)],
        capture_output=True, text=True, env=_env(home), check=True,
    )
    _git(dest, home, "config", "user.name", who)
    _git(dest, home, "config", "user.email", f"{who}@probe.invalid")
    return dest


def _fresh_origin(root: Path, home: Path, name: str, *, prior_worker: str | None) -> Path:
    """A bare origin holding one open card and one shared unrelated file."""
    origin = root / f"{name}.git"
    subprocess.run(
        ["git", "init", "--quiet", "--bare", "--initial-branch=main", str(origin)],
        capture_output=True, text=True, env=_env(home), check=True,
    )
    seed = _clone(origin, root / f"{name}-seed", home, "seeder")
    (seed / ".game-of-cards").mkdir()
    (seed / ".game-of-cards" / "config.yaml").write_text(CONFIG, encoding="utf-8")
    card = seed / ".game-of-cards" / "deck" / "claim-race-probe"
    card.mkdir(parents=True)
    # `worker` survives a release (`goc status <t> open` keeps it as a
    # historical record), so an open card can carry a prior claimant's name.
    worker = f"worker: {{who: {prior_worker}, where: main}}\n" if prior_worker else ""
    (card / "README.md").write_text(CARD.format(worker=worker), encoding="utf-8")
    (card / "log.md").write_text("", encoding="utf-8")
    (seed / "shared.txt").write_text("seed\n", encoding="utf-8")
    _git(seed, home, "add", "-A")
    _git(seed, home, "commit", "--quiet", "-m", "seed deck")
    _git(seed, home, "push", "--quiet", "origin", "main")
    return origin


def _advance(origin: Path, root: Path, home: Path, name: str, marker: str) -> None:
    """Another worker pushes an unrelated commit, so origin diverges."""
    w = _clone(origin, root / f"{name}-adv", home, "other-worker")
    (w / "shared.txt").write_text(f"{marker}\n", encoding="utf-8")
    _git(w, home, "commit", "--quiet", "-am", f"other worker: {marker}")
    _git(w, home, "push", "--quiet", "origin", "main")


def _remote_card_status(clone: Path, home: Path) -> str:
    _git(clone, home, "fetch", "--quiet", "origin", "main")
    shown = _git(
        clone, home, "show",
        "origin/main:.game-of-cards/deck/claim-race-probe/README.md",
    )
    return next(
        (ln for ln in shown.stdout.splitlines() if ln.startswith("status:")), "status: ?"
    )


def main() -> int:
    failures = 0
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        home = root / "home"
        home.mkdir()
        (home / "gitconfig").write_text("[init]\n\tdefaultBranch = main\n", encoding="utf-8")

        # -- Case 1 (control): clean tree, divergent origin -------------------
        o1 = _fresh_origin(root, home, "c1", prior_worker=None)
        w1 = _clone(o1, root / "c1-work", home, "worker-clean")
        _advance(o1, root, home, "c1", "first")
        proc = _goc(w1, home, "worker-clean", "status", "claim-race-probe", "active")
        if proc.returncode == 0 and "claim race" not in proc.stderr:
            print("PASS  control: clean tree + divergent origin -> claim pushed after rebase")
        else:
            failures += 1
            print(f"FAIL  control: exit={proc.returncode} stderr={proc.stderr.strip()!r}")

        # -- Case 2 (BUG): unrelated unstaged file ----------------------------
        o2 = _fresh_origin(root, home, "c2", prior_worker=None)
        w2 = _clone(o2, root / "c2-work", home, "worker-dirty")
        (w2 / "shared.txt").write_text("uncommitted WIP from this session\n", encoding="utf-8")
        _advance(o2, root, home, "c2", "second")
        proc = _goc(w2, home, "worker-dirty", "status", "claim-race-probe", "active")
        if "claim race" in proc.stderr:
            failures += 1
            print(
                "FAIL  BUG: an unrelated unstaged file is reported as a claim race "
                f"(exit={proc.returncode})\n      {proc.stderr.strip()}"
            )
        else:
            print(
                "PASS  unstaged-changes rebase failure is not called a claim race "
                f"(exit={proc.returncode})"
            )

        # -- Case 3 (BUG): unrelated-file rebase conflict ---------------------
        # The card on origin is `open` but still carries `worker-three` from a
        # claim that was released -- the field the error message reads.
        o3 = _fresh_origin(root, home, "c3", prior_worker="worker-three")
        w3 = _clone(o3, root / "c3-work", home, "worker-conflict")
        (w3 / "shared.txt").write_text("worker-conflict's own line\n", encoding="utf-8")
        _git(w3, home, "commit", "--quiet", "-am", "worker-conflict: unrelated edit")
        _advance(o3, root, home, "c3", "third")
        remote_status = _remote_card_status(w3, home)
        proc = _goc(w3, home, "worker-conflict", "status", "claim-race-probe", "active")
        if "claim race" in proc.stderr:
            failures += 1
            print(
                "FAIL  BUG: an unrelated-file rebase conflict is reported as a claim race "
                f"(exit={proc.returncode})\n"
                f"      {proc.stderr.strip()}\n"
                f"      ...but the remote card is `{remote_status}` - nobody holds it"
            )
        else:
            print(
                "PASS  unrelated-file conflict is not called a claim race "
                f"(exit={proc.returncode})"
            )

    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
