"""Reproduce: `goc triage` silently truncates the `## Decision required`
preview at 6 lines with no overflow marker.

Builds a temp deck with one parked card whose decision section is 8 lines,
runs `goc triage`, and shows that the text view renders only 6 of them and
emits no `… +N more` indicator.
"""
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

DECISION_LINES = [
    "Option A: keep the cap at six lines.",
    "Option B: render the whole section.",
    "Option C: cap but advertise the overflow.",
    "Constraint 1: matches the board idiom.",
    "Constraint 2: the JSON path keeps full text.",
    "Constraint 3: readers act on this cold.",
    "LINE SEVEN MUST NOT VANISH SILENTLY.",
    "LINE EIGHT MUST NOT VANISH SILENTLY.",
]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        card = cwd / ".game-of-cards" / "deck" / "long-decision-card"
        card.mkdir(parents=True)
        decision_block = "\n".join(DECISION_LINES)
        (card / "README.md").write_text(
            "---\n"
            "title: long-decision-card\n"
            "summary: a parked card with a long decision section\n"
            "status: open\n"
            "stage: null\n"
            "contribution: medium\n"
            "created: 2026-05-04\n"
            "closed_at: null\n"
            "human_gate: decision\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [ ] decide\n"
            "---\n\n"
            "# long-decision-card\n\n"
            "## Decision required\n\n"
            f"{decision_block}\n"
        )
        (card / "log.md").write_text("")

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "--no-color", "triage"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    out = result.stdout
    rendered = [ln for ln in DECISION_LINES if ln in out]
    hidden = [ln for ln in DECISION_LINES if ln not in out]
    has_overflow_marker = "more" in out and "+" in out

    print(f"total preview lines : {len(DECISION_LINES)}")
    print(f"rendered (text view): {len(rendered)}")
    print(f"hidden silently     : {len(hidden)}")
    print(f"overflow indicator? : {'PRESENT' if has_overflow_marker else 'ABSENT'}")
    for ln in hidden:
        print(f"  dropped: {ln!r}")

    # Defect fires when lines are hidden AND no overflow marker is shown.
    bug_fires = len(hidden) > 0 and not has_overflow_marker
    if bug_fires:
        print("\nDEFECT CONFIRMED: lines dropped with no overflow marker.")
        return 1
    print("\nNo defect: overflow advertised or nothing dropped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
