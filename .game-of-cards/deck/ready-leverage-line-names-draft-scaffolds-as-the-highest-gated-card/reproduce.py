"""Proof that `goc --ready`'s leverage line names an unauthored `draft: true`
scaffold as the "Highest gated card" — a card that every other surface
(queue, board, `--status open`, the pullable set) correctly excludes as a
draft.

`render_leverage_line` builds its `open_gated` candidate set filtering only on
`status == "open"`, `human_gate in (decision, session)`, and
`not waiting_impedes(t)` — it omits the `card_is_draft` gate that the sibling
open-only predicate `card_is_ready` applies. So a freshly-filed `goc new`
scaffold with the default `decision` gate leaks into the operator's
leverage comparison as if it were real gated work being traded off.

Exercises the REAL shipping path: builds a temp deck with `goc new` +
`goc publish`, then runs `goc --ready` and inspects the leverage line.

Run: uv run python .game-of-cards/deck/ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card/reproduce.py

Exits 0 once the defect is fixed (the draft no longer appears in the leverage
line); exits 1 while the defect is present.
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


ROOT = _repo_root()


def _goc(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    return proc.stdout + proc.stderr


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        (repo / ".game-of-cards" / "deck").mkdir(parents=True)
        (repo / ".game-of-cards" / "config.yaml").write_text(
            "skills_source: vendored\n"
        )

        # An authored, ready, low-contribution card (open, gate none, not draft).
        _goc(repo, "new", "real-ready", "--contribution", "low", "--gate", "none")
        readme = repo / ".game-of-cards" / "deck" / "real-ready" / "README.md"
        body = readme.read_text()
        body = body.replace(
            "- [ ] (replace with real criteria)",
            "- [ ] Real criterion for the authored ready card.",
        )
        body = body.rstrip() + "\n\n## Context\n\nAuthored ready card.\n"
        readme.write_text(body)
        _goc(repo, "publish", "real-ready")

        # A freshly-filed draft scaffold: high contribution, default gate=decision.
        _goc(repo, "new", "phantom-draft", "--contribution", "high")

        ready_out = _goc(repo, "--ready", "--no-color")
        leverage = next(
            (ln for ln in ready_out.splitlines() if ln.startswith("Pulling ")), ""
        )

        print("=== goc --ready ===")
        print(ready_out.strip() or "(empty)")
        print("\n=== leverage line ===")
        print(leverage or "(no leverage line)")
        print()

        names_draft = "phantom-draft" in leverage
        print(f"leverage line names the draft scaffold : {names_draft}")

        if names_draft:
            print(
                "\nFAIL: the leverage line names `phantom-draft`, an unauthored "
                "draft scaffold, as the Highest gated card. No real gated card "
                "exists, so the clause should be omitted entirely."
            )
            return 1

        print(
            "\nOK: the leverage line excludes draft scaffolds (no real gated "
            "card -> clause omitted)."
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
