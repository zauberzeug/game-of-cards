"""Prove the two newest surfaces that forgot the `card_is_draft` gate.

1. `goc quality-pass` filters only on status (engine.py:4088-4089), so
   unauthored draft scaffolds — hidden from every listing — flow into
   the audit report (and into the `--llm` rewrite sample).
2. `goc decide` has no draft guard (engine.py:5951 ff.) and, after
   lowering the gate, prints "any agent can now claim this card"
   (engine.py:6000) — false while `draft: true` keeps the card out of
   the queue and `--ready`.

Exits 0 while both legs fire, 1 once fixed.
"""

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


def goc(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "consumer-repo"
        (repo / ".game-of-cards" / "deck").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)

        # An unauthored scaffold, parked on a decision gate (the exact
        # state `goc new --gate decision` leaves behind).
        goc(repo, "new", "unauthored-scaffold", "--gate", "decision")

        readme = (repo / ".game-of-cards" / "deck" / "unauthored-scaffold"
                  / "README.md").read_text()
        assert "draft: true" in readme, "scaffold should be born a draft"

        r = goc(repo, "--no-color")
        hidden_from_queue = "unauthored-scaffold" not in r.stdout

        r = goc(repo, "quality-pass")
        qp_audits_draft = "unauthored-scaffold" in r.stdout
        print(f"queue hides the draft: {hidden_from_queue}; "
              f"quality-pass audits it anyway: {qp_audits_draft}")

        r = goc(repo, "decide", "unauthored-scaffold",
                "--decision", "go with blue", "--because", "obvious")
        claim_msg = "any agent can now claim this card" in r.stdout
        readme = (repo / ".game-of-cards" / "deck" / "unauthored-scaffold"
                  / "README.md").read_text()
        still_draft = "draft: true" in readme
        r = goc(repo, "--ready", "--json")
        still_hidden = "unauthored-scaffold" not in r.stdout
        print(f"decide prints 'any agent can now claim this card': {claim_msg}; "
              f"draft flag persists: {still_draft}; "
              f"card still absent from --ready: {still_hidden}")

        defect = (hidden_from_queue and qp_audits_draft
                  and claim_msg and still_draft and still_hidden)

    if defect:
        print("DEFECT CONFIRMED: quality-pass audits draft scaffolds and "
              "decide falsely announces a hidden draft as claimable.")
        return 0
    print("defect no longer fires (fixed)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
