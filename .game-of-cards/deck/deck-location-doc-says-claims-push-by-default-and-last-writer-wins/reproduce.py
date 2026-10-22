#!/usr/bin/env python3
"""Run the claim protocol DECK_LOCATION.md describes against a real remote.

The Same-repo row of the "Claim and sync semantics" table used to say that
`goc status active` "autocommits and pushes" and that "Last-writer-wins on the
file resolves" a race between two claimers. The Same-repo row of "Offline
behavior" says the push is deferred. This script sets up bare remotes and
clones of a `goc install`-ed repo holding one open card, and observes:

1. default config: does agent-A's claim reach the remote?
2. default config: agent-B claims the same card from a stale view. Does
   anything detect the race?
3. `workflow.claim_push: true` (the shipped comment line, uncommented): A
   claims, then B claims from a stale view. Whose claim does the remote keep,
   and what does B see?
4. `claim_push`, both clones under one identity (a bot fleet): is the second
   claim refused?
5. `claim_push` with an unreachable remote: what does an offline claim do?

It then checks both rows against the observations:

- a sentence saying `goc status … active` pushes must name `claim_push` when a
  default claim does not push;
- the claim row must name the winner of a `claim_push` race, and the right one;
- when a default racing claim succeeds, the claim row must say nothing detects
  it;
- the claim row must link the open identical-claim card while an identical
  claim still succeeds, and must not once it is refused;
- the Offline row must except `claim_push` when an offline `claim_push` claim
  fails.

Usage: reproduce.py [path/to/DECK_LOCATION.md]   (default: the working tree's)
Exits 1 and lists every claim the observations contradict, 0 when there are none.
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
CARD = "race-card"
CARD_README = f".game-of-cards/deck/{CARD}/README.md"
IDENTICAL_CLAIM_CARD = "claim-push-reports-success-when-rebase-drops-identical-racing-claim"
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
SHIPPED_OFF = "  # claim_push: true        #"
ENABLED = "  claim_push: true          #"


def _env(**extra: str) -> dict[str, str]:
    drop = {"CLAUDECODE", "CLAUDE_CODE", "CLAUDE_PROJECT_DIR", "GOC_WORKER", "GOC_WORKTREE_DECK"}
    env = {k: v for k, v in os.environ.items() if k not in drop and not k.startswith("GIT_")}
    env["PYTHONPATH"] = str(ROOT)
    env.update(extra)
    return env


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=_env(), check=True, capture_output=True, text=True
    ).stdout.strip()


def _goc(cwd: Path, *args: str, when: str | None = None) -> subprocess.CompletedProcess[str]:
    # Pinning the commit date keeps two same-identity claims from landing in
    # the same second, which would make them byte-identical commits.
    extra = {"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when} if when else {}
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args], cwd=cwd, env=_env(**extra), text=True, capture_output=True
    )


def _clone(work: Path, remote: Path, name: str, who: str | None = None) -> Path:
    dest = work / name
    _git(work, "clone", "-q", str(remote), str(dest))
    _git(dest, "config", "user.name", who or name)
    _git(dest, "config", "user.email", f"{name}@example.com")
    return dest


def _remote_card(remote: Path) -> dict[str, str]:
    text = _git(remote, "show", f"main:{CARD_README}")
    return dict(re.findall(r"^(status|worker): (.*)$", text, re.MULTILINE))


def _seed(work: Path, *, claim_push: bool) -> Path:
    """A bare remote whose main holds a `goc install`-ed repo with one open card."""
    work.mkdir()
    remote = work / "remote.git"
    _git(work, "init", "-q", "--bare", "-b", "main", str(remote))
    seed = _clone(work, remote, "seed")
    install = _goc(seed, "install")
    if install.returncode != 0:
        raise SystemExit(f"goc install failed: {install.stderr}")
    config = seed / ".game-of-cards" / "config.yaml"
    if claim_push:
        text = config.read_text()
        if SHIPPED_OFF not in text:
            raise SystemExit("the shipped config no longer carries the commented claim_push line")
        config.write_text(text.replace(SHIPPED_OFF, ENABLED, 1))
    card = seed / CARD_README
    card.parent.mkdir(parents=True)
    card.write_text(CARD_TEXT)
    _git(seed, "add", "-A")
    _git(seed, "commit", "-q", "-m", "seed")
    _git(seed, "push", "-q", "origin", "main")
    return remote


def observe() -> dict:
    facts: dict = {}
    with tempfile.TemporaryDirectory(prefix="goc-claim-protocol-") as tmp:
        work = Path(tmp) / "default"
        remote = _seed(work, claim_push=False)
        a, b = _clone(work, remote, "agent-A"), _clone(work, remote, "agent-B")
        before = _git(remote, "rev-parse", "main")
        facts["default_a"] = _goc(a, "status", CARD, "active")
        facts["default_b"] = _goc(b, "status", CARD, "active")
        facts["default_pushes"] = _git(remote, "rev-parse", "main") != before
        facts["default_detects_race"] = facts["default_b"].returncode != 0

        work = Path(tmp) / "claim_push"
        remote = _seed(work, claim_push=True)
        a, b = _clone(work, remote, "agent-A"), _clone(work, remote, "agent-B")
        before = _git(remote, "rev-parse", "main")
        facts["push_a"] = _goc(a, "status", CARD, "active")
        facts["push_b"] = _goc(b, "status", CARD, "active")
        facts["claim_push_pushes"] = _git(remote, "rev-parse", "main") != before
        facts["claim_push_remote"] = _remote_card(remote)
        facts["claim_push_winner"] = "first" if "agent-A" in facts["claim_push_remote"].get("worker", "") else "last"
        facts["loser_refused_naming_winner"] = facts["push_b"].returncode != 0 and "'agent-A'" in facts["push_b"].stderr

        work = Path(tmp) / "identical"
        remote = _seed(work, claim_push=True)
        c = _clone(work, remote, "runner-1", who="fleet-bot")
        d = _clone(work, remote, "runner-2", who="fleet-bot")
        facts["fleet_1"] = _goc(c, "status", CARD, "active", when="2026-10-04T00:00:00Z")
        facts["fleet_2"] = _goc(d, "status", CARD, "active", when="2026-10-04T00:00:05Z")
        facts["identical_claim_detected"] = facts["fleet_2"].returncode != 0

        work = Path(tmp) / "offline"
        remote = _seed(work, claim_push=True)
        e = _clone(work, remote, "agent-E")
        _git(e, "remote", "set-url", "origin", str(work / "unreachable.git"))
        facts["offline"] = _goc(e, "status", CARD, "active")
        facts["offline_claim_committed"] = _git(e, "rev-list", "--count", "origin/main..HEAD") == "1"
    return facts


def _row(doc: Path, section: str) -> str:
    text = doc.read_text()
    start = text.index(section)
    end = text.find("\n### ", start + 1)
    for line in text[start : end if end != -1 else len(text)].splitlines():
        if line.startswith("| Same repo |"):
            return line
    raise SystemExit(f"{doc} has no Same-repo row under {section!r}")


def contradictions(claim_row: str, offline_row: str, facts: dict) -> list[str]:
    found: list[str] = []
    for sentence in re.split(r"(?<=[.;])\s+", claim_row):
        if "goc status" in sentence and re.search(r"\bpush(?:es)?\b", sentence) and "claim_push" not in sentence:
            if not facts["default_pushes"]:
                found.append(f"says goc pushes the claim, but a default claim does not push: {sentence.strip()!r}")
    lowered = claim_row.lower()
    says_last = re.search(r"last[- ]writer[- ]wins", lowered)
    says_first = re.search(r"first[- ]writer[- ]wins", lowered)
    if facts["claim_push_winner"] == "first" and (says_last or not says_first):
        found.append("does not say the first writer wins, but with claim_push the later claimer is refused")
    if facts["claim_push_winner"] == "last" and (says_first or not says_last):
        found.append("does not say the last writer wins, but with claim_push the later claim replaced the first")
    if not facts["default_detects_race"] and not re.search(r"nothing detects", lowered):
        found.append("never says that under the default config nothing detects a racing claim")
    if not facts["identical_claim_detected"] and IDENTICAL_CLAIM_CARD not in claim_row:
        found.append("omits that an identical claim (one shared worker identity) reports success under claim_push")
    if facts["identical_claim_detected"] and IDENTICAL_CLAIM_CARD in claim_row:
        found.append("still documents the identical-claim hole, but the engine now refuses that claim")
    if facts["offline"].returncode != 0 and re.search(r"push deferred", offline_row, re.I) and "claim_push" not in offline_row:
        found.append("Offline row says the push is deferred, but an offline claim_push claim exits non-zero")
    return found


def _last(stream: str) -> str:
    lines = stream.strip().splitlines()
    return lines[-1] if lines else ""


def main() -> int:
    doc = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "DECK_LOCATION.md"
    facts = observe()
    print("Observed:")
    print(f"  default config: claim pushed to the remote: {facts['default_pushes']}")
    print(f"    agent-A: exit {facts['default_a'].returncode}, stdout ends {_last(facts['default_a'].stdout)!r}")
    print(f"    agent-B (stale): exit {facts['default_b'].returncode}, stderr {facts['default_b'].stderr.strip()!r}")
    print(f"  default config: racing claim detected: {facts['default_detects_race']}")
    print(f"  claim_push: claim pushed to the remote: {facts['claim_push_pushes']}")
    print(f"    agent-B (stale): exit {facts['push_b'].returncode}, stderr {facts['push_b'].stderr.strip()!r}")
    print(f"    remote card after both claims: {facts['claim_push_remote']}")
    print(f"  claim_push: winner = {facts['claim_push_winner']} writer;"
          f" loser refused naming the winner: {facts['loser_refused_naming_winner']}")
    print(f"  claim_push, one identity: second claim exit {facts['fleet_2'].returncode},"
          f" stdout ends {_last(facts['fleet_2'].stdout)!r}")
    print(f"  claim_push, offline: exit {facts['offline'].returncode},"
          f" claim committed locally: {facts['offline_claim_committed']},"
          f" stderr starts {facts['offline'].stderr.strip().splitlines()[0]!r}")
    claim_row = _row(doc, "### Claim and sync semantics")
    offline_row = _row(doc, "### Offline behavior")
    found = contradictions(claim_row, offline_row, facts)
    print()
    print(f"{doc.name} claim row:\n  {claim_row}")
    print(f"{doc.name} offline row:\n  {offline_row}")
    print()
    if found:
        print(f"{len(found)} claim(s) contradicted:")
        for item in found:
            print(f"  - {item}")
        return 1
    print("Both rows match the observed claim protocol.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
