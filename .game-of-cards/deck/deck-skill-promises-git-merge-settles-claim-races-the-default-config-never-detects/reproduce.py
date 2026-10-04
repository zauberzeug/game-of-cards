#!/usr/bin/env python3
"""Does git's merge settle a claim race the way the deck skill and ABOUT.md say?

`goc/templates/skills/deck/SKILL.md` and `reference.md` say git's merge
"handles the rare simultaneous-claim race (whichever commits first wins)", and
`ABOUT.md` says "git's merge handles claim-races". This script races two claims
on one card from two clones of a bare remote under the shipped config (no
`workflow.claim_push`), then integrates the way workers do once their work is
done: the first pushes, the second pulls with rebase.

It runs two pairs of workers: distinct identities (agent-A, agent-B), and one
shared identity (fleet-bot), the way scheduled bots run. For each pair it
reports whether either claim failed, whether integrating raised anything, and
who the remote's card names afterwards.

It then checks the three surfaces: while both racing claims succeed, no
sentence may say git's merge handles the race or that whichever commits first
wins. Exits 1 and lists every contradicted sentence, 0 when there are none.
"""

from __future__ import annotations

import os
import re
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
SURFACES = (
    "goc/templates/skills/deck/SKILL.md",
    "goc/templates/skills/deck/reference.md",
    "ABOUT.md",
)
CLAIM = re.compile(r"git'?s merge handles[^.]*|whichever commits first wins", re.IGNORECASE)
CARD = "race-card"
CARD_TEXT = """\
---
title: race-card
summary: "A card two workers race to claim."
status: open
stage: null
contribution: medium
created: "2026-10-04T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: something happens
---

# Race card
"""


def _env(**extra: str) -> dict[str, str]:
    drop = {"CLAUDECODE", "CLAUDE_CODE", "CLAUDE_PROJECT_DIR", "GOC_WORKER", "GOC_WORKTREE_DECK"}
    env = {k: v for k, v in os.environ.items() if k not in drop and not k.startswith("GIT_")}
    env["PYTHONPATH"] = str(ROOT)
    env.update(extra)
    return env


def _run(cwd: Path, *cmd: str, when: str | None = None) -> subprocess.CompletedProcess[str]:
    # A pinned date keeps two same-identity claims from being byte-identical commits.
    extra = {"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when} if when else {}
    return subprocess.run(list(cmd), cwd=cwd, env=_env(**extra), capture_output=True, text=True)


def _git(cwd: Path, *args: str) -> str:
    done = _run(cwd, "git", *args)
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {done.stderr}")
    return done.stdout.strip()


def _clone(work: Path, remote: Path, name: str, who: str) -> Path:
    dest = work / name
    _git(work, "clone", "-q", str(remote), str(dest))
    _git(dest, "config", "user.name", who)
    _git(dest, "config", "user.email", f"{name}@example.com")
    return dest


def race(work: Path, first_who: str, second_who: str) -> dict:
    """Two stale clones claim one card; the first pushes, the second integrates."""
    work.mkdir()
    remote = work / "remote.git"
    _git(work, "init", "-q", "--bare", "-b", "main", str(remote))
    seed = _clone(work, remote, "seed", "seed")
    (seed / ".game-of-cards").mkdir()
    config = (ROOT / "goc" / "templates" / "game_of_cards" / "config.yaml").read_text()
    (seed / ".game-of-cards" / "config.yaml").write_text(config)
    card = seed / ".game-of-cards" / "deck" / CARD / "README.md"
    card.parent.mkdir(parents=True)
    card.write_text(CARD_TEXT)
    _git(seed, "add", "-A")
    _git(seed, "commit", "-q", "-m", "seed")
    _git(seed, "push", "-q", "origin", "main")

    one = _clone(work, remote, "worker-1", first_who)
    two = _clone(work, remote, "worker-2", second_who)
    goc = (sys.executable, "-m", "goc.cli", "status", CARD, "active")
    claim_1 = _run(one, *goc, when="2026-10-04T00:00:00Z")
    claim_2 = _run(two, *goc, when="2026-10-04T00:00:05Z")
    push_1 = _run(one, "git", "push", "-q", "origin", "main")
    pull_2 = _run(two, "git", "pull", "-q", "--rebase", "origin", "main")
    if pull_2.returncode != 0:
        _run(two, "git", "rebase", "--abort")
    remote_card = _git(remote, "show", f"main:.game-of-cards/deck/{CARD}/README.md")
    return {
        "claims": (claim_1.returncode, claim_2.returncode),
        "first_push": push_1.returncode,
        "second_integration": pull_2.returncode,
        "second_integration_says": (pull_2.stdout + pull_2.stderr).strip().splitlines()[:1],
        "remote_worker": re.search(r"^worker: (.*)$", remote_card, re.MULTILINE).group(1),
    }


def contradicted_sentences() -> list[str]:
    found = []
    for rel in SURFACES:
        for lineno, line in enumerate((ROOT / rel).read_text().splitlines(), 1):
            for match in CLAIM.finditer(line):
                found.append(f"{rel}:{lineno}: {match.group(0).strip()!r}")
    return found


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="goc-merge-claims-") as tmp:
        distinct = race(Path(tmp) / "distinct", "agent-A", "agent-B")
        shared = race(Path(tmp) / "shared", "fleet-bot", "fleet-bot")
    both_succeed = distinct["claims"] == (0, 0) and shared["claims"] == (0, 0)
    for label, result in (("distinct identities", distinct), ("one shared identity", shared)):
        print(f"{label}:")
        print(f"  claim exit codes (first, second): {result['claims']}")
        print(f"  first worker's push exit: {result['first_push']}")
        print(f"  second worker's `git pull --rebase` exit: {result['second_integration']}"
              f" {result['second_integration_says']}")
        print(f"  remote card's worker afterwards: {result['remote_worker']}")
    print()
    found = contradicted_sentences() if both_succeed else []
    if not both_succeed:
        print("A racing claim failed under the default config; the surfaces' reassurance is not contradicted.")
        return 0
    print("Both racing claims succeed under the default config: no merge happens at claim time,")
    print("and with one shared identity the second worker's integration raises nothing at all.")
    if found:
        print(f"\n{len(found)} sentence(s) still say git's merge settles the race:")
        for item in found:
            print(f"  - {item}")
        return 1
    print("\nNo surface says git's merge settles the race.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
