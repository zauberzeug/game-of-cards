"""`goc wait` writes an impediment overlay onto a closed card.

One throwaway deck holds a `done`, a `disproved` and a `superseded` card plus
a live `open` control. Each closed card gets three `goc wait` calls — the
`--reason` setter, the bare `--until` setter, and `--clear` against an overlay
the card carried from its live state — and its README bytes are compared
before and after. A closed card is the deck's record; the overlay is the live
"cannot pull yet" signal, so every call must exit non-zero and leave the card
byte-identical. `--clear` is refused too: an overlay inherited from before
closure is history, and wiping it is a post-close mutation like any other.

The control runs the `--reason` setter on the open card. It must succeed and
write the overlay, or it is the harness — not a guard — that stopped the
closed-card writes.

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = the harness or
a precondition is broken.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()

CARD = """---
title: {title}
summary: "Probe card for the goc wait terminal guard."
status: {status}
stage: null
contribution: medium
created: "2026-05-29T00:00:00Z"
closed_at: {closed_at}
human_gate: none
advances: []
advanced_by: []
{edges}tags: [bug]
{overlay}definition_of_done: |
  - [x] MECHANICAL: probe.
---

# {title}

Body.
"""

# (title, status, extra edge lines, overlay inherited from the live state)
CARDS = [
    ("done-card", "done", "", "waiting_on: external\n"),
    ("disproved-card", "disproved", "", "waiting_until: 2026-06-01\n"),
    ("superseded-card", "superseded", "superseded_by:\n  - live-card\n", "waiting_on: resource\n"),
    ("live-card", "open", "supersedes:\n  - superseded-card\n", ""),
]

TERMINAL_CALLS = [
    ("--reason setter", ["--reason", "external", "--until", "2027-01-01"]),
    ("bare --until setter", ["--until", "2027-01-01"]),
    ("--clear", ["--clear"]),
]


def build_deck(root: Path) -> Path:
    deck = root / ".game-of-cards" / "deck"
    for title, status, edges, overlay in CARDS:
        card = deck / title
        card.mkdir(parents=True)
        closed_at = "null" if status == "open" else '"2026-05-30T00:00:00Z"'
        (card / "README.md").write_text(CARD.format(
            title=title, status=status, closed_at=closed_at,
            edges=edges, overlay=overlay,
        ))
        (card / "log.md").write_text("")
    return deck


def goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env.pop("GOC_WORKTREE_DECK", None)
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args, "--no-commit"],
        cwd=str(cwd), env=env, text=True, capture_output=True, check=False,
    )


def main() -> int:
    fired: list[str] = []
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        deck = build_deck(root)

        control = goc(root, "wait", "live-card", "--reason", "external")
        live_text = (deck / "live-card" / "README.md").read_text()
        print(f"control  live-card --reason external: exit {control.returncode}")
        if control.returncode != 0 or "waiting_on: external" not in live_text:
            print("[HARNESS] the open-card control did not write its overlay:")
            print(control.stdout + control.stderr)
            return 2

        for title, status, _edges, _overlay in CARDS:
            if status == "open":
                continue
            readme = deck / title / "README.md"
            for label, flags in TERMINAL_CALLS:
                before = readme.read_bytes()
                res = goc(root, "wait", title, *flags)
                changed = readme.read_bytes() != before
                print(f"{status:<10} {title} {label}: exit {res.returncode}, "
                      f"README {'CHANGED' if changed else 'unchanged'}")
                if res.returncode == 0 or changed:
                    fired.append(f"{title} ({status}) {label}: exit "
                                 f"{res.returncode}, README changed={changed}")
                if changed:
                    readme.write_bytes(before)
                elif res.returncode != 0 and title not in res.stderr:
                    fired.append(f"{title} {label}: refusal does not name the card: "
                                 f"{res.stderr.strip()!r}")

    print()
    if fired:
        for line in fired:
            print(f"[DEFECT] {line}")
        return 1
    print("defect no longer fires: every closed card refused all three calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
