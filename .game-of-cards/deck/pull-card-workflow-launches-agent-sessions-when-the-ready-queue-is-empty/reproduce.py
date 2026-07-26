"""Reproduce: pull-card.yml's queue gate counts cards goc --ready refuses.

Part A (engine behavior, hermetic): a scratch deck with one open,
gate-none card carrying an active `waiting_on: external` overlay is
counted by the workflow's predicate (`--status open --human-gate none`)
but excluded by the picker's predicate (`--ready`).

Part B (the defect): `.github/workflows/pull-card.yml` still gates its
agent-launch and self-retrigger steps on the Part-A workflow predicate,
so it launches (and re-launches, up to MAX_ITERATIONS) agent sessions
that can pull nothing.

Exits non-zero while the defect is present; exits zero once the
workflow counts `goc --ready --json` instead.
"""

import json
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


def goc(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        subprocess.run(["git", "init", "-q", str(scratch)], check=True)
        deck = scratch / ".game-of-cards" / "deck"
        deck.mkdir(parents=True)
        card = deck / "impeded-open-card"
        card.mkdir()
        (card / "README.md").write_text(
            "---\n"
            "title: impeded-open-card\n"
            "status: open\n"
            "stage: null\n"
            "contribution: medium\n"
            'created: "2026-07-23T00:00:00Z"\n'
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "waiting_on: external\n"
            "definition_of_done: |\n"
            "  - [ ] anything\n"
            "---\n\n# impeded-open-card\n"
        )
        (card / "log.md").write_text("")

        workflow_pred = goc(scratch, "--status", "open", "--human-gate", "none", "--json")
        ready_pred = goc(scratch, "--ready", "--json")
        n_workflow = len(json.loads(workflow_pred.stdout))
        n_ready = len(json.loads(ready_pred.stdout))
        print(f"workflow predicate (--status open --human-gate none): {n_workflow} card(s)")
        print(f"picker predicate   (--ready):                         {n_ready} card(s)")
        assert n_workflow == 1 and n_ready == 0, (
            "scratch-deck premise failed — predicates no longer diverge on "
            f"waiting-impeded cards (workflow={n_workflow}, ready={n_ready})"
        )

    workflow_text = (ROOT / ".github" / "workflows" / "pull-card.yml").read_text()
    drifting = "--status open --human-gate none --json" in workflow_text
    counts_ready = "--ready --json" in workflow_text
    if drifting or not counts_ready:
        print(
            "[FAIL] pull-card.yml still counts the queue with "
            "`--status open --human-gate none` — it launches agent sessions "
            "(and self-retriggers) for cards the picker's `--ready` refuses."
        )
        return 1
    print("[OK] pull-card.yml counts the queue with `goc --ready --json` — gate matches the picker.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
