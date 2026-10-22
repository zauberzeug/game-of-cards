#!/usr/bin/env python3
"""Reproduce: `goc decide` on a card parked while `active` strands it.

Drives the real `goc` CLI through the Skill(pull-card) Andon round trip in a
scratch git repo:

  1. `goc new probe-card --gate none`, then author the DoD (not a draft).
  2. `goc status probe-card active`     — pull-card claims before working.
  3. raise `human_gate: decision` by hand, add `## Decision required`, commit
                                         — pull-card's Andon step; nothing
                                           releases the claim.
  4. `goc decide probe-card --decision a --because b`
                                         — the human's one-action handoff.

Then asks the three surfaces an autonomous worker reads whether the decided
card is pullable again:

  * `goc --ready --json`                            (Skill(pull-card) / next-card)
  * `goc --status open --human-gate none --json`    (pull-card.yml launch count)
  * `goc decide`'s own `Next:` line, which promises "any agent can now claim
    this card" — true only if the card is back in the queue.

Exits 0 when the decided card is pullable on every surface (fixed engine);
exits 1 when it is stranded at `status: active` + `human_gate: none`, the shape
of a live agent claim (the bug).

    uv run python .game-of-cards/deck/deciding-a-card-parked-while-active-strands-it-outside-the-pull-queue/reproduce.py
"""
from __future__ import annotations

import json
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
TITLE = "probe-card"


def goc(cwd: Path, *argv: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env.pop("GOC_WORKER", None)
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *argv],
        cwd=cwd, env=env, capture_output=True, text=True,
    )


def git(cwd: Path, *argv: str) -> None:
    subprocess.run(["git", *argv], cwd=cwd, check=True, capture_output=True)


def frontmatter_field(readme: Path, field: str) -> str:
    m = re.search(rf"^{field}: (.*)$", readme.read_text(), re.MULTILINE)
    return m.group(1).strip() if m else "<absent>"


def titles(proc: subprocess.CompletedProcess) -> list[str]:
    return [c["title"] for c in json.loads(proc.stdout or "[]")]


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        (repo / ".game-of-cards" / "deck").mkdir(parents=True)
        git(repo, "init", "-q", ".")
        git(repo, "config", "user.name", "Probe User")
        git(repo, "config", "user.email", "probe@example.com")
        readme = repo / ".game-of-cards" / "deck" / TITLE / "README.md"

        # 1. File an authored, gate-free card.
        new = goc(repo, "new", TITLE, "--gate", "none", "--summary", "probe card")
        assert new.returncode == 0, new.stderr
        text = readme.read_text()
        text = re.sub(
            r"definition_of_done: \|\n(?:  .*\n)+",
            "definition_of_done: |\n  - [ ] MECHANICAL: probe item\n",
            text,
        )
        readme.write_text(text)

        # 2. Claim it — Skill(pull-card) step 1.
        claim = goc(repo, "status", TITLE, "active")
        assert claim.returncode == 0, claim.stderr

        # 3. The Andon step: raise the gate on the claimed card and commit.
        text = readme.read_text().replace("human_gate: none", "human_gate: decision")
        text += "\n## Decision required\n\n- **A** — one way.\n- **B** — another way.\n"
        readme.write_text(text)
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", f"park {TITLE} at decision")
        parked_status = frontmatter_field(readme, "status")

        # 4. The human decides.
        decide = goc(repo, "decide", TITLE, "--decision", "a", "--because", "b")
        assert decide.returncode == 0, decide.stderr

        status = frontmatter_field(readme, "status")
        gate = frontmatter_field(readme, "human_gate")
        ready = TITLE in titles(goc(repo, "--ready", "--json"))
        launch = TITLE in titles(
            goc(repo, "--status", "open", "--human-gate", "none", "--json")
        )
        claimed = TITLE in titles(goc(repo, "--status", "active", "--json"))
        next_line = next(
            (ln for ln in decide.stdout.splitlines() if ln.startswith("Next:")), "<none>"
        )
        promises_claimable = "can now claim" in next_line
        validate = goc(repo, "validate")

        print(f"=== `goc decide {TITLE} --decision a --because b` ===")
        print(decide.stdout.rstrip())
        print()
        print(f"status while parked:                        {parked_status}")
        print(f"status / gate after decide:                 {status} / {gate}")
        print(f"listed by `goc --ready --json`:             {ready}")
        print(f"counted by pull-card.yml's launch query:    {launch}")
        print(f"listed by `goc --status active` (soft lock): {claimed}")
        print(f"Next: line promises the card is claimable:  {promises_claimable}")
        print(f"`goc validate` exit:                        {validate.returncode}")
        print()

        if parked_status != "active" or gate != "none":
            print("SETUP FAILED: the probe did not reproduce the parked-active shape.")
            return 2
        if ready and launch and not claimed and validate.returncode == 0:
            print("PASS: the decided card is back in the pull queue on every surface.")
            return 0
        print(
            "FAIL: the decided card is stranded at status active + human_gate none —"
            " the shape of a live agent claim — so no autonomous worker pulls it,"
            " while `goc decide` says any agent can now claim it."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
