"""Reproduce: `goc move` renames a card whose status is already terminal.

Builds a throwaway two-card deck: `dummy-closed-card` (`done`) and
`dummy-open-card` (`open`), whose body links to the closed card. Each scenario
starts from a fresh copy of that deck:

- `goc move dummy-closed-card renamed-closed-card` — the defect. Unguarded,
  the verb exits 0, renames the closed card's directory and rewrites every
  reference to its slug, including the open card's link. Fixed means it is
  refused by the terminal-status guard (exit 2, "(terminal)" and the
  `--force` escape hatch on stderr) with every deck file byte-identical.
- `goc move dummy-open-card renamed-open-card` — the paired positive case: a
  live card still renames.
- `goc move dummy-closed-card renamed-closed-card --force` — the decided
  escape hatch: a deliberate retitle of a closed card still renames.

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = harness or
precondition broken (including a fix that broke either positive case).

Run via `uv run python .game-of-cards/deck/goc-move-renames-terminal-status-cards-without-any-guard/reproduce.py`.
"""

from __future__ import annotations

import os
import shutil
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


REPO_ROOT = _repo_root()


CLOSED_README = """\
---
title: dummy-closed-card
summary: "A closed card used to reproduce the goc-move closed-card defect."
status: done
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: "2026-01-02T00:00:00Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: closed
---

# dummy-closed-card

Closed for reproduction purposes.
"""

CLOSED_LOG = """\
## 2026-01-02T00:00:00Z: closure

Closed.
"""

OPEN_README = """\
---
title: dummy-open-card
summary: "A live card whose body links to the closed card."
status: open
stage: null
contribution: low
created: "2026-01-03T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] TDD: open
---

# dummy-open-card

Follows up on [dummy-closed-card](../dummy-closed-card/).
"""

CONFIG_YAML = """\
workflow:
  auto_commit: false
"""


def _build_deck() -> Path:
    workdir = Path(tempfile.mkdtemp(prefix="goc-move-repro-"))
    subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
    subprocess.run(["git", "config", "user.email", "x@y"], cwd=workdir, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=workdir, check=True)
    (workdir / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
    deck = workdir / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)
    (workdir / ".game-of-cards" / "config.yaml").write_text(CONFIG_YAML)
    for slug, readme, log in (
        ("dummy-closed-card", CLOSED_README, CLOSED_LOG),
        ("dummy-open-card", OPEN_README, ""),
    ):
        (deck / slug).mkdir()
        (deck / slug / "README.md").write_text(readme)
        (deck / slug / "log.md").write_text(log)
    subprocess.run(["git", "add", "."], cwd=workdir, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=workdir, check=True)
    return workdir


def _snapshot(deck: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(deck)): p.read_bytes()
        for p in sorted(deck.rglob("*"))
        if p.is_file()
    }


def _move(*args: str) -> tuple[subprocess.CompletedProcess[str], dict[str, bytes], dict[str, bytes]]:
    """Run `goc move <args>` on a fresh deck; return (result, deck before, deck after)."""
    workdir = _build_deck()
    try:
        deck = workdir / ".game-of-cards" / "deck"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        env.pop("GOC_WORKTREE_DECK", None)
        before = _snapshot(deck)
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "move", *args],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
        )
        return result, before, _snapshot(deck)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _report(label: str, result: subprocess.CompletedProcess[str]) -> None:
    print("=" * 72)
    print(label)
    print("=" * 72)
    print("exit code:", result.returncode)
    print("--- stdout ---")
    print(result.stdout)
    print("--- stderr ---")
    print(result.stderr)


def _renamed(after: dict[str, bytes], old: str, new: str) -> bool:
    return f"{new}/README.md" in after and f"{old}/README.md" not in after


def main() -> int:
    try:
        closed, closed_before, closed_after = _move("dummy-closed-card", "renamed-closed-card")
        live, _, live_after = _move("dummy-open-card", "renamed-open-card")
        forced, _, forced_after = _move("dummy-closed-card", "renamed-closed-card", "--force")
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"HARNESS BROKEN: {exc}")
        return 2

    _report("goc move dummy-closed-card renamed-closed-card  (card status: done)", closed)
    changed = sorted(
        path for path in closed_before.keys() | closed_after.keys()
        if closed_before.get(path) != closed_after.get(path)
    )
    refused = (
        closed.returncode == 2
        and "(terminal)" in closed.stderr
        and "--force" in closed.stderr
    )
    print(f"  deck files changed:                {changed or 'none'}")
    print(f"  refused by terminal guard:         {refused}")
    print()

    _report("goc move dummy-open-card renamed-open-card  (card status: open)", live)
    live_ok = live.returncode == 0 and _renamed(live_after, "dummy-open-card", "renamed-open-card")
    print(f"  live card renamed:                 {live_ok}")
    print()

    _report("goc move dummy-closed-card renamed-closed-card --force  (card status: done)", forced)
    forced_ok = forced.returncode == 0 and _renamed(
        forced_after, "dummy-closed-card", "renamed-closed-card"
    )
    print(f"  closed card renamed under --force: {forced_ok}")
    print()

    if changed:
        print(
            "DEFECT REPRODUCED: `goc move` retitled a closed card without being told "
            "to. Its slug is part of the deck's record, and the rename rewrote every "
            "reference to it — the open card's link included."
        )
        return 1
    if not refused:
        print(
            "HARNESS BROKEN: `goc move` left the closed card alone but was not refused "
            "by the terminal-status guard naming `--force`; inspect the output above."
        )
        return 2
    if not (live_ok and forced_ok):
        print(
            "HARNESS BROKEN: the closed card is refused, but a live-card rename or the "
            "`--force` retitle no longer works; inspect the output above."
        )
        return 2
    print(
        "No defect — `goc move` refused the closed card unless forced and left the "
        "deck untouched, while live cards and `--force` retitles still rename."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
