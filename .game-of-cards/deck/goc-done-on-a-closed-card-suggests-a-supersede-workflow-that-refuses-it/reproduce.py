"""`goc done` answers a closed card with advice that `goc status` refuses.

One throwaway deck holds a `disproved` card, a `superseded` card and the open
card that superseded it. `goc done` — single and `--bundle` — is run against
each closed card, and the refusal's advice is then followed: the
"supersede/disprove workflow" is `goc status <card> superseded --by <new>` or
`goc status <card> disproved`, and `goc status` refuses (or no-ops) both on a
closed card. The defect fires while a refusal still names that workflow; it is
gone once the refusal names the post-close amendment path instead.

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = the harness or
a precondition is broken (for instance `goc done` no longer refusing at all).
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
summary: "Probe card for the goc done refusal message."
status: {status}
stage: null
contribution: medium
created: "2026-05-29T00:00:00Z"
closed_at: {closed_at}
human_gate: none
advances: []
advanced_by: []
{edges}tags: [bug]
definition_of_done: |
  - [x] MECHANICAL: probe.
---

# {title}

Body.
"""

CARDS = [
    ("disproved-card", "disproved", ""),
    ("superseded-card", "superseded", "superseded_by:\n  - live-card\n"),
    ("live-card", "open", "supersedes:\n  - superseded-card\n"),
]

STALE_ADVICE = "supersede/disprove workflow"
FORWARD_PATH = "post-close amendment"


def goc(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env.pop("GOC_WORKTREE_DECK", None)
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(cwd), env=env, text=True, capture_output=True, check=False,
    )


def main() -> int:
    fired: list[str] = []
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        deck = root / ".game-of-cards" / "deck"
        for title, status, edges in CARDS:
            card = deck / title
            card.mkdir(parents=True)
            closed_at = "null" if status == "open" else '"2026-05-30T00:00:00Z"'
            (card / "README.md").write_text(CARD.format(
                title=title, status=status, closed_at=closed_at, edges=edges,
            ))
            (card / "log.md").write_text("")

        for title, status, _ in CARDS[:2]:
            for label, args in (
                ("goc done", ("done", title)),
                ("goc done --bundle", ("done", "--bundle", title, "live-card")),
            ):
                readme = deck / title / "README.md"
                before = readme.read_bytes()
                res = goc(root, *args)
                print(f"{label} {title} ({status}): exit {res.returncode}")
                print(f"  {res.stderr.strip()}")
                if res.returncode == 0 or readme.read_bytes() != before:
                    print("[HARNESS] goc done no longer refuses a closed card")
                    return 2
                if STALE_ADVICE in res.stderr or FORWARD_PATH not in res.stderr:
                    fired.append(f"{label} on a {status} card names no working forward path")

        # Follow the advice: both halves of the supersede/disprove workflow.
        print()
        for args in (
            ("status", "disproved-card", "superseded", "--by", "live-card", "--no-commit"),
            ("status", "superseded-card", "disproved", "--no-commit"),
        ):
            res = goc(root, *args)
            out = (res.stderr or res.stdout).strip()
            print(f"goc {' '.join(args[:-1])}: exit {res.returncode}")
            print(f"  {out}")
            if res.returncode == 0:
                print("[HARNESS] goc status now moves a closed card; re-check the premise")
                return 2

    print()
    if fired:
        for line in fired:
            print(f"[DEFECT] {line}")
        return 1
    print("defect no longer fires: every refusal names the post-close amendment path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
