"""Regression guard: no doc or shipped template says git's merge settles a claim race.

The shipped deck skill (`SKILL.md` and `reference.md`) and `ABOUT.md` said
git's merge handles a simultaneous claim race, whichever commits first wins.
A claim is a local commit and `workflow.claim_push` is off by default, so two
clones can both claim one card and both succeed. Nothing merges at claim time:
the race surfaces at the earliest when the second worker integrates, and under
one shared identity the two claims are identical, so integrating them raises
nothing at all
(`deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects`).

`DECK_LOCATION.md` had already lost the same reassurance, but its guard
(`tests/test_deck_location_claim_rows.py`) reads that one page, so the copies
in the deck skill and `ABOUT.md` survived it. This guard is keyed to the claim
instead of a file: it sweeps every tracked file outside the deck's cards and
`tests/`, which quote the claims they retire, so the skill mirrors and plugin
payloads are covered too. It observes a default claim against a scratch bare
remote seeded with the shipped config template, and while that claim does not
push:

- no swept file may say a merge or rebase handles, settles, resolves or
  decides a claim race, or that whichever commits first wins;
- each passage that carried the claim must say a claim stays in the
  claimer's clone by default, and name `workflow.claim_push`, the opt-in that
  refuses a later conflicting claimer.

Once a default claim pushes, the passage check runs the other way: no passage
may still say the claim stays in the clone. Both checks are fed the pre-fix
wording verbatim, and the current wording under the flipped observation, to
prove they fire.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_TEMPLATE = ROOT / "goc" / "templates" / "game_of_cards" / "config.yaml"

# Records, not guidance: cards quote the claims they retire, and tests quote
# them as fixtures.
RECORD_PREFIXES = (".game-of-cards/deck/", "tests/")

# The source-of-truth passages that carried the claim. Their mirrors are held
# to them by the sync and OpenClaw-port checks.
PASSAGES = (
    "goc/templates/skills/deck/SKILL.md",
    "goc/templates/skills/deck/reference.md",
    "ABOUT.md",
)

PRE_FIX = {
    "goc/templates/skills/deck/SKILL.md": (
        "Multiple sessions work cards in parallel. `status: active` is the\n"
        "soft lock; git's merge handles the rare simultaneous-claim race\n"
        "(whichever commits first wins).\n"
    ),
    "goc/templates/skills/deck/reference.md": (
        "Multiple Claude sessions on the same project work cards in parallel.\n"
        "The `status: active` field is the soft lock; git's merge handles\n"
        "the rare race when two sessions claim the same card simultaneously\n"
        "(whichever commits first wins). The user can have N parallel chats\n"
        "going while M scheduled agents work the deck — they ride the events\n"
        "as they occur, present or absent as resources allow.\n"
    ),
    "ABOUT.md": (
        "4. **Multiple parallel realities are normal.** N sessions + M scheduled"
        " agents working the same project is the default mode, not the exception."
        " The `status: active` field is the soft lock; git's merge handles"
        " claim-races. The deck design assumes the swarm is heterogeneous and"
        " partially-coordinated — exactly like GRRM's Westeros: nobody has the"
        " full picture, decisions are made on partial information, and the realm"
        " muddles forward anyway.\n"
    ),
}

CARD = "race-card"
CARD_TEXT = """\
---
title: race-card
summary: "A card a worker claims."
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

_MERGE_SETTLES_RACE = re.compile(
    r"\b(?:merge|rebase)\s+(?:handles|settles|resolves|decides)\b[^.;]*?\b(?:race|claim)",
    re.IGNORECASE,
)
_COMMIT_FIRST_WINS = re.compile(r"\bwhichever\s+commits\s+first\s+wins\b", re.IGNORECASE)
_SOFT_LOCK = re.compile(r"\bthe\s+soft\s+lock\b")
_STAYS_IN_CLONE = re.compile(r"\bby\s+default\s+a\s+claim\s+stays\s+in\b", re.IGNORECASE)


def _env() -> dict[str, str]:
    drop = {"CLAUDECODE", "CLAUDE_CODE", "CLAUDE_PROJECT_DIR", "GOC_WORKER", "GOC_WORKTREE_DECK"}
    env = {k: v for k, v in os.environ.items() if k not in drop and not k.startswith("GIT_")}
    env["PYTHONPATH"] = str(ROOT)
    return env


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=_env(), check=True, capture_output=True, text=True
    ).stdout.strip()


def _clone(work: Path, remote: Path, name: str) -> Path:
    dest = work / name
    _git(work, "clone", "-q", str(remote), str(dest))
    _git(dest, "config", "user.name", name)
    _git(dest, "config", "user.email", f"{name}@example.com")
    return dest


def default_claim_pushes(work: Path) -> bool:
    """Claim a card under the shipped config and report whether the remote moved."""
    remote = work / "remote.git"
    _git(work, "init", "-q", "--bare", "-b", "main", str(remote))
    seed = _clone(work, remote, "seed")
    (seed / ".game-of-cards").mkdir()
    (seed / ".game-of-cards" / "config.yaml").write_text(CONFIG_TEMPLATE.read_text())
    card = seed / ".game-of-cards" / "deck" / CARD / "README.md"
    card.parent.mkdir(parents=True)
    card.write_text(CARD_TEXT)
    _git(seed, "add", "-A")
    _git(seed, "commit", "-q", "-m", "seed")
    _git(seed, "push", "-q", "origin", "main")

    agent = _clone(work, remote, "agent")
    before = _git(remote, "rev-parse", "main")
    claim = subprocess.run(
        [sys.executable, "-m", "goc.cli", "status", CARD, "active"],
        cwd=agent, env=_env(), capture_output=True, text=True,
    )
    if claim.returncode != 0:
        raise AssertionError(f"an uncontested claim failed (exit {claim.returncode}): {claim.stderr}")
    return _git(remote, "rev-parse", "main") != before


def swept_files() -> dict[str, str]:
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout
    files: dict[str, str] = {}
    for rel in listed.split("\0"):
        if not rel or rel.startswith(RECORD_PREFIXES):
            continue
        try:
            files[rel] = (ROOT / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary assets, or a tracked file deleted in the working tree
    return files


def _soft_lock_paragraph(text: str) -> str:
    for paragraph in re.split(r"\n[ \t]*\n", text):
        if _SOFT_LOCK.search(paragraph):
            return paragraph
    return ""


def problems(files: dict[str, str], default_pushes: bool) -> list[tuple[str, str, str]]:
    """(check, path, message) for every contradiction of the observed default."""
    found: list[tuple[str, str, str]] = []
    if not default_pushes:
        for rel, text in sorted(files.items()):
            for pattern in (_MERGE_SETTLES_RACE, _COMMIT_FIRST_WINS):
                for match in pattern.finditer(text):
                    line = text.count("\n", 0, match.start()) + 1
                    said = " ".join(match.group(0).split())
                    found.append(("merge-settles", rel, f"line {line} says {said!r}"))
    for rel in PASSAGES:
        paragraph = _soft_lock_paragraph(files.get(rel, ""))
        if not paragraph:
            found.append(("passage", rel, "no paragraph calls `status: active` the soft lock"))
            continue
        if bool(_STAYS_IN_CLONE.search(paragraph)) == default_pushes:
            state = "pushes" if default_pushes else "does not push"
            found.append(("passage", rel, f"a default claim {state}; say it stays in the clone only while it does not"))
        if not default_pushes and "claim_push" not in paragraph:
            found.append(("passage", rel, "names no `workflow.claim_push`, the only setting that refuses a racing claim"))
    return found


class ClaimRaceReassuranceTest(unittest.TestCase):
    default_pushes: bool
    files: dict[str, str]

    @classmethod
    def setUpClass(cls) -> None:
        if not (ROOT / ".git").exists():
            raise unittest.SkipTest("not a git checkout (sdist/wheel test run)")
        with tempfile.TemporaryDirectory(prefix="goc-claim-race-") as tmp:
            cls.default_pushes = default_claim_pushes(Path(tmp))
        cls.files = swept_files()

    def test_passages_are_swept(self) -> None:
        self.assertEqual([rel for rel in PASSAGES if rel not in self.files], [])

    def test_docs_match_the_observed_default_claim(self) -> None:
        found = problems(self.files, self.default_pushes)
        self.assertEqual(
            found, [],
            f"docs contradict the claim protocol goc ships (a default claim"
            f" {'pushes' if self.default_pushes else 'does not push'}):\n"
            + "\n".join(f"  [{check}] {rel}: {msg}" for check, rel, msg in found),
        )

    def test_pre_fix_wording_fires_every_check(self) -> None:
        fired = {(check, rel) for check, rel, _msg in problems(PRE_FIX, default_pushes=False)}
        expected = {(check, rel) for check in ("merge-settles", "passage") for rel in PASSAGES}
        self.assertEqual(fired, expected)

    def test_current_wording_fires_once_the_default_flips(self) -> None:
        current = {rel: self.files[rel] for rel in PASSAGES}
        fired = {(check, rel) for check, rel, _msg in problems(current, not self.default_pushes)}
        self.assertTrue({("passage", rel) for rel in PASSAGES} <= fired, fired)


if __name__ == "__main__":
    unittest.main()
