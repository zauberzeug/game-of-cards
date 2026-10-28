"""Check that `goc decide` refuses a blank `--decision` or `--because`.

The defect: argparse's `required=True` on both options enforces presence
only, so `goc decide <t> --decision '' --because ''` passed. `_cmd_decide`
then lowered the gate to `none`, wrote a `## Decision` block with nothing
after `*Resolved …:*` and `*Reasoning:*`, appended a log entry reading
` — . Gate decision → none.`, printed `decision recorded` and exited 0 —
a forged Andon-cord handoff the next puller takes at face value. Fixed, a
blank value in either option (or both) is refused: non-zero exit, `ERROR:`
on stderr, no success line, README and log.md untouched. A decision with
both values filled in, the control, is still recorded.

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = the harness or
a precondition is broken.

Run with:  uv run python .game-of-cards/deck/goc-decide-accepts-empty-decision-and-because-arguments/reproduce.py
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


REPO = _repo_root()

PARKED_CARD = """---
title: {slug}
summary: "Probe card parked on a decision."
status: open
stage: null
contribution: medium
created: "2026-05-29T00:00:00Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] MECHANICAL: probe.
---

# {slug}

## Decision required

Pick option A or option B.
"""

# (card, --decision, --because): each blank combination on its own card, so
# a call that wrongly lowers one gate cannot make the next case look refused.
CASES = (
    ("blank-decision", "", "Option A is simpler."),
    ("blank-because", "Option A.", ""),
    ("both-blank", "", ""),
)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        deck_root = Path(tmp) / "deck-root"
        gocdir = deck_root / ".game-of-cards"
        deck = gocdir / "deck"
        deck.mkdir(parents=True)
        (gocdir / "config.yaml").write_text("skills_source: vendored\n")
        for slug in ("control", *(case[0] for case in CASES)):
            (deck / slug).mkdir()
            (deck / slug / "README.md").write_text(PARKED_CARD.format(slug=slug))
            (deck / slug / "log.md").write_text("")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
        env.pop("GOC_WORKTREE_DECK", None)

        def decide(slug: str, decision: str, because: str) -> subprocess.CompletedProcess:
            res = subprocess.run(
                [sys.executable, "-m", "goc.cli", "decide", slug,
                 "--decision", decision, "--because", because, "--no-commit"],
                cwd=deck_root,
                env=env,
                capture_output=True,
                text=True,
            )
            print(f"$ goc decide {slug} --decision {decision!r} --because {because!r}")
            print(f"  exit {res.returncode}")
            print(f"  stdout: {res.stdout.strip().splitlines()[0] if res.stdout.strip() else '(empty)'}")
            print(f"  stderr: {res.stderr.strip() or '(empty)'}")
            return res

        def files(slug: str) -> tuple[str, str]:
            return ((deck / slug / "README.md").read_text(), (deck / slug / "log.md").read_text())

        # The control: a decision with both values filled in is recorded.
        control = decide("control", "Option A.", "Option A is simpler.")
        readme, _ = files("control")
        if control.returncode != 0 or "decision recorded" not in control.stdout or "human_gate: none" not in readme:
            print("HARNESS: recording a real decision failed — the control is broken", file=sys.stderr)
            return 2

        accepted = []
        for slug, decision, because in CASES:
            print()
            before = files(slug)
            res = decide(slug, decision, because)
            after = files(slug)
            refused = (
                res.returncode != 0
                and "ERROR:" in res.stderr
                and "decision recorded" not in res.stdout
                and before == after
            )
            if not refused:
                accepted.append(slug)
                readme, log = after
                print("  resulting `## Decision` block:")
                for line in readme.split("## Decision\n\n", 1)[-1].rstrip().splitlines():
                    print(f"    | {line}")
                print("  resulting log.md tail:")
                for line in log.rstrip().splitlines()[-3:]:
                    print(f"    | {line}")

        if not accepted:
            print("\nFIXED: a blank --decision, --because or both is refused with nothing written;"
                  " a filled-in decision is still recorded.")
            return 0
        print(f"\nDEFECT FIRES: blank input accepted for {', '.join(accepted)}"
              " — the gate went down on a decision record with nothing in it.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
