"""Regression guard: DECK_LOCATION.md's claim rows must describe the claim protocol goc ships.

The Same-repo row of DECK_LOCATION.md's "Claim and sync semantics" table said
`goc status active` "autocommits and pushes" and that "Last-writer-wins on the
file resolves" a race between two claimers. A default claim only commits
locally, so nothing detects a race, and with `workflow.claim_push: true` the
first claim stays while the later claimer is refused. The Same-repo row of
"Offline behavior" said the push is deferred, but an offline `claim_push`
claim exits 2
(`deck-location-doc-says-claims-push-by-default-and-last-writer-wins`).

These tests run the protocol against scratch bare remotes and clones, using
the shipped config template, and check both rows against what happened. Every
check runs both ways, so it fails when the engine moves as well as when the
page does:

- the claim row says `claim_push` is off by default exactly when a default
  claim does not push, and then no sentence may say `goc status … active`
  pushes without naming `claim_push`;
- the claim row names the winner of a `claim_push` race, and only that one;
- the claim row says nothing detects a racing claim exactly when a default
  racing claim succeeds;
- the claim row links the open identical-claim card exactly while a
  same-identity claim still reports success, so whoever lands that card's
  decision has to update this page;
- the Offline row excepts `claim_push` from "push deferred" when an offline
  `claim_push` claim exits non-zero, and says it exits 2 only while it does.

Each check is fed the pre-fix wording verbatim, and the current wording with
every observation flipped, to prove it fires.
"""

from __future__ import annotations

import dataclasses
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "DECK_LOCATION.md"
CONFIG_TEMPLATE = ROOT / "goc" / "templates" / "game_of_cards" / "config.yaml"
IDENTICAL_CLAIM_CARD = "claim-push-reports-success-when-rebase-drops-identical-racing-claim"
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

PRE_FIX_CLAIM_ROW = (
    "| Same repo | Git on main. `goc status active` autocommits and pushes; other agents pull before"
    " claiming. | A worker that forgets to pull races a stale view of the queue. Last-writer-wins on the"
    " file resolves it (per the recorded decision in"
    " `design-claim-protocol-with-branch-and-author-metadata`). |"
)
PRE_FIX_OFFLINE_ROW = "| Same repo | Fully functional. Git push deferred; `goc` keeps working. |"

_GOC_PUSHES = re.compile(r"\bpush(?:es)?\b")
_OFF_BY_DEFAULT = re.compile(r"off by default", re.IGNORECASE)
_LAST_WINS = re.compile(r"last[- ]writer[- ]wins", re.IGNORECASE)
_FIRST_WINS = re.compile(r"first[- ]writer[- ]wins", re.IGNORECASE)
_NOTHING_DETECTS = re.compile(r"nothing detects", re.IGNORECASE)
_PUSH_DEFERRED = re.compile(r"push deferred", re.IGNORECASE)
_EXITS_NONZERO = re.compile(r"exits (?:2|non-zero)", re.IGNORECASE)

_CHECKS = ("default-push", "winner", "default-race", "identical-claim", "offline")


@dataclasses.dataclass(frozen=True)
class Observations:
    default_pushes: bool
    default_race_detected: bool
    claim_push_winner: str  # "first" or "last"
    identical_claim_detected: bool
    offline_claim_fails: bool


# What the engine did when the card was filed: the pre-fix rows contradict it.
FILED = Observations(
    default_pushes=False,
    default_race_detected=False,
    claim_push_winner="first",
    identical_claim_detected=False,
    offline_claim_fails=True,
)


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


def _claim(clone: Path, when: str | None = None) -> subprocess.CompletedProcess[str]:
    # A pinned commit date keeps two same-identity claims from landing in the
    # same second as byte-identical commits; the rebase path is the one tested.
    extra = {"GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when} if when else {}
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", "status", CARD, "active"],
        cwd=clone, env=_env(**extra), capture_output=True, text=True,
    )


def _seed(work: Path, *, claim_push: bool) -> Path:
    """A bare remote whose main holds a deck with one open card and the shipped config."""
    work.mkdir()
    remote = work / "remote.git"
    _git(work, "init", "-q", "--bare", "-b", "main", str(remote))
    seed = _clone(work, remote, "seed")
    config = CONFIG_TEMPLATE.read_text()
    if claim_push:
        config = re.sub(r"^[ \t]*claim_push:.*\n", "", config, flags=re.MULTILINE)
        config = re.sub(r"^workflow:\n", "workflow:\n  claim_push: true\n", config, count=1, flags=re.MULTILINE)
    (seed / ".game-of-cards").mkdir()
    (seed / ".game-of-cards" / "config.yaml").write_text(config)
    card = seed / ".game-of-cards" / "deck" / CARD / "README.md"
    card.parent.mkdir(parents=True)
    card.write_text(CARD_TEXT)
    _git(seed, "add", "-A")
    _git(seed, "commit", "-q", "-m", "seed")
    _git(seed, "push", "-q", "origin", "main")
    return remote


def _uncontested(claim: subprocess.CompletedProcess[str]) -> None:
    """A claim nobody races must succeed, or the observations mean nothing."""
    if claim.returncode != 0:
        raise AssertionError(f"an uncontested claim failed (exit {claim.returncode}): {claim.stderr}")


def _clone(work: Path, remote: Path, name: str, who: str | None = None) -> Path:
    dest = work / name
    _git(work, "clone", "-q", str(remote), str(dest))
    _git(dest, "config", "user.name", who or name)
    _git(dest, "config", "user.email", f"{name}@example.com")
    return dest


def observe(tmp: Path) -> Observations:
    remote = _seed(tmp / "default", claim_push=False)
    a, b = _clone(tmp / "default", remote, "agent-A"), _clone(tmp / "default", remote, "agent-B")
    before = _git(remote, "rev-parse", "main")
    _uncontested(_claim(a))
    default_b = _claim(b)
    default_pushes = _git(remote, "rev-parse", "main") != before

    remote = _seed(tmp / "claim_push", claim_push=True)
    a, b = _clone(tmp / "claim_push", remote, "agent-A"), _clone(tmp / "claim_push", remote, "agent-B")
    _uncontested(_claim(a))
    _claim(b)
    remote_card = _git(remote, "show", f"main:.game-of-cards/deck/{CARD}/README.md")
    winner = "first" if re.search(r"^worker: .*\bagent-A\b", remote_card, re.MULTILINE) else "last"

    remote = _seed(tmp / "identical", claim_push=True)
    one = _clone(tmp / "identical", remote, "runner-1", who="fleet-bot")
    two = _clone(tmp / "identical", remote, "runner-2", who="fleet-bot")
    _uncontested(_claim(one, when="2026-10-04T00:00:00Z"))
    second = _claim(two, when="2026-10-04T00:00:05Z")

    remote = _seed(tmp / "offline", claim_push=True)
    offline = _clone(tmp / "offline", remote, "agent-E")
    _git(offline, "remote", "set-url", "origin", str(tmp / "offline" / "unreachable.git"))
    offline_claim = _claim(offline)

    return Observations(
        default_pushes=default_pushes,
        default_race_detected=default_b.returncode != 0,
        claim_push_winner=winner,
        identical_claim_detected=second.returncode != 0,
        offline_claim_fails=offline_claim.returncode != 0,
    )


def _same_repo_row(text: str, section: str) -> str:
    start = text.index(section)
    end = text.find("\n### ", start + 1)
    for line in text[start : end if end != -1 else len(text)].splitlines():
        if line.startswith("| Same repo |"):
            return line
    raise AssertionError(f"DECK_LOCATION.md has no Same-repo row under {section!r}")


def problems(claim_row: str, offline_row: str, obs: Observations) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if bool(_OFF_BY_DEFAULT.search(claim_row)) == obs.default_pushes:
        state = "pushes" if obs.default_pushes else "does not push"
        found.append(("default-push", f"a default claim {state}; say claim_push is off by default only while it does not"))
    if not obs.default_pushes:
        for sentence in re.split(r"(?<=[.;])\s+", claim_row):
            if "goc status" in sentence and _GOC_PUSHES.search(sentence) and "claim_push" not in sentence:
                found.append(("default-push", f"says the claim is pushed, but a default claim is not: {sentence!r}"))
    says_first, says_last = bool(_FIRST_WINS.search(claim_row)), bool(_LAST_WINS.search(claim_row))
    if (says_first, says_last) != (obs.claim_push_winner == "first", obs.claim_push_winner == "last"):
        found.append(("winner", f"must say the {obs.claim_push_winner} writer wins a claim_push race, and only that"))
    if bool(_NOTHING_DETECTS.search(claim_row)) == obs.default_race_detected:
        state = "is refused" if obs.default_race_detected else "succeeds"
        found.append(("default-race", f"a default racing claim {state}; say nothing detects it only while it succeeds"))
    if obs.identical_claim_detected == (IDENTICAL_CLAIM_CARD in claim_row):
        state = "refuses" if obs.identical_claim_detected else "reports success for"
        found.append(("identical-claim", f"claim_push now {state} a same-identity racing claim; link {IDENTICAL_CLAIM_CARD} only while it reports success"))
    if obs.offline_claim_fails and _PUSH_DEFERRED.search(offline_row) and "claim_push" not in offline_row:
        found.append(("offline", "says the push is deferred, but an offline claim_push claim exits non-zero"))
    if not obs.offline_claim_fails and _EXITS_NONZERO.search(offline_row):
        found.append(("offline", "says an offline claim_push claim exits non-zero, but it succeeds"))
    return found


def _flipped(obs: Observations) -> Observations:
    return Observations(
        default_pushes=not obs.default_pushes,
        default_race_detected=not obs.default_race_detected,
        claim_push_winner="last" if obs.claim_push_winner == "first" else "first",
        identical_claim_detected=not obs.identical_claim_detected,
        offline_claim_fails=not obs.offline_claim_fails,
    )


class DeckLocationClaimRowsTest(unittest.TestCase):
    observed: Observations

    @classmethod
    def setUpClass(cls) -> None:
        with tempfile.TemporaryDirectory(prefix="goc-claim-rows-") as tmp:
            cls.observed = observe(Path(tmp))

    def _rows(self) -> tuple[str, str]:
        text = DOC.read_text()
        return (
            _same_repo_row(text, "### Claim and sync semantics"),
            _same_repo_row(text, "### Offline behavior"),
        )

    def test_rows_match_the_observed_claim_protocol(self) -> None:
        claim_row, offline_row = self._rows()
        found = problems(claim_row, offline_row, self.observed)
        self.assertEqual(
            found, [],
            f"DECK_LOCATION.md's Same-repo rows contradict the claim protocol goc ships"
            f" (observed {self.observed}):\n" + "\n".join(f"  [{check}] {msg}" for check, msg in found),
        )

    def test_pre_fix_wording_fires_every_check(self) -> None:
        fired = {check for check, _msg in problems(PRE_FIX_CLAIM_ROW, PRE_FIX_OFFLINE_ROW, FILED)}
        self.assertEqual(fired, set(_CHECKS))

    def test_current_wording_fires_every_check_once_the_engine_flips(self) -> None:
        # E.g. once the identical-claim card's decision lands and the engine
        # refuses that claim, the row's link to it must go.
        claim_row, offline_row = self._rows()
        fired = {check for check, _msg in problems(claim_row, offline_row, _flipped(self.observed))}
        self.assertEqual(fired, set(_CHECKS))


if __name__ == "__main__":
    unittest.main()
